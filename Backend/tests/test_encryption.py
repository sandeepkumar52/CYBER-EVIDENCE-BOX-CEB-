import os
import pytest
from ..app.services.encryption_service import encryption_service
from ..app.services.key_manager import DevelopmentKeyManager

def test_encryption_and_decryption_integrity(tmp_path):
    key_manager = DevelopmentKeyManager(key_path=str(tmp_path / "dev_kek"))
    
    plaintext = b"CONFIDENTIAL EVIDENCE DATA: 12345"
    
    plaintext_path = tmp_path / "evidence.txt"
    ciphertext_path = tmp_path / "evidence.enc"
    decrypted_path = tmp_path / "decrypted.txt"
    
    with open(plaintext_path, "wb") as f:
        f.write(plaintext)
        
    dek = key_manager.generate_dek()
    wrapped_dek = key_manager.wrap_dek(dek)
    
    # Encrypt
    nonce, tag = encryption_service.encrypt_evidence(dek, str(plaintext_path), str(ciphertext_path))
    
    # Clean staging
    os.remove(plaintext_path)
    assert not os.path.exists(plaintext_path)
    
    # Verify we can't read plaintext from ciphertext
    with open(ciphertext_path, "rb") as f:
        cipher_content = f.read()
        assert plaintext not in cipher_content
        
    # Unwrap DEK
    unwrapped_dek = key_manager.unwrap_dek(wrapped_dek)
    assert dek == unwrapped_dek
    
    # Decrypt
    encryption_service.decrypt_evidence(unwrapped_dek, nonce, tag, str(ciphertext_path), str(decrypted_path))
    
    with open(decrypted_path, "rb") as f:
        decrypted = f.read()
        assert decrypted == plaintext

def test_stream_decryption(tmp_path):
    key_manager = DevelopmentKeyManager(key_path=str(tmp_path / "dev_kek"))
    plaintext = b"STREAMING_TEST" * 1000
    
    plaintext_path = tmp_path / "stream.txt"
    ciphertext_path = tmp_path / "stream.enc"
    
    with open(plaintext_path, "wb") as f:
        f.write(plaintext)
        
    dek = key_manager.generate_dek()
    nonce, tag = encryption_service.encrypt_evidence(dek, str(plaintext_path), str(ciphertext_path))
    
    streamed_data = b""
    for chunk in encryption_service.stream_decrypted_evidence(dek, nonce, tag, str(ciphertext_path)):
        streamed_data += chunk
        
    assert streamed_data == plaintext
