import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set

from ...config import HARDWARE_MODE, USB_AUTOCONNECT, USB_SCAN_INTERVAL
from .device_registry import device_registry
from .serial_manager import serial_manager
from .usb_detector import DetectedUSBDevice, USBDetector, is_valid_device_path
from .usb_events import hardware_events

logger = logging.getLogger("ceb.hardware.manager")


class USBDeviceManager:
    def __init__(self):
        self.detector = USBDetector(mode=HARDWARE_MODE)
        self.registry = device_registry
        self.serial = serial_manager
        self.events = hardware_events

        self.auto_connect = USB_AUTOCONNECT
        self.scan_interval = USB_SCAN_INTERVAL
        self._scan_task: Optional[asyncio.Task] = None
        self._running = False
        self._known_devices: Dict[str, DetectedUSBDevice] = {}
        self._last_scan_time: Optional[str] = None

    async def start(self) -> None:
        """Start the background USB detector and monitor service."""
        if self._running:
            return
        self._running = True

        # Bind event loop for thread-safe websocket broadcasts
        try:
            loop = asyncio.get_running_loop()
            self.events.set_loop(loop)
        except RuntimeError:
            pass

        logger.info(f"Starting CEB USB Device Manager (mode={self.detector.mode}, auto_connect={self.auto_connect})")
        self._scan_task = asyncio.create_task(self._scan_loop(), name="CEB-USB-Scanner")

    async def stop(self) -> None:
        """Stop the background service and cleanly disconnect all ports."""
        self._running = False
        if self._scan_task:
            self._scan_task.cancel()
            try:
                await self._scan_task
            except asyncio.CancelledError:
                pass

        # Disconnect any open serial ports
        for path in list(self._known_devices.keys()):
            try:
                self.serial.disconnect(path)
            except Exception as e:
                logger.debug(f"Error disconnecting {path} on shutdown: {e}")

        logger.info("CEB USB Device Manager stopped.")

    async def _scan_loop(self) -> None:
        """Continuous background scan for plugged/unplugged USB devices."""
        # Initial scan
        await self.perform_scan()

        while self._running:
            try:
                await asyncio.sleep(self.scan_interval)
                await self.perform_scan()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in USB scan loop: {e}", exc_info=True)
                await asyncio.sleep(self.scan_interval)

    async def perform_scan(self) -> List[Dict[str, Any]]:
        """Scans for devices and updates connections & events."""
        current_list = self.detector.scan_devices()
        current_paths: Set[str] = {d.device_path for d in current_list}
        known_paths: Set[str] = set(self._known_devices.keys())
        self._last_scan_time = datetime.now(timezone.utc).isoformat()

        # Check for newly plugged devices
        new_paths = current_paths - known_paths
        for dev in current_list:
            if dev.device_path in new_paths:
                self._known_devices[dev.device_path] = dev
                profile = self.registry.match_device(
                    dev.vendor_id, dev.product_id, dev.description, dev.product
                )
                role = profile.role if profile else None
                logger.info(f"USB Device Detected: {dev.device_path} (VID={dev.vendor_id}, PID={dev.product_id}, role={role})")

                await self.events.broadcast(
                    "usb:detected",
                    {
                        "device": self._format_device_dict(dev),
                    },
                )

                # Attempt auto-connection if permitted
                should_auto = self.auto_connect and (profile.auto_connect if profile else False)
                if should_auto and not self.serial.is_connected(dev.device_path):
                    try:
                        self.serial.connect(
                            device_path=dev.device_path,
                            baud_rate=profile.baud_rate if profile else 115200,
                            data_bits=profile.data_bits if profile else 8,
                            stop_bits=profile.stop_bits if profile else 1,
                            parity=profile.parity if profile else "none",
                            timeout=profile.timeout if profile else 1.0,
                            is_mock=dev.is_mock,
                            role=role,
                        )
                    except Exception as e:
                        logger.error(f"Auto-connect failed for {dev.device_path}: {e}")

        # Check for unplugged devices
        unplugged_paths = known_paths - current_paths
        for path in unplugged_paths:
            dev = self._known_devices.pop(path, None)
            if self.serial.is_connected(path):
                self.serial.disconnect(path)
            logger.info(f"USB Device Unplugged / Disconnected: {path}")

            await self.events.broadcast(
                "usb:disconnected",
                {
                    "devicePath": path,
                    "status": "disconnected",
                },
            )

        # Handle auto-reconnect for known devices that should be connected
        if self.auto_connect:
            for path, dev in self._known_devices.items():
                profile = self.registry.match_device(
                    dev.vendor_id, dev.product_id, dev.description, dev.product
                )
                if profile and profile.auto_connect and not self.serial.is_connected(path):
                    conn = self.serial.get_connection(path)
                    # If not currently connecting and last attempt wasn't recent
                    if not conn or conn.status in ("disconnected", "error"):
                        try:
                            self.serial.connect(
                                device_path=path,
                                baud_rate=profile.baud_rate,
                                data_bits=profile.data_bits,
                                stop_bits=profile.stop_bits,
                                parity=profile.parity,
                                timeout=profile.timeout,
                                is_mock=dev.is_mock,
                                role=profile.role,
                            )
                        except Exception as e:
                            logger.debug(f"Auto-reconnect attempt for {path} failed: {e}")

        return self.get_all_devices()

    def get_all_devices(self) -> List[Dict[str, Any]]:
        if not self._known_devices:
            for dev in self.detector.scan_devices():
                self._known_devices[dev.device_path] = dev
        result = []
        for path, dev in self._known_devices.items():
            result.append(self._format_device_dict(dev))
        return result

    def get_device(self, device_path: str) -> Optional[Dict[str, Any]]:
        if not self._known_devices:
            for dev in self.detector.scan_devices():
                self._known_devices[dev.device_path] = dev
        dev = self._known_devices.get(device_path)
        if not dev:
            return None
        return self._format_device_dict(dev)


    def _format_device_dict(self, dev: DetectedUSBDevice) -> Dict[str, Any]:
        profile = self.registry.match_device(
            dev.vendor_id, dev.product_id, dev.description, dev.product
        )
        conn = self.serial.get_connection(dev.device_path)
        status = conn.status if conn else "disconnected"

        return {
            "vendorId": dev.vendor_id,
            "productId": dev.product_id,
            "manufacturer": dev.manufacturer,
            "product": dev.product or dev.description,
            "serialNumber": dev.serial_number,
            "devicePath": dev.device_path,
            "usbPath": dev.usb_path,
            "type": dev.type,
            "status": status,
            "isMock": dev.is_mock,
            "matchedRole": profile.role if profile else None,
            "roleName": profile.name if profile else None,
            "baudRate": conn.baud_rate if conn else (profile.baud_rate if profile else 115200),
            "lastData": conn.last_data if conn else None,
            "lastCommunicationTime": conn.last_comm_time if conn else None,
            "error": conn.error if conn else None,
        }

    def connect_device(
        self,
        device_path: str,
        baud_rate: Optional[int] = None,
        data_bits: int = 8,
        stop_bits: int = 1,
        parity: str = "none",
        timeout: float = 1.0,
    ) -> bool:
        if not is_valid_device_path(device_path):
            raise ValueError(f"Invalid device path format: {device_path}")

        dev = self._known_devices.get(device_path)
        profile = None
        is_mock = False

        if dev:
            is_mock = dev.is_mock
            profile = self.registry.match_device(
                dev.vendor_id, dev.product_id, dev.description, dev.product
            )
        elif device_path.startswith("MOCK_"):
            is_mock = True

        effective_baud = baud_rate or (profile.baud_rate if profile else 115200)
        effective_data = data_bits or (profile.data_bits if profile else 8)
        effective_stop = stop_bits or (profile.stop_bits if profile else 1)
        effective_parity = parity or (profile.parity if profile else "none")
        role = profile.role if profile else None

        return self.serial.connect(
            device_path=device_path,
            baud_rate=effective_baud,
            data_bits=effective_data,
            stop_bits=effective_stop,
            parity=effective_parity,
            timeout=timeout,
            is_mock=is_mock,
            role=role,
        )

    def disconnect_device(self, device_path: str) -> bool:
        if not is_valid_device_path(device_path):
            raise ValueError(f"Invalid device path format: {device_path}")
        return self.serial.disconnect(device_path)

    def write_to_device(self, device_path: str, data: str) -> bool:
        if not is_valid_device_path(device_path):
            raise ValueError(f"Invalid device path format: {device_path}")
        return self.serial.write(device_path, data)

    def read_from_device(self, device_path: str, limit: int = 50) -> List[str]:
        if not is_valid_device_path(device_path):
            raise ValueError(f"Invalid device path format: {device_path}")
        return self.serial.read_buffer(device_path, limit)

    def get_subsystem_status(self) -> Dict[str, Any]:
        devices = self.get_all_devices()
        connected_count = sum(1 for d in devices if d["status"] == "connected")

        has_error = any(d["status"] == "error" for d in devices)
        usb_status = "error" if has_error else ("healthy" if devices else "idle")

        return {
            "mode": self.detector.mode,
            "scanActive": self._running,
            "totalDevices": len(devices),
            "connectedCount": connected_count,
            "autoConnect": self.auto_connect,
            "devices": devices,
            "lastScanTime": self._last_scan_time or datetime.now(timezone.utc).isoformat(),
            "system": "healthy",
            "usb": usb_status,
        }

    def get_health(self) -> Dict[str, Any]:
        devices = self.get_all_devices()
        roles_status: Dict[str, str] = {
            "esp32": "disconnected",
            "gps": "disconnected",
            "sensorController": "disconnected",
        }

        for d in devices:
            role = d.get("matchedRole")
            if role:
                roles_status[role] = d.get("status", "disconnected")

        any_error = any(d["status"] == "error" for d in devices)
        usb_health = "error" if any_error else "healthy"

        return {
            "system": "healthy",
            "usb": usb_health,
            "devices": roles_status,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


# Global manager instance
usb_manager = USBDeviceManager()
