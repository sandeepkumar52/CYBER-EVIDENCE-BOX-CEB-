import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv("SECRET_KEY", "ceb-super-secret-key-change-in-production-2026")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))

DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR}/ceb.db")

# Staging path for unencrypted evidence during acquisition
STORAGE_DIR = os.getenv("STORAGE_DIR", str(BASE_DIR / "storage" / "staging"))

# Encrypted Vault path
CEB_STORAGE_PATH = os.getenv("CEB_STORAGE_PATH", str(BASE_DIR / "storage" / "vault"))

ACCESS_SESSION_TIMEOUT = int(os.getenv("ACCESS_SESSION_TIMEOUT", "10"))
CEB_ENV = os.getenv("CEB_ENV", "development")

CORS_ORIGINS = os.getenv(
    "CORS_ORIGINS",
    "http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000"
).split(",")

# Hardware & USB Subsystem Configuration
HARDWARE_MODE = os.getenv("HARDWARE_MODE", "auto").lower()  # "auto", "mock", "production"
USB_DEVICE_REGISTRY_PATH = os.getenv(
    "USB_DEVICE_REGISTRY_PATH",
    str(BASE_DIR / "app" / "hardware" / "device_registry.json")
)
USB_SCAN_INTERVAL = float(os.getenv("USB_SCAN_INTERVAL", "2.0"))
USB_AUTOCONNECT = os.getenv("USB_AUTOCONNECT", "true").lower() in ("true", "1", "yes")
AUTO_EXPORT_TO_USB = os.getenv("AUTO_EXPORT_TO_USB", "false").lower() in ("true", "1", "yes")
USB_STORAGE_MOUNT_BASE = os.getenv("USB_STORAGE_MOUNT_BASE", "/media/usb")
MOCK_USB_STORAGE_DIR = os.getenv("MOCK_USB_STORAGE_DIR", str(BASE_DIR / "storage" / "mock_usb"))
