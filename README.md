# OBD2 BLE

A Home Assistant integration for reading OBD2 vehicle data via Bluetooth Low Energy (BLE).

## Features

- Real-time OBD2 data reading from compatible BLE devices
- Automatic device discovery via Bluetooth
- Configurable polling intervals for different vehicle states
- Support for caching sensor values
- Automatic reconnection when device comes back in range

## Installation

### Via HACS (Recommended)

This integration is available through HACS. Search for "OBD2 BLE" in HACS and install it.

### Manual Installation

1. Copy the `custom_component/obd2_ble` folder to your Home Assistant `custom_components` directory
2. Restart Home Assistant
3. Go to Settings → Devices & Services → Create Automation → and add the integration

## Configuration

The integration is configured via the UI. No YAML configuration is required.

### Setup Requirements

- A compatible OBD2 BLE device (using the standard BLE service UUID `0000ffe0-0000-1000-8000-00805f9b34fb`)
- Home Assistant with connected ESPHome Bluetooth Proxy

## Supported Devices

This integration supports OBD2 dongles with BLE connectivity. It has been tested with devices using the standard OBD2 BLE GATT service.

## Troubleshooting

- Ensure your OBD2 BLE device is in range and has Bluetooth enabled
- Check Home Assistant logs for detailed error messages
- Verify the BLE service and characteristic UUIDs match your device's specifications

## Support

For issues and feature requests, please visit the [GitHub repository](https://github.com/dala318/obd2_ble/issues)
