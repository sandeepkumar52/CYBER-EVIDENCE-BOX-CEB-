import json
import logging
import os
import platform
import shutil
import subprocess
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
    device: str  # e.g. /dev/sda1, /dev/sdb1, E:, MOCK_SDA1
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
    removable: bool = True
    is_mock: bool = False
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "device": self.device,
            "mountPoint": self.mount_point,
            "mount_point": self.mount_point,
            "filesystem": self.filesystem,
            "totalBytes": self.total_bytes,
            "total_bytes": self.total_bytes,
            "usedBytes": self.used_bytes,
            "used_bytes": self.used_bytes,
            "freeBytes": self.free_bytes,
            "free_bytes": self.free_bytes,
            "mounted": self.mounted,
            "status": self.status,
            "vendor": self.vendor,
            "model": self.model,
            "serialNumber": self.serial_number,
            "serial_number": self.serial_number,
            "readOnly": self.read_only,
            "read_only": self.read_only,
            "removable": self.removable,
            "isMock": self.is_mock,
            "is_mock": self.is_mock,
            "error": self.error,
        }


class USBStorageDetector:
    def __init__(self, mode: str = HARDWARE_MODE):
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
            removable=True,
            is_mock=True,
        )

    def add_mock_storage(self, dev: USBStorageDevice) -> None:
        dev.is_mock = True
        self._mock_devices[dev.device] = dev

    def remove_mock_storage(self, device_path: str) -> None:
        self._mock_devices.pop(device_path, None)

    def _scan_linux_lsblk(self) -> List[USBStorageDevice]:
        """Query block devices on Linux/Raspberry Pi using lsblk JSON output."""
        devices: List[USBStorageDevice] = []
        try:
            cmd = [
                "lsblk",
                "-J",
                "-b",
                "-o",
                "NAME,KNAME,PATH,TYPE,SIZE,FSAVAIL,FSSIZE,FSTYPE,MOUNTPOINT,LABEL,MODEL,SERIAL,VENDOR,RO,RM,HOTPLUG,TRAN",
            ]
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=4)
            if res.returncode != 0 or not res.stdout.strip():
                return []

            data = json.loads(res.stdout)
            block_devices = data.get("blockdevices", [])

            for bd in block_devices:
                is_usb_bus = str(bd.get("tran", "")).lower() == "usb"
                is_removable = bool(bd.get("rm")) or bool(bd.get("hotplug"))
                dev_path = bd.get("path") or f"/dev/{bd.get('name')}"

                # Check if removable via sysfs if flag wasn't direct
                if not is_removable and not is_usb_bus:
                    disk_name = "".join([c for c in bd.get("kname", "") if not c.isdigit()])
                    removable_file = Path(f"/sys/block/{disk_name}/removable")
                    if removable_file.exists():
                        try:
                            if removable_file.read_text().strip() == "1":
                                is_removable = True
                        except Exception:
                            pass

                # If this block device is not removable or USB, ignore internal root drive (e.g. mmcblk0)
                if not is_usb_bus and not is_removable:
                    continue

                vendor = (bd.get("vendor") or "").strip() or None
                model = (bd.get("model") or "").strip() or None
                serial = (bd.get("serial") or "").strip() or None
                base_name = f"{vendor} {model}".strip() if vendor or model else f"USB Storage ({dev_path})"

                children = bd.get("children", [])
                if children:
                    # Device has partitions (e.g., /dev/sda1, /dev/sda2)
                    for child in children:
                        c_path = child.get("path") or f"/dev/{child.get('name')}"
                        c_mount = child.get("mountpoint")
                        c_fstype = child.get("fstype")
                        c_size = int(child.get("size") or 0)
                        c_fssize = int(child.get("fssize") or 0)
                        c_fsavail = int(child.get("fsavail") or 0)
                        c_ro = bool(child.get("ro"))
                        c_label = child.get("label")

                        total_b = c_fssize or c_size
                        free_b = c_fsavail
                        used_b = max(0, total_b - free_b) if total_b and free_b is not None else 0

                        # If mounted, query psutil for exact filesystem metrics
                        if c_mount and HAS_PSUTIL and os.path.exists(c_mount):
                            try:
                                u = psutil.disk_usage(c_mount)
                                total_b = u.total
                                used_b = u.used
                                free_b = u.free
                            except Exception:
                                pass

                        part_name = f"{c_label} ({c_path})" if c_label else f"{base_name} ({c_path})"

                        dev = USBStorageDevice(
                            device=c_path,
                            name=part_name,
                            mount_point=c_mount,
                            filesystem=c_fstype or "unknown",
                            total_bytes=total_b,
                            used_bytes=used_b,
                            free_bytes=free_b,
                            mounted=bool(c_mount),
                            status="mounted" if c_mount else "connected",
                            vendor=vendor,
                            model=model,
                            serial_number=serial,
                            read_only=c_ro,
                            removable=True,
                            is_mock=False,
                        )
                        devices.append(dev)
                else:
                    # Unpartitioned raw drive (e.g. /dev/sda)
                    mount_p = bd.get("mountpoint")
                    fstype = bd.get("fstype")
                    size_b = int(bd.get("size") or 0)
                    fssize_b = int(bd.get("fssize") or 0)
                    fsavail_b = int(bd.get("fsavail") or 0)
                    ro = bool(bd.get("ro"))

                    total_b = fssize_b or size_b
                    free_b = fsavail_b
                    used_b = max(0, total_b - free_b) if total_b and free_b is not None else 0

                    if mount_p and HAS_PSUTIL and os.path.exists(mount_p):
                        try:
                            u = psutil.disk_usage(mount_p)
                            total_b = u.total
                            used_b = u.used
                            free_b = u.free
                        except Exception:
                            pass

                    dev = USBStorageDevice(
                        device=dev_path,
                        name=base_name,
                        mount_point=mount_p,
                        filesystem=fstype or "unknown",
                        total_bytes=total_b,
                        used_bytes=used_b,
                        free_bytes=free_b,
                        mounted=bool(mount_p),
                        status="mounted" if mount_p else "connected",
                        vendor=vendor,
                        model=model,
                        serial_number=serial,
                        read_only=ro,
                        removable=True,
                        is_mock=False,
                    )
                    devices.append(dev)
        except Exception as e:
            logger.debug(f"[STORAGE] Note during lsblk scan: {e}")

        return devices

    def scan_storage_devices(self) -> List[USBStorageDevice]:
        """
        Detects USB storage devices dynamically.
        On Linux: checks lsblk, /sys/block, /proc/mounts, psutil.
        On Windows: checks removable drives.
        In mock/auto mode: includes mock devices when physical pendrives are absent.
        """
        physical_devices: List[USBStorageDevice] = []

        if self.mode != "mock":
            if platform.system() == "Linux":
                physical_devices = self._scan_linux_lsblk()

            # Fallback or supplementary check via psutil
            if not physical_devices and HAS_PSUTIL:
                try:
                    partitions = psutil.disk_partitions(all=True)
                    for part in partitions:
                        is_usb = False
                        is_linux = platform.system() == "Linux"

                        if is_linux:
                            if any(part.mountpoint.startswith(p) for p in ["/media", "/mnt", "/run/media", "/var/lib/ceb/mounts"]):
                                is_usb = True
                            elif part.device.startswith("/dev/sd") or part.device.startswith("/dev/nvme"):
                                base_block = part.device.replace("/dev/", "")
                                base_disk = "".join([c for c in base_block if not c.isdigit()])
                                removable_file = Path(f"/sys/block/{base_disk}/removable")
                                if removable_file.exists():
                                    try:
                                        if removable_file.read_text().strip() == "1":
                                            is_usb = True
                                    except Exception:
                                        pass
                        elif platform.system() == "Windows":
                            if "removable" in part.opts.lower() or "cdrom" not in part.opts.lower() and part.device not in ("C:\\", "c:\\"):
                                if "fixed" not in part.opts.lower():
                                    is_usb = True

                        if is_usb and part.device:
                            total_b, used_b, free_b = 0, 0, 0
                            if part.mountpoint and os.path.exists(part.mountpoint):
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
                                mount_point=part.mountpoint or None,
                                filesystem=part.fstype or "unknown",
                                total_bytes=total_b,
                                used_bytes=used_b,
                                free_bytes=free_b,
                                mounted=bool(part.mountpoint),
                                status="mounted" if part.mountpoint else "connected",
                                read_only="ro" in part.opts.lower(),
                                removable=True,
                                is_mock=False,
                            )
                            # Avoid duplicates
                            if not any(d.device == dev.device for d in physical_devices):
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

