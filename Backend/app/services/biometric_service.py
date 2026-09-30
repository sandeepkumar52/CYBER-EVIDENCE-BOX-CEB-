import os
import time
import logging
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class BiometricService(ABC):
    @abstractmethod
    def verify_user(self, user_id: int) -> bool:
        """
        Initiates a biometric verification challenge for the user.
        Returns True if biometric verification succeeds, False otherwise.
        """
        pass

    @abstractmethod
    def enroll_user(self, user_id: int) -> bool:
        """
        Enrolls a user's biometric data.
        """
        pass

    @abstractmethod
    def remove_user(self, user_id: int) -> bool:
        """
        Removes a user's biometric data from the sensor.
        """
        pass


class DevelopmentBiometricService(BiometricService):
    """
    DEVELOPMENT ONLY. NOT REAL BIOMETRIC AUTHENTICATION.
    This simulates biometric hardware for testing the application workflow.
    """
    def __init__(self):
        logger.warning("DEVELOPMENT ONLY: Using DevelopmentBiometricService. This provides NO real biometric security.")

    def verify_user(self, user_id: int) -> bool:
        logger.info(f"[DEV BIOMETRICS] Simulating fingerprint read for user {user_id}...")
        time.sleep(1) # Simulate hardware delay
        # In a real dev environment, we might reject some or accept based on a flag,
        # but for the CEB workflow, we simulate a successful scan if the user exists.
        logger.info(f"[DEV BIOMETRICS] Simulated fingerprint match successful for user {user_id}.")
        return True

    def enroll_user(self, user_id: int) -> bool:
        logger.info(f"[DEV BIOMETRICS] Simulating enrollment for user {user_id}.")
        return True

    def remove_user(self, user_id: int) -> bool:
        logger.info(f"[DEV BIOMETRICS] Simulating removal for user {user_id}.")
        return True


class LinuxBiometricService(BiometricService):
    """
    Production Biometric Service for Linux / Raspberry Pi.
    Uses libfprint or PAM integration for actual hardware fingerprint verification.
    """
    def __init__(self):
        logger.info("Initializing LinuxBiometricService with hardware fingerprint scanner.")
        # Hardware initialization goes here

    def verify_user(self, user_id: int) -> bool:
        # Stub: Call out to fprintd / libfprint or a custom PAM stack
        # to request a real fingerprint swipe.
        raise NotImplementedError("Real Linux biometric hardware integration is pending.")

    def enroll_user(self, user_id: int) -> bool:
        raise NotImplementedError("Real Linux biometric hardware integration is pending.")

    def remove_user(self, user_id: int) -> bool:
        raise NotImplementedError("Real Linux biometric hardware integration is pending.")


def get_biometric_service() -> BiometricService:
    env = os.environ.get("CEB_ENV", "development")
    if env == "production":
        return LinuxBiometricService()
    return DevelopmentBiometricService()
