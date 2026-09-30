import os
import hashlib
from typing import Tuple
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

class EncryptionService:
    @staticmethod
    def generate_data_key() -> bytes:
        """Generate a random 32-byte (256-bit) Data Encryption Key (DEK)."""
        return os.urandom(32)

    @staticmethod
    def calculate_hash(file_path: str, algorithm: str = 'SHA-256') -> str:
        """Calculate the hash of a file."""
        if algorithm.upper() != 'SHA-256':
            raise ValueError(f"Unsupported hash algorithm: {algorithm}")
        
        sha256 = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(64 * 1024), b""):
                sha256.update(chunk)
        return sha256.hexdigest()

    @staticmethod
    def encrypt_evidence(dek: bytes, plaintext_path: str, ciphertext_path: str) -> Tuple[bytes, bytes]:
        """
        Encrypts a file using AES-256-GCM in a streaming manner.
        Returns (nonce, authentication_tag).
        """
        nonce = os.urandom(12) # 96-bit nonce
        encryptor = Cipher(
            algorithms.AES(dek),
            modes.GCM(nonce)
        ).encryptor()

        with open(plaintext_path, 'rb') as f_in, open(ciphertext_path, 'wb') as f_out:
            while True:
                chunk = f_in.read(64 * 1024)
                if len(chunk) == 0:
                    break
                f_out.write(encryptor.update(chunk))
            f_out.write(encryptor.finalize())
            tag = encryptor.tag
            
        return nonce, tag

    @staticmethod
    def decrypt_evidence(dek: bytes, nonce: bytes, tag: bytes, ciphertext_path: str, plaintext_path: str) -> None:
        """
        Decrypts a file using AES-256-GCM in a streaming manner.
        Raises cryptography.exceptions.InvalidTag if authentication fails.
        """
        decryptor = Cipher(
            algorithms.AES(dek),
            modes.GCM(nonce, tag)
        ).decryptor()

        with open(ciphertext_path, 'rb') as f_in, open(plaintext_path, 'wb') as f_out:
            while True:
                chunk = f_in.read(64 * 1024)
                if len(chunk) == 0:
                    break
                f_out.write(decryptor.update(chunk))
            f_out.write(decryptor.finalize())

    @staticmethod
    def stream_decrypted_evidence(dek: bytes, nonce: bytes, tag: bytes, ciphertext_path: str):
        """
        Generator that yields decrypted chunks of evidence for streaming.
        Raises cryptography.exceptions.InvalidTag if authentication fails upon finalization.
        """
        decryptor = Cipher(
            algorithms.AES(dek),
            modes.GCM(nonce, tag)
        ).decryptor()

        with open(ciphertext_path, 'rb') as f_in:
            while True:
                chunk = f_in.read(64 * 1024)
                if len(chunk) == 0:
                    break
                yield decryptor.update(chunk)
            yield decryptor.finalize()

encryption_service = EncryptionService()
