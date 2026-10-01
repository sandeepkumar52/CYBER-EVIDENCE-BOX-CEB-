import logging
import os
import platform
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from ...config import HARDWARE_MODE, MOCK_USB_STORAGE_DIR

logger = logging.getLogger("ceb.storage.detector")

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False


@dataclass
class USBStorageDevice:
    device: str  # e.g. /dev/sda1, E:, MOCK_SDA1
    name: str  # e.g. "SanDisk Ultra 64GB"
    mount_point: Optional[str] = None
    filesystem: Optional[str] = None
    total_bytes: int = 0
    used_bytes: int = 0
    free_bytes: int = 0
    mounted: bool = False
    status: str = "connected"  # "connected", "mounted", "ejected", "error"
    vendor: Optional[str] = None
    model: Optional[str] = None
    serial_number: Optional[str] = None
    read_only: bool = False
    is_mock: bool = False
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "device": self.device,
            "mountPoint": self.mount_point,
            "filesystem": self.filesystem,
            "totalBytes": self.total_bytes,
            "usedBytes": self.used_bytes,
            "freeBytes": self.free_bytes,
            "mounted": self.mounted,
            "status": self.status,
            "vendor": self.vendor,
            "model": self.model,
            "serialNumber": self.serial_number,
            "readOnly": self.read_only,
            "isMock": self.is_mock,
            "error": self.error,
        }


class USBStorageDetector:
    def __init__(self, mode: str = "auto"):
        self.mode = mode.lower()
        self._mock_devices: Dict[str, USBStorageDevice] = {}
        self._init_default_mock_storage()

    def _init_default_mock_storage(self) -> None:
        """Create mock storage folder and device for development & testing."""
        mock_dir = Path(MOCK_USB_STORAGE_DIR).resolve()
        mock_dir.mkdir(parents=True, exist_ok=True)

        # Create sample folders & files inside mock USB storage
        (mock_dir / "CEB_DATA").mkdir(exist_ok=True)
        (mock_dir / "LOGS").mkdir(exist_ok=True)
        (mock_dir / "EXPORTS").mkdir(exist_ok=True)

        sample_config = mock_dir / "configuration.json"
        if not sample_config.exists():
            sample_config.write_text('{"box_id": "CEB-UNIT-01", "firmware": "2.4.0", "encryption": "AES-256"}')

        sample_csv = mock_dir / "sensor_data.csv"
        if not sample_csv.exists():
            sample_csv.write_text("timestamp,temperature,lock_status,tamper_alarm\n2026-09-30T10:00:00Z,23.4,LOCKED,0\n2026-09-30T11:00:00Z,23.8,LOCKED,0\n")

        sample_pdf = mock_dir / "report.pdf"
        if not sample_pdf.exists():
            sample_pdf.write_bytes(b"%PDF-1.4 Mock CEB Forensic Report Header")

        dev_path = "/dev/sda1" if platform.system() != "Windows" else "MOCK_USB_E"
        # Simulate ~64 GB total, ~12 GB used, ~52 GB free
        total_b = 64_000_000_000
        used_b = 12_400_000_000
        free_b = total_b - used_b

        self._mock_devices[dev_path] = USBStorageDevice(
            device=dev_path,
            name="SanDisk Ultra USB 3.0",
            mount_point=str(mock_dir),
            filesystem="exfat",
            total_bytes=total_b,
            used_bytes=used_b,
            free_bytes=free_b,
            mounted=True,
            status="mounted",
            vendor="SanDisk",
            model="Ultra Fit 64GB",
            serial_number="4C530001090123112191",
            read_only=False,
            is_mock=True,
        )

    def add_mock_storage(self, dev: USBStorageDevice) -> None:
        dev.is_mock = True
        self._mock_devices[dev.device] = dev

    def remove_mock_storage(self, device_path: str) -> None:
        self._mock_devices.pop(device_path, None)

    def scan_storage_devices(self) -> List[USBStorageDevice]:
        """
        Detects USB storage devices dynamically.
        On Linux: checks /sys/block/sd*, /proc/mounts, psutil.
        On Windows: checks removable drives.
        In mock/auto mode: includes mock devices when physical pendrives are absent.
        """
        physical_devices: List[USBStorageDevice] = []

        if self.mode != "mock" and HAS_PSUTIL:
            try:
                partitions = psutil.disk_partitions(all=False)
                for part in partitions:
                    is_usb = False
                    is_linux = platform.system() == "Linux"

                    # Linux USB detection
                    if is_linux:
                        # Common mount locations for USB drives
                        if any(part.mountpoint.startswith(p) for p in ["/media", "/mnt", "/run/media"]):
                            is_usb = True
                        elif part.device.startswith("/dev/sd") or part.device.startswith("/dev/nvme"):
                            # Check if removable via sysfs
                            base_block = part.device.replace("/dev/", "")
                            base_disk = "".join([c for c in base_block if not c.isdigit()])
                            removable_file = Path(f"/sys/block/{base_disk}/removable")
                            if removable_file.exists() and removable_file.read_text().strip() == "1":
                                is_usb = True

                    # Windows USB detection
                    elif platform.system() == "Windows":
                        if "removable" in part.opts.lower():
                            is_usb = True

                    if is_usb:
                        # Get usage statistics safely
                        total_b, used_b, free_b = 0, 0, 0
                        try:
                            usage = psutil.disk_usage(part.mountpoint)
                            total_b = usage.total
                            used_b = usage.used
                            free_b = usage.free
                        except Exception as e:
                            logger.debug(f"Could not read disk usage for {part.mountpoint}: {e}")

                        dev_name = f"USB Drive ({part.device})"
                        dev = USBStorageDevice(
                            device=part.device,
                            name=dev_name,
                            mount_point=part.mountpoint,
                            filesystem=part.fstype or "unknown",
                            total_bytes=total_b,
                            used_bytes=used_b,
                            free_bytes=free_b,
                            mounted=bool(part.mountpoint),
                            status="mounted" if part.mountpoint else "connected",
                            read_only="ro" in part.opts.lower(),
                            is_mock=False,
                        )
                        physical_devices.append(dev)
            except Exception as e:
                logger.error(f"Error scanning physical storage devices: {e}")

        if self.mode == "production":
            return physical_devices

        if self.mode == "mock":
            return list(self._mock_devices.values())

        # In "auto" mode:
        if physical_devices:
            return physical_devices
        # Fallback to mock for seamless testing and local development
        return list(self._mock_devices.values())
