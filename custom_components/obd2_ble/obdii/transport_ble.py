import asyncio
import logging

from bleak import BleakClient
from bleak.backends.device import BLEDevice

from typing import Optional, Dict, Any

from obdii.basetypes import MISSING

from .async_transport_base import AsyncTransportBase

_LOGGER: logging.Logger = logging.getLogger(__package__)

class TransportBLE(AsyncTransportBase):
    def __init__(
        self,
        ble_device: BLEDevice = MISSING,
        uuid_write: str = MISSING,
        uuid_read: str = MISSING,
        timeout: float = 10.0,
        **kwargs,
    ) -> None:
        self._ble_device = ble_device
        self.config: Dict[str, Any] = {
            "uuid_write": uuid_write,
            "uuid_read": uuid_read,
            "timeout": timeout,
            **kwargs,
        }

        self.ble_conn: Optional[BleakClient] = None

        if ble_device is MISSING or uuid_write is MISSING or uuid_read is MISSING:
            raise ValueError(
                "ble_device (%s), uuid_write (%s) and uuid_read (%s) must be specified for TransportBLE.",
                ble_device, uuid_write, uuid_read
            )

        self._buffer = bytearray()
        self._data_event = asyncio.Event()

    def __repr__(self) -> str:
        return f"<TransportBLE {self._ble_device}>"

    def _notify_callback(self, _, data: bytearray) -> None:
        self._buffer.extend(data)
        self._data_event.set()

    def is_connected(self) -> bool:
        if self.ble_conn is None:
            _LOGGER.warning("BLE connection is not defined.")
            return False
        return self.ble_conn.is_connected

    async def async_connect(self) -> None:
        self.ble_conn = BleakClient(self._ble_device)
        _LOGGER.debug("Attempting to connect to BLE device %s (%s)", self.ble_conn.name, self._ble_device.address)
        await self.ble_conn.connect()
        await self.ble_conn.start_notify(self.config["uuid_read"], self._notify_callback)
        for service in self.ble_conn.services:
            _LOGGER.debug("Discovered service: %s", service.uuid)
            for char in service.characteristics:
                _LOGGER.debug("Discovered characteristic: %s", char.uuid)
    
    async def async_close(self) -> None:
        if self.ble_conn and self.ble_conn.is_connected:
            await self.ble_conn.stop_notify(self.config["uuid_read"])
            await self.ble_conn.disconnect()
        self.ble_conn = None

    async def async_write_bytes(self, query: bytes) -> None:
        if self.ble_conn is None:
            raise RuntimeError("BLE connection is not established.")
        await self.ble_conn.write_gatt_char(self.config["uuid_write"], query)

    async def async_read_bytes(self, expected_seq: bytes = b'>', size: Optional[int] = None) -> bytes:
        """Read bytes from the BLE device until expected sequence or size is reached."""
        lenterm = len(expected_seq)

        while True:
            # Check if we have enough data to look for the terminator
            if len(self._buffer) >= lenterm:
                if self._buffer[-lenterm:] == expected_seq:
                    break
            if size is not None and len(self._buffer) >= size:
                break

            # Wait for more data with timeout
            self._data_event.clear()
            try:
                await asyncio.wait_for(self._data_event.wait(), timeout=self.config["timeout"])
            except asyncio.TimeoutError:
                # Timeout reached, return what we have
                break

        result = bytes(self._buffer)
        self._buffer.clear()
        return result
