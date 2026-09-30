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
