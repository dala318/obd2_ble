"""Adds config flow for OBD2 BLE."""

from glob import translate
import logging
import re
from typing import Any

try:
    from bluetooth_data_tools import human_readable_name # type: ignore
except ImportError:  # pragma: no cover - fallback for missing dependency
    def human_readable_name(_manufacturer: str | None, name: str | None, address: str):
        """Fallback if bluetooth_data_tools is unavailable."""
        return name or address
import voluptuous as vol

from bleak.backends.scanner import AdvertisementData

from homeassistant import config_entries
from homeassistant.components.bluetooth import (
    BluetoothServiceInfoBleak,
    async_discovered_service_info,
)
from homeassistant.const import CONF_ADDRESS
from homeassistant.core import callback
from homeassistant.helpers.device_registry import format_mac

from . import Obd2BleConfigEntry
from .coordinator import Obd2BleDataUpdateCoordinator
from .const import (
    DOMAIN,
    CONF_SERVICE_UUID,
    CONF_CHARACTERISTIC_UUID_READ,
    CONF_CHARACTERISTIC_UUID_WRITE,
    DEFAULT_SERVICE_UUID,
    DEFAULT_CHARACTERISTIC_UUID_READ,
    DEFAULT_CHARACTERISTIC_UUID_WRITE,
)
from .device_identifier import AVAILABLE_OBD2_CLASSES, BaseOBD2, MatcherPattern

_LOGGER = logging.getLogger(__name__)

