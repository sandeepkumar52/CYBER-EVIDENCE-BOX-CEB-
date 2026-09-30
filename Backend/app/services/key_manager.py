import os
import base64
from abc import ABC, abstractmethod
import logging
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

logger = logging.getLogger(__name__)

class KeyManager(ABC):
    @abstractmethod
    def generate_dek(self) -> bytes:
        """Generates a random 32-byte Data Encryption Key."""
        pass

    @abstractmethod
    def wrap_dek(self, dek: bytes) -> bytes:
        """Wraps (encrypts) the DEK using the Key Encryption Key (KEK)."""
        pass

    @abstractmethod
    def unwrap_dek(self, wrapped_dek: bytes) -> bytes:
        """Unwraps (decrypts) the DEK using the Key Encryption Key (KEK)."""
        pass


class DevelopmentKeyManager(KeyManager):
    """
    DEVELOPMENT ONLY. DO NOT USE IN PRODUCTION.
    This uses a local file or environment variable to store a software KEK.
    """
    def __init__(self, key_path: str = ".dev_kek"):
        logger.warning("DEVELOPMENT ONLY: Using DevelopmentKeyManager. This is not secure for production!")
        self.key_path = key_path
        self._kek = self._load_or_generate_kek()

    def _load_or_generate_kek(self) -> bytes:
        if os.environ.get("CEB_DEV_KEK"):
            return base64.b64decode(os.environ["CEB_DEV_KEK"])
        
        if os.path.exists(self.key_path):
            with open(self.key_path, "rb") as f:
                return f.read()
        
        # Generate new KEK for development
        kek = AESGCM.generate_key(bit_length=256)
        with open(self.key_path, "wb") as f:
            f.write(kek)
        return kek

    def generate_dek(self) -> bytes:
        return AESGCM.generate_key(bit_length=256)

    def wrap_dek(self, dek: bytes) -> bytes:
        # Use AES-GCM to wrap the DEK
        aesgcm = AESGCM(self._kek)
        nonce = os.urandom(12)
        ciphertext = aesgcm.encrypt(nonce, dek, None)
        return nonce + ciphertext  # Prepend nonce

    def unwrap_dek(self, wrapped_dek: bytes) -> bytes:
        aesgcm = AESGCM(self._kek)
        nonce = wrapped_dek[:12]
        ciphertext = wrapped_dek[12:]
        return aesgcm.decrypt(nonce, ciphertext, None)


class TPMKeyManager(KeyManager):
    """
    Production TPM 2.0 Key Manager.
    Uses hardware-backed key storage.
    """
    def __init__(self):
        logger.info("Initializing TPMKeyManager.")
        # TPM initialization logic would go here.
        # This is a stub for Raspberry Pi TPM integration.
        # Usually implemented with tpm2-pytss or calling tpm2-tools.
        pass

    def generate_dek(self) -> bytes:
        # In a real TPM environment, you might ask the TPM for random bytes,
        # or use os.urandom.
        return os.urandom(32)

    def wrap_dek(self, dek: bytes) -> bytes:
        # Stub: send DEK to TPM to be sealed/wrapped with the hardware KEK
        raise NotImplementedError("TPM integration requires hardware.")

    def unwrap_dek(self, wrapped_dek: bytes) -> bytes:
        # Stub: send wrapped_dek to TPM to be unsealed/unwrapped
        raise NotImplementedError("TPM integration requires hardware.")


def get_key_manager() -> KeyManager:
    env = os.environ.get("CEB_ENV", "development")
    if env == "production":
        return TPMKeyManager()
    return DevelopmentKeyManager()
