import asyncio
import logging

from bleak import BleakClient
from bleak.backends.device import BLEDevice

from threading import Lock, Event
from time import monotonic
from typing import Optional, Dict, Any, Coroutine, Union

from obdii.transports.transport_base import TransportBase
from obdii.basetypes import MISSING

_LOGGER: logging.Logger = logging.getLogger(__package__)

class TransportBLE(TransportBase):
    def __init__(
        self,
        ble_device: BLEDevice = MISSING,
        uuid_write: str = MISSING,
        uuid_read: str = MISSING,
        timeout: float = 10.0,
        loop: Optional[asyncio.AbstractEventLoop] = None,
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
        self._lock = Lock()
        self._data_ready = Event()

        self._loop = loop

    def __repr__(self) -> str:
        return f"<TransportBLE {self._ble_device}>"

    def _run_coro(self, coro: Coroutine) -> Any:
        if self._loop is None:
            raise RuntimeError("Event loop is not running.")
        future = asyncio.run_coroutine_threadsafe(coro, self._loop)
        return future.result(timeout=self.config["timeout"])
    
    def _notify_callback(self, _, data: bytearray) -> None:
        with self._lock:
            self._buffer.extend(data)
        self._data_ready.set()

    async def _connect(self) -> None:
        self.ble_conn = BleakClient(self._ble_device)
        _LOGGER.debug("Attempting to connect to BLE device %s", self.ble_conn)
        await self.ble_conn.connect()
        await self.ble_conn.start_notify(self.config["uuid_read"], self._notify_callback)
        for service in self.ble_conn.services:
            _LOGGER.debug("Discovered service: %s", service.uuid)
            for char in service.characteristics:
                _LOGGER.debug("Discovered characteristic: %s", char.uuid)
    
    async def _close(self) -> None:
        if self.ble_conn and self.ble_conn.is_connected:
            await self.ble_conn.stop_notify(self.config["uuid_read"])
            await self.ble_conn.disconnect()
        self.ble_conn = None

    async def _write(self, query: bytes) -> None:
        if self.ble_conn is None:
            raise RuntimeError("BLE connection is not established.")
        await self.ble_conn.write_gatt_char(self.config["uuid_write"], query)

    def connect(self, loop: Optional[asyncio.AbstractEventLoop] = None, **kwargs) -> None:
        self.config.update(kwargs)

        if loop is not None:
            self._loop = loop

        try:
            self._run_coro(self._connect())
        except Exception:
            self.close() # Cleanup on failure
            raise

    def close(self) -> None:
        if self.is_connected():
            try:
                self._run_coro(self._close())
            except Exception:
                pass # Already disconnecting or loop is dead

    def is_connected(self) -> bool:
        if self.ble_conn is None:
            return False
        return self.ble_conn.is_connected

    def write_bytes(self, query: bytes) -> None:
        if not self.is_connected():
            raise RuntimeError("BLE is not connected.")
        with self._lock:
            self._buffer.clear()
        self._data_ready.clear()
        self._run_coro(self._write(query))

    def read_bytes(self, expected_seq: bytes = b'>', size: int = MISSING) -> bytes:
        lenterm = len(expected_seq)
        deadline = monotonic() + self.config["timeout"]

        while True:
            remaining = deadline - monotonic()
            if remaining <= 0:
                raise TimeoutError("read timed out.")

            with self._lock:
                snapshot = bytes(self._buffer)

            if snapshot[-lenterm:] == expected_seq:
                break
            if size is not MISSING and len(snapshot) >= size:
                break

            self._data_ready.wait(timeout=remaining)
            self._data_ready.clear()

        return snapshot
