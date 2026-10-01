import asyncio
import logging
import os
import platform
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from ...config import AUTO_EXPORT_TO_USB, USB_SCAN_INTERVAL
from ..usb.usb_events import hardware_events
from .storage_detector import USBStorageDetector, USBStorageDevice
from .storage_exporter import storage_exporter
from .storage_file_manager import storage_file_manager

logger = logging.getLogger("ceb.storage.manager")


class USBStorageManager:
    def __init__(self):
        self.detector = USBStorageDetector()
        self.file_manager = storage_file_manager
        self.exporter = storage_exporter
        self.events = hardware_events

        self.auto_export = AUTO_EXPORT_TO_USB
        self.scan_interval = USB_SCAN_INTERVAL
        self._running = False
        self._scan_task: Optional[asyncio.Task] = None
        self._known_devices: Dict[str, USBStorageDevice] = {}
        self._last_scan_time: Optional[str] = None

    async def start(self) -> None:
        if self._running:
            return
        self._running = True
        logger.info(f"Starting CEB USB Storage Manager (auto_export={self.auto_export})")
        self._scan_task = asyncio.create_task(self._scan_loop(), name="CEB-Storage-Scanner")

    async def stop(self) -> None:
        self._running = False
        if self._scan_task:
            self._scan_task.cancel()
            try:
                await self._scan_task
            except asyncio.CancelledError:
                pass
        logger.info("CEB USB Storage Manager stopped.")

    async def _scan_loop(self) -> None:
        await self.perform_scan()
        while self._running:
            try:
                await asyncio.sleep(self.scan_interval)
                await self.perform_scan()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in USB Storage scan loop: {e}", exc_info=True)
                await asyncio.sleep(self.scan_interval)

    async def perform_scan(self) -> List[Dict[str, Any]]:
        current_list = self.detector.scan_storage_devices()
        current_map = {d.device: d for d in current_list}
        known_devices = set(self._known_devices.keys())
        current_devices = set(current_map.keys())
        self._last_scan_time = datetime.now(timezone.utc).isoformat()

        # Check for newly plugged USB storage devices
        new_devices = current_devices - known_devices
        for dev_path in new_devices:
            dev = current_map[dev_path]
            self._known_devices[dev_path] = dev
            logger.info(f"USB Storage Detected: {dev.name} ({dev.device}) at {dev.mount_point}")

            await self.events.broadcast(
                "storage:connected",
                {
                    "device": dev.to_dict(),
                    "mountPoint": dev.mount_point,
                },
            )

            if dev.mounted:
                await self.events.broadcast(
                    "storage:mounted",
                    {
                        "device": dev.device,
                        "mountPoint": dev.mount_point,
                    },
                )

        # Check for removed USB storage devices
        removed_devices = known_devices - current_devices
        for dev_path in removed_devices:
            dev = self._known_devices.pop(dev_path, None)
            logger.info(f"USB Storage Removed: {dev_path}")

            await self.events.broadcast(
                "storage:removed",
                {
                    "device": dev_path,
                    "status": "removed",
                },
            )

        # Update status/space for existing devices
        for dev_path, dev in current_map.items():
            old = self._known_devices.get(dev_path)
            if old and (old.used_bytes != dev.used_bytes or old.free_bytes != dev.free_bytes):
                self._known_devices[dev_path] = dev
                await self.events.broadcast(
                    "storage:spaceChanged",
                    {
                        "device": dev_path,
                        "usedBytes": dev.used_bytes,
                        "freeBytes": dev.free_bytes,
                        "totalBytes": dev.total_bytes,
                    },
                )

        return self.get_all_devices()

    def scan_storage(self) -> List[Dict[str, Any]]:
        current_list = self.detector.scan_storage_devices()
        self._known_devices = {d.device: d for d in current_list}
        return [d.to_dict() for d in self._known_devices.values()]

    def get_all_devices(self) -> List[Dict[str, Any]]:
        if not self._known_devices:
            self.scan_storage()
        return [d.to_dict() for d in self._known_devices.values()]

    def get_device(self, device_path: str) -> Optional[USBStorageDevice]:
        if not self._known_devices:
            self.scan_storage()
        return self._known_devices.get(device_path)


    def get_status(self) -> Dict[str, Any]:
        devices = self.get_all_devices()
        mounted_count = sum(1 for d in devices if d.get("mounted"))
        total_space = sum(d.get("totalBytes", 0) for d in devices)
        used_space = sum(d.get("usedBytes", 0) for d in devices)
        free_space = sum(d.get("freeBytes", 0) for d in devices)

        return {
            "totalStorageDevices": len(devices),
            "mountedCount": mounted_count,
            "totalBytes": total_space,
            "usedBytes": used_space,
            "freeBytes": free_space,
            "devices": devices,
            "autoExportEnabled": self.auto_export,
            "lastScanTime": self._last_scan_time or datetime.now(timezone.utc).isoformat(),
            "status": "healthy" if devices else "idle",
        }

    def safe_eject(self, device_path: str) -> Dict[str, Any]:
        """
        Safely flushes pending writes and unmounts the USB storage device.
        """
        dev = self._known_devices.get(device_path)
        if not dev:
            # Check if matching device by mountpoint
            dev = next((d for d in self._known_devices.values() if d.mount_point == device_path), None)

        if not dev:
            raise ValueError(f"Storage device '{device_path}' not found")

        self.events.dispatch_from_thread(
            "storage:ejecting",
            {"device": dev.device, "mountPoint": dev.mount_point},
        )

        logger.info(f"Initiating safe eject for USB storage: {dev.device} ({dev.mount_point})")

        # 1. Flush filesystem buffers (sync)
        try:
            if hasattr(os, "sync"):
                os.sync()
        except Exception as e:
            logger.debug(f"Sync call note: {e}")

        # 2. Unmount on Linux if real physical mount
        if platform.system() == "Linux" and dev.mount_point and not dev.is_mock:
            try:
                cmd = ["umount", dev.mount_point]
                res = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
                if res.returncode != 0:
                    # Try lazy unmount if busy
                    subprocess.run(["umount", "-l", dev.mount_point], capture_output=True, text=True, timeout=5)
            except Exception as e:
                logger.error(f"Error executing umount for {dev.mount_point}: {e}")

        # 3. Mark as ejected and unmounted
        dev.mounted = False
        dev.status = "ejected"

        self.events.dispatch_from_thread(
            "storage:ejected",
            {
                "device": dev.device,
                "mountPoint": dev.mount_point,
                "message": "USB READY TO REMOVE",
            },
        )

        return {
            "status": "ejected",
            "device": dev.device,
            "mountPoint": dev.mount_point,
            "message": "USB READY TO REMOVE",
            "readyToRemove": True,
        }


# Global storage manager instance
storage_manager = USBStorageManager()
