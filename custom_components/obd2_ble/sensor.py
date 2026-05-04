"""Sensor platform for OBD2 BLE."""

from obdii import commands

from homeassistant.components.sensor import (
    # SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN, NAME
from .entity import ObdBleEntity

SENSOR_TYPES: dict[str, SensorEntityDescription] = {
    # "gear_position": SensorEntityDescription(
    #     key="gear_position",
    #     icon="mdi:car-shift-pattern",
    #     name="Gear position",
    #     device_class=SensorDeviceClass.ENUM,
    # ),
    # "bat_12v_voltage": SensorEntityDescription(
    #     key="bat_12v_voltage",
    #     icon="mdi:car-battery",
    #     name="12V battery voltage",
    #     native_unit_of_measurement="V",
    #     suggested_display_precision=1,
    #     device_class=SensorDeviceClass.VOLTAGE,
    #     state_class=SensorStateClass.MEASUREMENT,
    # ),
    # "bat_12v_current": SensorEntityDescription(
    #     key="bat_12v_current",
    #     icon="mdi:car-battery",
    #     name="12V battery current",
    #     native_unit_of_measurement="A",
    #     suggested_display_precision=2,
    #     device_class=SensorDeviceClass.CURRENT,
    #     state_class=SensorStateClass.MEASUREMENT,
    # ),
    "engine_speed": SensorEntityDescription(
        key=commands.ENGINE_SPEED,
        icon="mdi:gauge",
        name="Engine speed",
        native_unit_of_measurement=commands.ENGINE_SPEED.units.__str__(),
        suggested_display_precision=1,
        # device_class=SensorDeviceClass.REVOLUTION_PER_MINUTE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
}


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities
):
    """Set up sensor platform."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    entities = [
        ObdBleSensor(coordinator, entry, id, description)
        for id, description in SENSOR_TYPES.items()
    ]
    async_add_entities(entities)


class ObdBleSensor(ObdBleEntity, SensorEntity):
    """Config entry for obd2_ble sensors."""

    def __init__(
        self,
        coordinator,
        config_entry,
        id: str,
        description: SensorEntityDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, config_entry, description.key, description.icon)
        self._id = id
        self._description = description
        self._attr_name = f"{NAME} {description.name}"
        self._attr_device_class = description.device_class
        self._attr_native_unit_of_measurement = description.native_unit_of_measurement
        self._attr_state_class = description.state_class

    async def async_update(self) -> None:
        try:
            # data = await self.client.get_data()
            # data = self.coordinator.data.get(self._id)
            data = self.coordinator.data.get(self._description.key)
        except Exception as ex:
            self._attr_available = False
        else:
            self._attr_available = True
            self._attr_native_value = data

    # @property
    # def native_value(self):
    #     """Return the state of the sensor."""
    #     return self.coordinator.data.get(self._id)

