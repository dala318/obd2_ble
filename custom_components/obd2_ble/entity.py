"""ObdBleEntity class."""

import logging

from homeassistant.const import CONF_ADDRESS
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import ATTRIBUTION, DOMAIN, NAME


_LOGGER = logging.getLogger(__name__)


class ObdBleEntity(CoordinatorEntity):
    """Config entry for obd2_ble."""

    def __init__(self, coordinator, config_entry, command, icon) -> None:
        """Initialise."""
        super().__init__(coordinator)
        self.config_entry = config_entry
        self._command = command
        self._attr_icon = icon

        self._attr_device_info = {
            "identifiers": {(DOMAIN, self.config_entry.data[CONF_ADDRESS])},
            "name": NAME,
            # "model": VERSION,
            "manufacturer": NAME,
        }
        self._attr_unique_id = f"{self.config_entry.data[CONF_ADDRESS]}-{self.name}"


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

    # @property
    # def unique_id(self):
    #     """Return a unique ID to use for this entity."""
    #     return f"{self.config_entry.data[CONF_ADDRESS]}-{self.name}"

    # @property
    # def device_info(self):
    #     """Return device information."""
    #     return {
    #         "identifiers": {(DOMAIN, self.config_entry.data[CONF_ADDRESS])},
    #         "name": NAME,
    #         # "model": VERSION,
    #         "manufacturer": NAME,
    #     }

    @property
    def device_state_attributes(self):
        """Return the state attributes."""
        return {
            "attribution": ATTRIBUTION,
            "id": str(self.coordinator.data.get("id")),
            "integration": DOMAIN,
        }
