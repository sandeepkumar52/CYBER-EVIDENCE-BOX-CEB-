import os
import time
import threading
import logging
import asyncio
import subprocess
import hashlib
import mimetypes
import uuid
from typing import Optional, Dict, Any, List
from pathlib import Path
from ..websocket_manager import ws_manager

logger = logging.getLogger(__name__)

class USBService:
    def __init__(self):
        self.is_linux = os.name == 'posix'
        self.running = False
        self.monitor_thread: Optional[threading.Thread] = None

    def start_monitoring(self):
        if self.running:
            return
        self.running = True
        
        if self.is_linux:
            self.monitor_thread = threading.Thread(target=self._linux_monitor, daemon=True)
        else:
            self.monitor_thread = threading.Thread(target=self._mock_monitor, daemon=True)
            
        self.monitor_thread.start()
        logger.info("USB monitoring started.")

    def stop_monitoring(self):
        self.running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=2)
            
    def _broadcast_event_sync(self, event_data: dict):
        # We need to run the async broadcast in the main event loop
        # FastAPI typically runs in an event loop, but threading here means we have to bridge it.
        # A simpler way is to just create a new task in the main loop if we can get it,
        # but since we don't have direct access to the uvicorn loop from a generic thread,
        # we can use asyncio.run (which blocks) or better, we can inject an event queue.
        # For simplicity in this implementation, we will use a global async queue or directly run.
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(ws_manager.broadcast(event_data))
        except RuntimeError:
            # No running event loop in this thread, use a new one temporarily to broadcast
            asyncio.run(ws_manager.broadcast(event_data))

    def _linux_monitor(self):
        """Uses pyudev to monitor block devices on Linux/Raspberry Pi."""
        try:
            import pyudev
            context = pyudev.Context()
            monitor = pyudev.Monitor.from_netlink(context)
            monitor.filter_by(subsystem='block')
            
            logger.info("pyudev monitor initialized.")
            
            for device in iter(monitor.poll, None):
                if not self.running:
                    break
                    
                # We only care about partitions (e.g. sda1) or full disks that are removable
                if device.device_type in ['partition', 'disk']:
                    if device.action == 'add':
                        vendor = device.get('ID_VENDOR', 'Unknown Vendor')
                        model = device.get('ID_MODEL', 'Unknown Model')
                        
                        # Filter out loopback devices or non-usb
                        if 'usb' not in device.get('ID_BUS', ''):
                            continue
                            
                        event_data = {
                            "event": "usb_connected",
                            "device_id": device.device_node,
                            "vendor": vendor,
                            "model": model,
                            "capacity": device.get('ID_PART_ENTRY_SIZE', 'Unknown'), # Needs block size conversion for bytes
                            "filesystem": device.get('ID_FS_TYPE', 'Unknown'),
                        }
                        logger.info(f"USB Inserted: {event_data}")
                        self._broadcast_event_sync(event_data)
                        
                    elif device.action == 'remove':
                        if 'usb' not in device.get('ID_BUS', ''):
                            continue
                            
                        event_data = {
                            "event": "usb_removed",
                            "device_id": device.device_node
                        }
                        logger.info(f"USB Removed: {event_data}")
                        self._broadcast_event_sync(event_data)
        except ImportError:
            logger.error("pyudev not installed. Cannot monitor USB events on Linux.")
        except Exception as e:
            logger.error(f"Error in Linux USB monitor: {e}")

    def _mock_monitor(self):
        """DEVELOPMENT ONLY: Mock USB insertion for non-Linux systems (Windows/Mac)."""
        logger.warning("DEVELOPMENT ONLY: Using mock USB monitor.")
        # In a real dev scenario, we might trigger this via an API endpoint for testing.
        # Here we just wait a few seconds and trigger a fake USB insertion for UI testing.
        time.sleep(10)
        if self.running:
            event_data = {
                "event": "usb_connected",
                "device_id": "/dev/sda1",
                "vendor": "SanDisk (MOCK)",
                "model": "Ultra (MOCK)",
                "capacity": 32000000000,
                "filesystem": "exFAT"
            }
            logger.info(f"[DEV] Mock USB Inserted: {event_data}")
            self._broadcast_event_sync(event_data)
            
            time.sleep(60)
            if self.running:
                event_data = {
                    "event": "usb_removed",
                    "device_id": "/dev/sda1"
                }
                logger.info(f"[DEV] Mock USB Removed: {event_data}")
                self._broadcast_event_sync(event_data)

    def mount_usb(self, device_id: str) -> str:
        """Mounts the given device read-only and returns the mount point."""
        # Sanitize device_id somewhat
        if ".." in device_id or not device_id.startswith("/dev/"):
            if self.is_linux:
                raise ValueError("Invalid device path.")

        mount_id = str(uuid.uuid4())
        base_mount = os.getenv("CEB_MOUNT_PATH", "/var/lib/ceb/mounts")
        mount_point = os.path.join(base_mount, mount_id)
        
        os.makedirs(mount_point, exist_ok=True)
        
        if self.is_linux:
            # Mount read-only
            try:
                subprocess.run(["sudo", "mount", "-o", "ro", device_id, mount_point], check=True)
                logger.info(f"Mounted {device_id} at {mount_point} (Read-Only)")
            except subprocess.CalledProcessError as e:
                logger.error(f"Failed to mount {device_id}: {e}")
                raise RuntimeError(f"Mount failed: {e}")
        else:
            # Development: just use a local dummy folder
            logger.warning("[DEV] Mock mounting USB. Creating dummy files.")
            with open(os.path.join(mount_point, "evidence.txt"), "w") as f:
                f.write("CONFIDENTIAL EVIDENCE: HACKER LOGS")
            with open(os.path.join(mount_point, "suspicious.exe"), "w") as f:
                f.write("MZ... \x00\x00 MALWARE")
            
        return mount_point

    def unmount_usb(self, mount_point: str):
        if self.is_linux:
            try:
                subprocess.run(["sudo", "umount", mount_point], check=True)
                logger.info(f"Unmounted {mount_point}")
                os.rmdir(mount_point)
            except Exception as e:
                logger.error(f"Unmount failed: {e}")
        else:
            logger.info(f"[DEV] Mock unmount {mount_point}")

    def scan_filesystem(self, mount_point: str) -> List[Dict[str, Any]]:
        """Scans the mounted filesystem and returns a list of files with metadata, hash, and malware scan."""
        files_data = []
        
        for root, dirs, files in os.walk(mount_point):
            for file in files:
                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, mount_point)
                
                try:
                    stat = os.stat(full_path)
                    
                    # Calculate SHA-256
                    sha256 = hashlib.sha256()
                    with open(full_path, 'rb') as f:
                        for chunk in iter(lambda: f.read(64 * 1024), b""):
                            sha256.update(chunk)
                    
                    file_hash = sha256.hexdigest()
                    
                    # Mock Malware Scan
                    malware_status = "Clean"
                    if "suspicious.exe" in file or file.endswith(".exe"):
                        malware_status = "THREAT DETECTED (Mock ClamAV)"
                        
                    mime_type, _ = mimetypes.guess_type(full_path)
                    
                    files_data.append({
                        "name": file,
                        "relative_path": rel_path,
                        "size": stat.st_size,
                        "mime_type": mime_type or "application/octet-stream",
                        "extension": os.path.splitext(file)[1],
                        "created_time": stat.st_ctime,
                        "modified_time": stat.st_mtime,
                        "sha256": file_hash,
                        "malware_status": malware_status,
                        "full_path": full_path # Internal use only
                    })
                except Exception as e:
                    logger.error(f"Error scanning file {full_path}: {e}")
                    
        return files_data

usb_service = USBService()
