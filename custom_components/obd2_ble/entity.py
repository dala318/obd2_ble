"""ObdBleEntity class."""

import logging

from homeassistant.const import CONF_ADDRESS
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import ATTRIBUTION, DOMAIN, NAME


_LOGGER = logging.getLogger(__name__)


class ObdBleEntity(CoordinatorEntity):
    """Config entry for obd2_ble."""

    def __init__(self, coordinator, config_entry) -> None:
        """Initialise."""
        super().__init__(coordinator)
        self.config_entry = config_entry

    async def async_added_to_hass(self):
        """Run when entity is added to register its command."""
        self.coordinator.active_commands.add(self.config_entry.data.get("key"))
        _LOGGER.debug("Added command %s to active commands", self.config_entry.data.get("key"))
        await super().async_added_to_hass()

    async def async_will_remove_from_hass(self):
        """Clean up when sensor is disabled/removed."""
        self.coordinator.active_commands.discard(self.config_entry.data.get("key"))
        _LOGGER.debug("Removed command %s from active commands", self.config_entry.data.get("key"))
        await super().async_will_remove_from_hass()

    @property
    def unique_id(self):
        """Return a unique ID to use for this entity."""
        return f"{self.config_entry.data[CONF_ADDRESS]}-{self.name}"

    @property
    def device_info(self):
        """Return device information."""
        return {
            "identifiers": {(DOMAIN, self.config_entry.data[CONF_ADDRESS])},
            "name": NAME,
            # "model": VERSION,
            "manufacturer": NAME,
        }

    @property
    def device_state_attributes(self):
        """Return the state attributes."""
        return {
            "attribution": ATTRIBUTION,
            "id": str(self.coordinator.data.get("id")),
            "integration": DOMAIN,
        }