# LOCAL_NAMES = {"OBDBLE", "OBDII-BLE", "OBD2-BLE", "OBDII BLE", "OBD2 BLE", "IOS-Vlink"}
LOCAL_NAMES = {"OBDBLE"}


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow handler."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_POLL

    def __init__(self) -> None:
        """Initialize."""
        self._errors = {}
        self._discovery_info: BluetoothServiceInfoBleak | None = None
        self._discovered_devices: dict[str, BluetoothServiceInfoBleak] = {}

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: Obd2BleConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Return the options flow."""
        return Obd2BleOptionsFlowHandler()

    def advertisement_matches(
        self,
        matcher: MatcherPattern,
        adv_data: AdvertisementData,
        mac_addr: str
    ) -> bool:
        """Determine whether the given advertisement data matches the specified pattern.
        Args:
            matcher (MatcherPattern): A dictionary containing the matching criteria.
            adv_data (AdvertisementData): An object containing the advertisement data to be checked.
            mac_addr (str): Bluetooth device address in the format: "00:11:22:aa:bb:cc"

        Returns:
            bool: True if the advertisement data matches the specified pattern, False otherwise.
        """
        if (
            service_uuid := matcher.get("service_uuid")
        ) and service_uuid not in adv_data.service_uuids:
            return False

        if (
            service_data_uuid := matcher.get("service_data_uuid")
        ) and service_data_uuid not in adv_data.service_data:
            return False

        if (oui := matcher.get("oui")) and not mac_addr.lower().startswith(oui.lower()[:8]):
            return False

        if (manufacturer_id := matcher.get("manufacturer_id")) is not None:
            if manufacturer_id not in adv_data.manufacturer_data:
                return False

            if manufacturer_data_start := matcher.get("manufacturer_data_start"):
                if not adv_data.manufacturer_data[manufacturer_id].startswith(
                    bytes(manufacturer_data_start)
                ):
                    return False

        return not (
            (local_name := matcher.get("local_name"))
            and not re.compile(translate(local_name)).match(adv_data.local_name or "")
        )


    async def _async_device_supported(
        self, discovery_info: BluetoothServiceInfoBleak
    ) -> type[BaseOBD2] | None:
        """Check if device is supported by an available OBD2 BLE class."""
        for obd2_class in AVAILABLE_OBD2_CLASSES:
            if all([self.advertisement_matches(matcher, discovery_info.advertisement, discovery_info.address) for matcher in obd2_class.matcher_dict_list()]):
                _LOGGER.debug(
                    "Device %s (%s) detected as '%s'",
                    discovery_info.name,
                    format_mac(discovery_info.address),
                    # obd2_class.obd2_id(),
                    obd2_class.__name__,
                )
                return obd2_class
        return None

    async def async_step_bluetooth(
        self, discovery_info: BluetoothServiceInfoBleak
    ) -> config_entries.ConfigFlowResult:
        """Handle the bluetooth discovery step."""
        await self.async_set_unique_id(discovery_info.address)
        self._abort_if_unique_id_configured()

        if not (obd2_class := await self._async_device_supported(discovery_info)):
            return self.async_abort(reason="not_supported")

        self._discovery_info = discovery_info
        self.context["title_placeholders"] = {
            "name": human_readable_name(
                None, discovery_info.name, discovery_info.address
            )
        }
        return await self.async_step_user()

    async def async_step_user(self, user_input: dict | None = None) -> config_entries.ConfigFlowResult:
        """Handle the user step to pick discovered device."""
        errors: dict[str, str] = {}

        if user_input is not None:
            address = user_input[CONF_ADDRESS]
            discovery_info = self._discovered_devices[address]
            local_name = discovery_info.name
            await self.async_set_unique_id(
                discovery_info.address, raise_on_progress=False
            )
            self._abort_if_unique_id_configured()
            return self.async_create_entry(
                title=local_name,
                data={
                    CONF_ADDRESS: discovery_info.address,
                },
            )

        if discovery := self._discovery_info:
            self._discovered_devices[discovery.address] = discovery
        else:
            current_addresses = self._async_current_ids()
            for discovery in async_discovered_service_info(self.hass):
                if (
                    discovery.address in current_addresses
                    or discovery.address in self._discovered_devices
                    or not any(
                        discovery.name.startswith(local_name)
                        for local_name in LOCAL_NAMES
                    )
                    or not (obd2_class := await self._async_device_supported(discovery))
                ):
                    continue
                self._discovered_devices[discovery.address] = discovery

        if not self._discovered_devices:
            return self.async_abort(reason="no_unconfigured_devices")

        data_schema = vol.Schema(
            {
                vol.Required(CONF_ADDRESS): vol.In(
                    {
                        service_info.address: f"{service_info.name} ({service_info.address})"
                        for service_info in self._discovered_devices.values()
                    }
                ),
            }
        )
        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors,
        )


class Obd2BleOptionsFlowHandler(config_entries.OptionsFlow):
    """Config flow options handler for obd2_ble."""

    def __init__(self) -> None:
        """Initialize options flow."""
        self.options: dict = {}

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Manage the options."""
        if not self.options:
            self.options = dict(self.config_entry.options)

        if user_input is not None:
            self.options.update(user_input)
            return await self._update_options()

        # # Check if runtime_data exists (Python 3.10+ way)
        # if hasattr(self.config_entry, "runtime_data"):
        #     coordinator = self.config_entry.runtime_data.coordinator
        # else:
        #     # Fallback to the old way where DOMAIN is your integration slug
        #     coordinator = self.hass.data[DOMAIN][self.config_entry.entry_id]
        # coordinator: Obd2BleDataUpdateCoordinator = self.hass.data[DOMAIN][self.config_entry.entry_id]
        coordinator: Obd2BleDataUpdateCoordinator = self.config_entry.runtime_data
        pid_commands = await coordinator.async_get_all_pid_commands()
        _LOGGER.debug("PID commands: %s", pid_commands)
        service_collection = coordinator.transport.get_service_collection()
        for service in service_collection:
            _LOGGER.debug("Discovered service: %s", service.uuid)
            for characteristic in service.characteristics:
                _LOGGER.debug("Discovered characteristic: %s", characteristic.uuid)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        "cache_values", default=self.options.get("cache_values", False)
                    ): bool,
                    vol.Required(
                        "fast_poll", default=self.options.get("fast_poll", 10)
                    ): int,
                    vol.Required(
                        "slow_poll", default=self.options.get("slow_poll", 300)
                    ): int,
                    vol.Required(
                        "xs_poll", default=self.options.get("xs_poll", 3600)
                    ): int,
                    vol.Optional(
                        CONF_SERVICE_UUID,
                        default=self.options.get(CONF_SERVICE_UUID)
                        or DEFAULT_SERVICE_UUID,
                    ): str,
                    vol.Optional(
                        CONF_CHARACTERISTIC_UUID_READ,
                        default=self.options.get(CONF_CHARACTERISTIC_UUID_READ)
                        or DEFAULT_CHARACTERISTIC_UUID_READ,
                    ): str,
                    vol.Optional(
                        CONF_CHARACTERISTIC_UUID_WRITE,
                        default=self.options.get(CONF_CHARACTERISTIC_UUID_WRITE)
                        or DEFAULT_CHARACTERISTIC_UUID_WRITE,
                    ): str,
                }
            ),
        )

    async def _update_options(self):
        """Update config entry options."""
        return self.async_create_entry(
            title=self.config_entry.data.get(CONF_ADDRESS), data=self.options
        )
