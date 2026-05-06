"""Sensor platform for OBD2 BLE."""

import logging

from obdii import Response, commands

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN, NAME
from .entity import ObdBleEntity

_LOGGER = logging.getLogger(__name__)

SENSOR_TYPES: dict[str, SensorEntityDescription] = {
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
    "fuel_status": SensorEntityDescription(
        key=commands.FUEL_STATUS,
        icon="mdi:gas-station",
        name="Fuel Status",
        native_unit_of_measurement=commands.FUEL_STATUS.units.__str__(),
        device_class=SensorDeviceClass.VOLUME_STORAGE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    "engine_run_time": SensorEntityDescription(
        key=commands.ENGINE_RUN_TIME,
        icon="mdi:car-shift-pattern",
        name="Engine run time",
        native_unit_of_measurement=commands.ENGINE_RUN_TIME.units.__str__(),
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    "engine_speed": SensorEntityDescription(
        key=commands.ENGINE_SPEED,
        icon="mdi:gauge",
        name="Engine speed",
        native_unit_of_measurement=commands.ENGINE_SPEED.units.__str__(),
        suggested_display_precision=1,
        # device_class=SensorDeviceClass.REVOLUTION_PER_MINUTE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    "catalyst_temp_bank_1_sensor_1": SensorEntityDescription(
        key=commands.CATALYST_TEMP_BANK_1_SENSOR_1,
        icon="mdi:gauge",
        name="Catalyst Temperature Bank 1 Sensor 1",
        native_unit_of_measurement=commands.CATALYST_TEMP_BANK_1_SENSOR_1.units.__str__(),
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    "vehicle_voltage": SensorEntityDescription(
        key=commands.VEHICLE_VOLTAGE,
        icon="mdi:gauge",
        name="Vehicle Voltage",
        native_unit_of_measurement=commands.VEHICLE_VOLTAGE.units.__str__(),
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    "accelerator_position_relative": SensorEntityDescription(
        key=commands.ACCELERATOR_POSITION_RELATIVE,
        icon="mdi:gauge",
        name="Accelerator Position Relative",
        native_unit_of_measurement=commands.ACCELERATOR_POSITION_RELATIVE.units.__str__(),
        device_class=SensorDeviceClass.POWER_FACTOR,
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
        super().__init__(coordinator, config_entry, description.key, description.icon, id, DOMAIN)
        self._id = id
        self._description = description
        self._attr_name = f"{NAME} {description.name}"
        self._attr_device_class = description.device_class
        self._attr_native_unit_of_measurement = description.native_unit_of_measurement
        self._attr_state_class = description.state_class

    # async def async_update(self) -> None:
    def _handle_coordinator_update(self) -> None:
        try:
            # data = await self.client.get_data()
            # data = self.coordinator.data.get(self._id)
            data: Response | None = self.coordinator.data.get(self._description.key)
            _LOGGER.debug("Updating sensor %s with data: %s", self._id, data)
        except Exception as ex:
            _LOGGER.error(f"Error updating sensor {self._id}: {ex}")
            self._attr_available = False
        else:
            if data is None:
                _LOGGER.warning(f"No data available for sensor {self._id}")
                self._attr_available = False
            elif isinstance(data, Response):
                self._attr_available = True
                self._attr_native_value = data.value

        super()._handle_coordinator_update()

    # @property
    # def native_value(self):
    #     """Return the state of the sensor."""
    #     return self.coordinator.data.get(self._id)

