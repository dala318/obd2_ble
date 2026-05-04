"""Coordinator for OBD2 BLE."""

from datetime import timedelta
# from functools import partial
import logging
from typing import Any

from homeassistant.components.bluetooth.api import async_address_present
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from obdii import Command, Response, at_commands
# from .obdii.transport_ble import TransportBLE
from .obdii.async_connection import AsyncConnection

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

# when the device is in range, and the car is on, poll quickly to get
# as much data as we can before it turns off
FAST_POLL_INTERVAL = timedelta(seconds=10)

# when the device is in range, but the car is off, we need to poll
# occasionally to see whether the car has be turned back on. On some cars
# this causes a relay to click every time, so this interval needs to be
# as long as possible to prevent excessive wear on the relay.
SLOW_POLL_INTERVAL = timedelta(minutes=5)

# when the device is out of range, use ultra slow polling since a bluetooth
# advertisement message will kick it back into life when back in range.
# see __init__.py: _async_specific_device_found()
ULTRA_SLOW_POLL_INTERVAL = timedelta(hours=1)

DEFAULT_FAST_POLL = 10  # pick sane defaults for your integration
DEFAULT_SLOW_POLL = 300
DEFAULT_XS_POLL = 3600
DEFAULT_CACHE_VALUES = True


BASE_COMMANDS = [
    at_commands.VERSION_ID,
]

class Obd2BleDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching data from the API."""

    def __init__(
        self, hass: HomeAssistant, address: str, api: AsyncConnection, options
    ) -> None:
        """Initialize."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=FAST_POLL_INTERVAL,
            always_update=True,
        )
        self._address = address
        self.api = api
        self._cache_data: dict[str, Any] = {}
        self.options = options

        # Track which commands are active to avoid unnecessary polling of inactive commands
        self.active_commands: set[Command] = set()

    async def _async_update_data(self) -> dict[str, Any]:
        """Update data via library."""

        # Check if the device is still available
        _LOGGER.debug("Check if the device is still available")
        available = async_address_present(self.hass, self._address, connectable=True)
        if not available:
            # Device out of range? Switch to active polling interval for when it reappears
            _LOGGER.debug("Car out of range? Switch to extra slow polling")
            self.update_interval = timedelta(seconds=self._xs_poll_interval)
            _LOGGER.debug(
                "Car out of range? Switch to ultra slow polling: interval = %s",
                self.update_interval,
            )
            if self.options.get("cache_values", False):
                return self._cache_data
            return {}

        _LOGGER.debug("Device is available, check if connected")
        if not self.api.is_connected():
            try:
                _LOGGER.info("Device is available but not connected, attempt to connect")
                await self.api.aconnect()
                if not self.api.is_connected():
                    raise UpdateFailed("No connection to OBD2 after connect attempt")
            except Exception as err:
                raise UpdateFailed(f"Error connecting with OBD2: {err}")

        _LOGGER.debug("Device is connected, proceed to query data")
        try:
            new_data = {}
            for command in set(BASE_COMMANDS) | self.active_commands:
                if command is None:
                    _LOGGER.warning("Skipping invalid command: %s", command)
                    continue
                try:
                    _LOGGER.debug("Querying OBD2 for command %s", command)
                    response = await self.api.aquery(command)
                    new_data[command] = response
                except Exception as err:
                    _LOGGER.error(f"Error occurred while querying command {command}: {err}")
            if new_data is None:
                raise UpdateFailed("Failed to connect to OBD device")
            if len(new_data) == 0:
                self.update_interval = timedelta(seconds=self._slow_poll_interval)
                _LOGGER.debug(
                    "Car is probably off, switch to slow polling: interval = %s",
                    self.update_interval,
                )
            else:
                self.update_interval = timedelta(seconds=self._fast_poll_interval)
                _LOGGER.debug(
                    "Car is on, polling: interval = %s",
                    self.update_interval,
                )
        except Exception as err:
            raise UpdateFailed(f"Unable to fetch data: {err}") from err
        else:
            if self.options.get("cache_values", False):
                self._cache_data.update(new_data)
                return self._cache_data
            return new_data

    @property
    def options(self):
        """User configuration options."""
        return self._options

    @options.setter
    def options(self, options):
        """Set the configuration options."""
        self._options = options
        self._fast_poll_interval = options.get("fast_poll", DEFAULT_FAST_POLL)
        self._slow_poll_interval = options.get("slow_poll", DEFAULT_SLOW_POLL)
        self._xs_poll_interval = options.get("xs_poll", DEFAULT_XS_POLL)
        self._cache_values = options.get("cache_values", DEFAULT_CACHE_VALUES)
