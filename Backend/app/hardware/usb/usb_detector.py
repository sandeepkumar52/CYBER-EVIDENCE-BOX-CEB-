import logging
import os
import platform
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

logger = logging.getLogger("ceb.hardware.detector")

try:
    import serial.tools.list_ports
    HAS_PYSERIAL = True
except ImportError:
    HAS_PYSERIAL = False


@dataclass
class DetectedUSBDevice:
    device_path: str
    vendor_id: Optional[str] = None
    product_id: Optional[str] = None
    manufacturer: Optional[str] = None
    product: Optional[str] = None
    serial_number: Optional[str] = None
    usb_path: Optional[str] = None
    type: str = "serial"
    is_mock: bool = False
    description: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "devicePath": self.device_path,
            "vendorId": self.vendor_id,
            "productId": self.product_id,
            "manufacturer": self.manufacturer,
            "product": self.product,
            "serialNumber": self.serial_number,
            "usbPath": self.usb_path,
            "type": self.type,
            "isMock": self.is_mock,
            "description": self.description,
        }


def is_valid_device_path(path: str) -> bool:
    """Validate device path to prevent directory traversal or shell injection."""
    if not path or not isinstance(path, str):
        return False
    # Allowed formats:
    # Linux: /dev/ttyUSB0, /dev/ttyACM0, /dev/ttyAMA0, /dev/serial/by-id/...
    # Windows: COM1, COM2...
    # Mock: MOCK_USB0, MOCK_USB1, /dev/ttyUSB0 (in mock mode)
    clean = path.strip()
    if any(char in clean for char in [";", "&", "|", "`", "$", "(", ")", "\n", "\r", "<", ">", "\0"]):
        return False

    # Check against known safe patterns
    linux_pattern = r"^/dev/(tty(USB|ACM|AMA|S)[0-9]+|serial/by-id/[A-Za-z0-9_\-\.]+)"
    windows_pattern = r"^COM[0-9]+$"
    mock_pattern = r"^(MOCK_[A-Za-z0-9_\-]+|/dev/tty(USB|ACM)[0-9]+)$"

    return bool(
        re.match(linux_pattern, clean)
        or re.match(windows_pattern, clean, re.IGNORECASE)
        or re.match(mock_pattern, clean)
    )


class USBDetector:
    def __init__(self, mode: str = "auto"):
        self.mode = mode.lower()  # "auto", "mock", "production"
        self._mock_devices: Dict[str, DetectedUSBDevice] = {}
        self._init_default_mock_devices()

    def _init_default_mock_devices(self) -> None:
        """Default simulated devices for development & testing without physical hardware."""
        is_windows = platform.system() == "Windows"
        esp32_path = "MOCK_COM3" if is_windows else "/dev/ttyUSB0"
        gps_path = "MOCK_COM4" if is_windows else "/dev/ttyUSB1"

        self._mock_devices = {
            esp32_path: DetectedUSBDevice(
                device_path=esp32_path,
                vendor_id="10C4",
                product_id="EA60",
                manufacturer="Silicon Labs",
                product="CP2102 USB to UART Bridge (ESP32)",
                serial_number="CEB-ESP32-98421",
                usb_path="1-1.2:1.0",
                type="serial",
                is_mock=True,
                description="Simulated ESP32 Hardware Controller",
            ),
            gps_path: DetectedUSBDevice(
                device_path=gps_path,
                vendor_id="1546",
                product_id="01A7",
                manufacturer="u-blox AG",
                product="u-blox 7 - GPS/GNSS Receiver",
                serial_number="UBX-GNSS-0021",
                usb_path="1-1.3:1.0",
                type="serial",
                is_mock=True,
                description="Simulated Forensic GPS Receiver",
            ),
        }

    def add_mock_device(self, device: DetectedUSBDevice) -> None:
        device.is_mock = True
        self._mock_devices[device.device_path] = device

    def remove_mock_device(self, device_path: str) -> None:
        self._mock_devices.pop(device_path, None)

    def scan_devices(self) -> List[DetectedUSBDevice]:
        """
        Scans for connected USB devices.
        In 'production' mode: returns only real physical devices.
        In 'mock' mode: returns only simulated devices.
        In 'auto' mode: returns physical devices if detected; falls back to mock devices if none found.
        """
        physical_devices: List[DetectedUSBDevice] = []

        if HAS_PYSERIAL and self.mode != "mock":
            try:
                ports = serial.tools.list_ports.comports()
                for p in ports:
                    vid_str = f"{p.vid:04X}" if p.vid is not None else None
                    pid_str = f"{p.pid:04X}" if p.pid is not None else None

                    dev = DetectedUSBDevice(
                        device_path=p.device,
                        vendor_id=vid_str,
                        product_id=pid_str,
                        manufacturer=p.manufacturer,
                        product=p.product or p.description,
                        serial_number=p.serial_number,
                        usb_path=p.location,
                        type="serial",
                        is_mock=False,
                        description=p.description,
                    )
                    physical_devices.append(dev)
            except Exception as e:
                logger.error(f"Error scanning serial ports: {e}")

        if self.mode == "production":
            return physical_devices

        if self.mode == "mock":
            return list(self._mock_devices.values())

        # In "auto" mode:
        if physical_devices:
            return physical_devices
        # Fallback to mock for seamless local development
        return list(self._mock_devices.values())
