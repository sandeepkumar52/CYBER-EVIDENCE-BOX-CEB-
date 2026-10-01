import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from ...config import USB_DEVICE_REGISTRY_PATH

logger = logging.getLogger("ceb.hardware.registry")

DEFAULT_REGISTRY: Dict[str, Dict[str, Any]] = {
    "esp32": {
        "name": "CEB Sensor & Hardware Controller (ESP32)",
        "type": "serial",
        "vendorId": "10C4",
        "productId": "EA60",
        "secondaryIds": [
            {"vendorId": "1A86", "productId": "7523"},
            {"vendorId": "0403", "productId": "6001"},
            {"vendorId": "303A", "productId": "1001"},
            {"vendorId": "303A", "productId": "0002"},
        ],
        "baudRate": 115200,
        "dataBits": 8,
        "stopBits": 1,
        "parity": "none",
        "timeout": 1.0,
        "autoConnect": True,
        "reconnectAttempts": 5,
        "description": "Embedded controller for electronic locks, tamper sensors, and hardware status",
    },
    "gps": {
        "name": "Forensic GNSS/GPS Geolocation Module",
        "type": "serial",
        "vendorId": "1546",
        "productId": "01A7",
        "secondaryIds": [
            {"vendorId": "1546", "productId": "01A8"},
            {"vendorId": "067B", "productId": "2303"},
        ],
        "baudRate": 9600,
        "dataBits": 8,
        "stopBits": 1,
        "parity": "none",
        "timeout": 1.0,
        "autoConnect": True,
        "reconnectAttempts": 5,
        "description": "NMEA GNSS receiver for chain-of-custody timestamping and geolocation tagging",
    },
    "sensor_controller": {
        "name": "Auxiliary Sensor & GPIO Interface",
        "type": "serial",
        "vendorId": "2341",
        "productId": "0043",
        "secondaryIds": [
            {"vendorId": "2341", "productId": "0042"},
            {"vendorId": "2E8A", "productId": "000A"},
        ],
        "baudRate": 115200,
        "dataBits": 8,
        "stopBits": 1,
        "parity": "none",
        "timeout": 1.0,
        "autoConnect": False,
        "reconnectAttempts": 3,
        "description": "Secondary environmental temperature, humidity, and chassis interlock sensor",
    },
}


@dataclass
class DeviceProfile:
    role: str
    name: str
    type: str = "serial"
    vendor_id: Optional[str] = None
    product_id: Optional[str] = None
    secondary_ids: List[Dict[str, str]] = field(default_factory=list)
    baud_rate: int = 115200
    data_bits: int = 8
    stop_bits: int = 1
    parity: str = "none"
    timeout: float = 1.0
    auto_connect: bool = True
    reconnect_attempts: int = 5
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "role": self.role,
            "name": self.name,
            "type": self.type,
            "vendorId": self.vendor_id,
            "productId": self.product_id,
            "secondaryIds": self.secondary_ids,
            "baudRate": self.baud_rate,
            "dataBits": self.data_bits,
            "stopBits": self.stop_bits,
            "parity": self.parity,
            "timeout": self.timeout,
            "autoConnect": self.auto_connect,
            "reconnectAttempts": self.reconnect_attempts,
            "description": self.description,
        }


class DeviceRegistry:
    def __init__(self, config_path: Optional[str] = None):
        self.config_path = Path(config_path or USB_DEVICE_REGISTRY_PATH)
        self.profiles: Dict[str, DeviceProfile] = {}
        self.reload()

    def reload(self) -> None:
        raw_data = DEFAULT_REGISTRY.copy()
        if self.config_path.is_file():
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                    if isinstance(loaded, dict):
                        raw_data.update(loaded)
                        logger.info(f"Loaded {len(loaded)} device profiles from {self.config_path}")
            except Exception as e:
                logger.warning(f"Could not load custom device registry from {self.config_path}: {e}")

        self.profiles = {}
        for role, item in raw_data.items():
            self.profiles[role] = DeviceProfile(
                role=role,
                name=item.get("name", role.upper()),
                type=item.get("type", "serial"),
                vendor_id=str(item.get("vendorId", "")).upper() if item.get("vendorId") else None,
                product_id=str(item.get("productId", "")).upper() if item.get("productId") else None,
                secondary_ids=item.get("secondaryIds", []),
                baud_rate=int(item.get("baudRate", 115200)),
                data_bits=int(item.get("dataBits", 8)),
                stop_bits=int(item.get("stopBits", 1)),
                parity=item.get("parity", "none"),
                timeout=float(item.get("timeout", 1.0)),
                auto_connect=bool(item.get("autoConnect", True)),
                reconnect_attempts=int(item.get("reconnectAttempts", 5)),
                description=item.get("description", ""),
            )

    def get_profile(self, role: str) -> Optional[DeviceProfile]:
        return self.profiles.get(role)

    def match_device(
        self,
        vendor_id: Optional[str],
        product_id: Optional[str],
        description: Optional[str] = None,
        product: Optional[str] = None,
    ) -> Optional[DeviceProfile]:
        v_id = str(vendor_id).upper().strip() if vendor_id else ""
        p_id = str(product_id).upper().strip() if product_id else ""

        # Exact match VID + PID against primary and secondary
        if v_id and p_id:
            for profile in self.profiles.values():
                if profile.vendor_id == v_id and profile.product_id == p_id:
                    return profile
                for sec in profile.secondary_ids:
                    s_vid = str(sec.get("vendorId", "")).upper().strip()
                    s_pid = str(sec.get("productId", "")).upper().strip()
                    if s_vid == v_id and s_pid == p_id:
                        return profile

        # Fallback keyword match in description/product
        combined_text = f"{description or ''} {product or ''}".lower()
        if "gps" in combined_text or "gnss" in combined_text or "u-blox" in combined_text:
            return self.profiles.get("gps")
        if "esp32" in combined_text or "cp210" in combined_text or "ch340" in combined_text:
            return self.profiles.get("esp32")

        return None

    def all_profiles(self) -> Dict[str, Any]:
        return {k: v.to_dict() for k, v in self.profiles.items()}


# Global instance
device_registry = DeviceRegistry()
