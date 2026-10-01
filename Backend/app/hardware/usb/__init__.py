"""
Cyber Evidence Box (CEB) USB & Hardware Subsystem.
Provides detection, registry matching, connection lifecycle, and WebSocket events.
"""

from .usb_manager import USBDeviceManager, usb_manager
from .device_registry import DeviceRegistry, device_registry

__all__ = ["USBDeviceManager", "usb_manager", "DeviceRegistry", "device_registry"]
