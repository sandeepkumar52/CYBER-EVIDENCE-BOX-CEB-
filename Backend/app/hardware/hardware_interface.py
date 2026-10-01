from typing import Dict, Any, Optional, Tuple
from .usb.usb_manager import usb_manager


def parse_nmea_coordinates(nmea_data: Optional[str]) -> Tuple[Optional[float], Optional[float], bool]:
    """
    Parses standard NMEA sentences ($GPGGA, $GNGGA, $GPRMC, $GNRMC) to extract real GPS coordinates.
    Returns (latitude, longitude, has_fix).
    If no valid fix exists or data is unavailable, returns (None, None, False).
    """
    if not nmea_data or not isinstance(nmea_data, str):
        return None, None, False

    try:
        # Sentence could be embedded in buffer string or multiple lines
        lines = nmea_data.strip().splitlines()
        for line in reversed(lines):
            line = line.strip()
            # Handle potential trailing brackets or tags
            if "[" in line and "]" in line:
                line = line.split("[")[0].strip()

            if line.startswith(("$GPGGA", "$GNGGA")):
                parts = line.split(",")
                if len(parts) >= 6:
                    fix_quality = parts[6] if len(parts) > 6 and parts[6] != "" else "0"
                    if fix_quality == "0":
                        return None, None, False

                    raw_lat, lat_dir = parts[2], parts[3]
                    raw_lon, lon_dir = parts[4], parts[5]

                    if raw_lat and raw_lon and len(raw_lat) >= 4 and len(raw_lon) >= 5:
                        lat_deg = float(raw_lat[:2]) + float(raw_lat[2:]) / 60.0
                        if lat_dir.upper() == "S":
                            lat_deg = -lat_deg
                        lon_deg = float(raw_lon[:3]) + float(raw_lon[3:]) / 60.0
                        if lon_dir.upper() == "W":
                            lon_deg = -lon_deg
                        return round(lat_deg, 6), round(lon_deg, 6), True

            elif line.startswith(("$GPRMC", "$GNRMC")):
                parts = line.split(",")
                if len(parts) >= 7:
                    status = parts[2].upper()
                    if status != "A":  # 'A' = Active/Valid fix, 'V' = Void/No fix
                        return None, None, False

                    raw_lat, lat_dir = parts[3], parts[4]
                    raw_lon, lon_dir = parts[5], parts[6]

                    if raw_lat and raw_lon and len(raw_lat) >= 4 and len(raw_lon) >= 5:
                        lat_deg = float(raw_lat[:2]) + float(raw_lat[2:]) / 60.0
                        if lat_dir.upper() == "S":
                            lat_deg = -lat_deg
                        lon_deg = float(raw_lon[:3]) + float(raw_lon[3:]) / 60.0
                        if lon_dir.upper() == "W":
                            lon_deg = -lon_deg
                        return round(lat_deg, 6), round(lon_deg, 6), True
    except Exception:
        pass

    return None, None, False


class HardwareInterface:
    def get_status(self) -> Dict[str, Any]:
        """Return the current status of the hardware."""
        raise NotImplementedError


class CEBHardwareManager(HardwareInterface):
    def get_status(self) -> Dict[str, Any]:
        usb_status = usb_manager.get_subsystem_status()
        devices = usb_status.get("devices", [])

        gps_device = next(
            (d for d in devices if d.get("matchedRole") == "gps" or "gps" in str(d.get("product", "")).lower()),
            None,
        )
        esp32_device = next(
            (d for d in devices if d.get("matchedRole") == "esp32" or "esp32" in str(d.get("product", "")).lower()),
            None,
        )
        sensor_device = next(
            (d for d in devices if d.get("matchedRole") == "sensor_controller"),
            None,
        )

        gps_connected = gps_device is not None and gps_device.get("status") == "connected"
        esp32_connected = esp32_device is not None and esp32_device.get("status") == "connected"

        # Parse real GPS fix from hardware telemetry (NO hard-coded coordinates in production code)
        gps_last_data = gps_device.get("lastData") if gps_device else None
        lat, lon, has_fix = parse_nmea_coordinates(gps_last_data) if gps_connected else (None, None, False)

        gps_status_label = "disconnected"
        if gps_connected:
            gps_status_label = "locked" if has_fix else "searching_fix"

        return {
            "connected": usb_status.get("connectedCount", 0) > 0,
            "device": esp32_device.get("product") if esp32_device else (devices[0]["product"] if devices else None),
            "mode": usb_status.get("mode"),
            "usb": {
                "total": usb_status.get("totalDevices", 0),
                "connected": usb_status.get("connectedCount", 0),
                "status": usb_status.get("usb", "idle"),
            },
            "gps": {
                "available": gps_connected,
                "status": gps_status_label,
                "devicePath": gps_device.get("devicePath") if gps_device else None,
                "latitude": lat,
                "longitude": lon,
                "hasFix": has_fix,
                "lastData": gps_last_data,
            },
            "esp32": {
                "available": esp32_connected,
                "status": esp32_device.get("status") if esp32_device else "disconnected",
                "devicePath": esp32_device.get("devicePath") if esp32_device else None,
                "lastData": esp32_device.get("lastData") if esp32_device else None,
            },
            "sensor": {
                "available": esp32_connected or (sensor_device is not None and sensor_device.get("status") == "connected"),
                "tamper": False,
                "lockEngaged": True,
            },
            "gpio": {
                "available": True,
                "driver": "rpi.gpio" if usb_status.get("mode") == "production" else "simulated",
            },
        }


# Global hardware instance backwards-compatible with previous router
hardware_manager = CEBHardwareManager()
