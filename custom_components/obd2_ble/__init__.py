"""Custom integration to integrate OBD2 BLE with Home Assistant.

For more details about this integration, please refer to
https://github.com/dala318/obd2_ble
"""

import logging

from bleak_retry_connector import get_device

from homeassistant.components import bluetooth
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ADDRESS
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.config_validation import config_entry_only_config_schema
from homeassistant.helpers.typing import ConfigType

# from obdii import Connection
from .obdii.async_connection import AsyncConnection
from .obdii.transport_ble import TransportBLE
from .const import (
    DEFAULT_CHARACTERISTIC_UUID_READ,
    DEFAULT_CHARACTERISTIC_UUID_WRITE,
    CONF_CHARACTERISTIC_UUID_READ,
    CONF_CHARACTERISTIC_UUID_WRITE,
    DOMAIN,
    PLATFORMS,
    STARTUP_MESSAGE
)
from .coordinator import Obd2BleDataUpdateCoordinator

_LOGGER: logging.Logger = logging.getLogger(__package__)

CONFIG_SCHEMA = config_entry_only_config_schema(DOMAIN)


async def async_setup(hass: HomeAssistant, config: ConfigType):
    """Set up this integration using YAML is not supported."""
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up this integration using UI."""
    if hass.data.get(DOMAIN) is None:
        hass.data.setdefault(DOMAIN, {})
        _LOGGER.info(STARTUP_MESSAGE)

    address: str = entry.data[CONF_ADDRESS]
    ble_device = bluetooth.async_ble_device_from_address(
        hass, address.upper(), True
    ) or await get_device(address)
    if not ble_device:
        raise ConfigEntryNotReady(
            f"Could not find OBD BLE device with address {address}"
        )

    transport = TransportBLE(
        ble_device=ble_device,
        uuid_write=entry.options.get(CONF_CHARACTERISTIC_UUID_WRITE, DEFAULT_CHARACTERISTIC_UUID_WRITE),
        uuid_read=entry.options.get(CONF_CHARACTERISTIC_UUID_READ, DEFAULT_CHARACTERISTIC_UUID_READ),
        # timeout=entry.options.get("timeout", 10.0),
        loop = hass.loop,
    )
    # if _LOGGER.handlers:
    #     # Pass the primary handler used by your integration's logger
    #     handler = _LOGGER.handlers[0]
    # else:
    #     # Fallback: If HA hasn't attached handlers yet, use the NullHandler 
    #     # or the root handler to avoid errors.
    #     handler = logging.NullHandler()
    # api = AsyncConnection(transport, auto_connect=False, log_handler=handler)
    api = AsyncConnection(transport, auto_connect=False)
    coordinator = Obd2BleDataUpdateCoordinator(
        hass, address=address, api=api, options=entry.options or {}
    )

    hass.data[DOMAIN][entry.entry_id] = coordinator

    await coordinator.async_config_entry_first_refresh()
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
            {"address": address},
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


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Handle removal of an entry."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    hass.data[DOMAIN].pop(entry.entry_id)
    return unloaded


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)
