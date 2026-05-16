"""Custom integration to integrate OBD2 BLE with Home Assistant.

For more details about this integration, please refer to
https://github.com/dala318/obd2_ble
"""

import logging
from typing_extensions import Final

from bleak.backends.device import BLEDevice
# from bleak_retry_connector import BleakClientWithServiceCache, establish_connection, get_device

from homeassistant.components import bluetooth
from homeassistant.config_entries import ConfigEntry
# from homeassistant.const import CONF_ADDRESS
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryNotReady, ConfigEntryError
from homeassistant.helpers.config_validation import config_entry_only_config_schema
# from homeassistant.helpers.typing import ConfigType
from obdii import Connection, Protocol

from .obdii.transport_ble import TransportBLE
from .const import (
    DEFAULT_CHARACTERISTIC_UUID_READ,
    DEFAULT_CHARACTERISTIC_UUID_WRITE,
    CONF_CHARACTERISTIC_UUID_READ,
    CONF_CHARACTERISTIC_UUID_WRITE,
    CONF_PROTOCOL,
    DOMAIN,
    PLATFORMS,
    STARTUP_MESSAGE
)
from .coordinator import Obd2BleDataUpdateCoordinator

_LOGGER: logging.Logger = logging.getLogger(__package__)

CONFIG_SCHEMA = config_entry_only_config_schema(DOMAIN)

type Obd2BleConfigEntry = ConfigEntry[Obd2BleDataUpdateCoordinator]


async def async_setup_entry(hass: HomeAssistant, entry: Obd2BleConfigEntry) -> bool:
    """Set up this integration using UI."""
    if hass.data.get(DOMAIN) is None:
        hass.data.setdefault(DOMAIN, {})
        _LOGGER.info(STARTUP_MESSAGE)

    if entry.unique_id is None:
        raise ConfigEntryError(
            translation_domain=DOMAIN,
            translation_key="missing_unique_id",
        )

    # migrate old entries
    # migrate_sensor_entities(hass, entry)

    ble_device: BLEDevice | None = bluetooth.async_ble_device_from_address(
        hass, entry.unique_id, True
    )

    if ble_device is None:
        _LOGGER.debug("Failed to discover device %s via Bluetooth", entry.unique_id)
        raise ConfigEntryNotReady(
            translation_domain=DOMAIN,
            translation_key="device_not_found",
            translation_placeholders={
                "mac": entry.unique_id,
            },
        )

    # ble_conn = await establish_connection(
    #     BleakClientWithServiceCache,
    #     ble_device,
    #     ble_device.name or "Unknown Device",
    #     max_attempts=3
    # )
    # if ble_conn is None:
    #     raise ConnectionError(f"Failed to connect to BLE device {ble_device.address}")
    uuid_write = DEFAULT_CHARACTERISTIC_UUID_WRITE
    uuid_read = DEFAULT_CHARACTERISTIC_UUID_READ
    # with TransportBLE(
    #     ble_device=ble_device,
    #     uuid_write=uuid_write,
    #     uuid_read=uuid_read,
    #     loop=hass.loop
    # ) as tmp_transport:
    #     tmp_transport.connect()
    #     service_collection = tmp_transport.get_service_collection()
    #     _LOGGER.debug("Discovered services: %s", service_collection)

    transport = TransportBLE(
        ble_device=ble_device,
        uuid_write=entry.data.get(CONF_CHARACTERISTIC_UUID_WRITE, uuid_write),
        uuid_read=entry.data.get(CONF_CHARACTERISTIC_UUID_READ, uuid_read),
        # timeout=entry.options.get("timeout", 10.0),
        loop = hass.loop,
    )

    api = Connection(
        transport=transport,
        auto_connect=False,
        # protocol=Protocol.ISO_15765_4_CAN_B,
        protocol=entry.options.get(CONF_PROTOCOL, Protocol.AUTO),
        # log_handler=_LOGGER.handlers[0],
        log_level=logging.DEBUG,
    )

    coordinator = Obd2BleDataUpdateCoordinator(
        hass, device=ble_device, api=api, options=entry.options or {}
    )

    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    @callback
    def _async_specific_device_found(
        service_info: bluetooth.BluetoothServiceInfoBleak,
        change: bluetooth.BluetoothChange,
    ) -> None:
        """Handle re-discovery of the device."""
        _LOGGER.debug("New service_info: %s - %s", service_info, change)
        # have just discovered the device is back in range - ping the coordinator to update immediately
        hass.async_create_task(coordinator.async_request_refresh())

    # stuff to do when cleaning up
    entry.async_on_unload(
        bluetooth.async_register_callback(
            hass,
            _async_specific_device_found,
            {"address": ble_device.address},
            bluetooth.BluetoothScanningMode.ACTIVE,
        )  # does the register callback, and returns a cancel callback for cleanup
    )

    async def update_options_listener(hass: HomeAssistant | None, entry: ConfigEntry):
        """Handle options update."""
        coordinator.options = entry.options

    entry.async_on_unload(
        entry.add_update_listener(update_options_listener)
    )  # add the listener for when the user changes options

    # entry.add_update_listener(async_reload_entry)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: Obd2BleConfigEntry) -> bool:
    """Unload a config entry."""
    unloaded: Final = await hass.config_entries.async_unload_platforms(
        entry, PLATFORMS
    )
    _LOGGER.debug("Unloaded config entry: %s, ok? %s!", entry.unique_id, unloaded)
    if unloaded and getattr(entry, "runtime_data", None) is not None:
        await entry.runtime_data.async_shutdown()
    return unloaded


# async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
#     """Reload config entry."""
#     await async_unload_entry(hass, entry)
#     await async_setup_entry(hass, entry)
