from abc import ABC, abstractmethod
from typing import TypedDict


class MatcherPattern(TypedDict, total=False):
    """Optional patterns that can match Bleak advertisement data."""

    local_name: str  # name pattern that supports Unix shell-style wildcards
    manufacturer_data_start: list[int]  # start bytes of manufacturer data
    manufacturer_id: int  # required manufacturer ID
    oui: str  # required OUI used in the MAC address (first 3 bytes)
    service_data_uuid: str  # service data for the service UUID
    service_uuid: str  # 128-bit UUID that the device must advertise
    connectable: bool  # True if active connections to the device are required


class BaseOBD2(ABC):
    @staticmethod
    @abstractmethod
    def matcher_dict_list() -> list[MatcherPattern]:
        """Return a list of Bluetooth advertisement matchers."""

    @staticmethod
    @abstractmethod
    # def uuid_services() -> tuple[str, ...]:
    #     """Return list of 128-bit UUIDs of used services."""
    def uuid_service() -> str:
        """Return 128-bit UUID of used service."""

    @staticmethod
    @abstractmethod
    def uuid_rx() -> str:
        """Return 16-bit UUID of characteristic that provides notification/read property."""

    @staticmethod
    @abstractmethod
    def uuid_tx() -> str:
        """Return 16-bit UUID of characteristic that provides write property."""


class OBD2_BLE(BaseOBD2):
    @staticmethod
    def matcher_dict_list() -> list[MatcherPattern]:
        """Provide BluetoothMatcher definition."""
        # return [{"local_name": "OBD2*", "connectable": True}]
        return [{"local_name": "OBDII"}]

    @staticmethod
    def uuid_service() -> str:
        return "0000fff0-0000-1000-8000-00805f9b34fb"

    @staticmethod
    def uuid_rx() -> str:
        return "0000fff1-0000-1000-8000-00805f9b34fb"

    @staticmethod
    def uuid_tx() -> str:
        return "0000fff1-0000-1000-8000-00805f9b34fb"


class VlinkOBD2_BLE(OBD2_BLE):
    @staticmethod
    def matcher_dict_list() -> list[MatcherPattern]:
        """Provide BluetoothMatcher definition."""
        return [{"local_name": "Vlink*"}]

    @staticmethod
    def uuid_service() -> str:
        return "000018f0-0000-1000-8000-00805f9b34fb"

    @staticmethod
    def uuid_rx() -> str:
        return "000018f1-0000-1000-8000-00805f9b34fb"

    @staticmethod
    def uuid_tx() -> str:
        return "000018f1-0000-1000-8000-00805f9b34fb"

AVAILABLE_OBD2_CLASSES: list[type[BaseOBD2]] = [OBD2_BLE, VlinkOBD2_BLE]