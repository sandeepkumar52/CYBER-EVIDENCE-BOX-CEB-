from typing import Dict, Any

class HardwareInterface:
    def get_status(self) -> Dict[str, Any]:
        """Return the current status of the hardware."""
        raise NotImplementedError

class MockHardware(HardwareInterface):
    def get_status(self) -> Dict[str, Any]:
        return {
            "connected": False,
            "device": None,
            "gps": {
                "available": False,
                "latitude": None,
                "longitude": None
            },
            "sensor": {
                "available": False
            }
        }

# Global hardware instance
hardware_manager = MockHardware()
