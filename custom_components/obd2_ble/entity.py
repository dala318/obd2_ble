"""ObdBleEntity class."""

import logging

from homeassistant.const import CONF_ADDRESS
from homeassistant.components.bluetooth.const import DOMAIN as BLUETOOTH_DOMAIN
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.device_registry import CONNECTION_BLUETOOTH, DeviceInfo
import obdii

from .coordinator import Obd2BleDataUpdateCoordinator
from .const import ATTRIBUTION, DOMAIN, NAME

_LOGGER = logging.getLogger(__name__)

class ObdBleEntity(CoordinatorEntity):
    """Config entry for obd2_ble."""

    def __init__(self, coordinator: Obd2BleDataUpdateCoordinator, config_entry, command, icon, id, domain) -> None:
        """Initialise."""
        super().__init__(coordinator)
        self.config_entry = config_entry
        self._command = command
        self._attr_icon = icon

        mac = self.config_entry.data[CONF_ADDRESS]
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, mac), (BLUETOOTH_DOMAIN, mac)},
            connections={(CONNECTION_BLUETOOTH, mac)},
            name=NAME,
            model_id=coordinator.api.protocol.name,
            sw_version=obdii.__version__,
            # "manufacturer": NAME,
        )
        self._attr_unique_id = f"{self.config_entry.data[CONF_ADDRESS]}-{domain}-{id}"


    async def async_added_to_hass(self):
        """Run when entity is added to register its command."""
        self.coordinator.active_commands.add(self._command)
        _LOGGER.debug("Added command %s to active commands", self._command)
        await super().async_added_to_hass()

    async def async_will_remove_from_hass(self):
        """Clean up when sensor is disabled/removed."""
        self.coordinator.active_commands.discard(self._command)
        _LOGGER.debug("Removed command %s from active commands", self._command)
        await super().async_will_remove_from_hass()
