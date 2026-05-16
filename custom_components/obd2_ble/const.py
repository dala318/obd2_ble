"""Constants for OBD2 BLE."""

# Base component constants
from homeassistant.const import Platform

NAME = "OBD2 BLE"
DOMAIN = "obd2_ble"
DOMAIN_DATA = f"{DOMAIN}_data"

ATTRIBUTION = "Data provided by http://jsonplaceholder.typicode.com/"
ISSUE_URL = "https://github.com/dala318/obd2_ble/issues"

# Platforms
PLATFORMS: list[Platform] = [Platform.SENSOR]
# PLATFORMS: list[Platform] = [Platform.BINARY_SENSOR, Platform.BUTTON, Platform.SENSOR]


# Configuration and options
CONF_AUTO_CONFIGURE = "auto_configure"
CONF_CHARACTERISTIC_UUID_READ = "characteristic_uuid_read"
CONF_CHARACTERISTIC_UUID_WRITE = "characteristic_uuid_write"
CONF_ENABLED = "enabled"
# CONF_USERNAME = "username"
# CONF_PASSWORD = "password"
CONF_PROTOCOL = "protocol"
CONF_SERVICE_UUID = "service_uuid"

# Defaults
DEFAULT_NAME = DOMAIN
DEFAULT_SERVICE_UUID = "0000fff0-0000-1000-8000-00805f9b34fb"
DEFAULT_CHARACTERISTIC_UUID_READ = "0000fff1-0000-1000-8000-00805f9b34fb"
DEFAULT_CHARACTERISTIC_UUID_WRITE = "0000fff1-0000-1000-8000-00805f9b34fb"


STARTUP_MESSAGE = f"""
-------------------------------------------------------------------
{NAME}
This is a custom integration!
If you have any issues with this you need to open an issue here:
{ISSUE_URL}
-------------------------------------------------------------------
"""
