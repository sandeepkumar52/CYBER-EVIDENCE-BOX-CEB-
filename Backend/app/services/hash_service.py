import hashlib
from pathlib import Path


def calculate_file_hash(file_path: str | Path, algorithm: str = "SHA-256") -> str:
    path = Path(file_path)
    if not path.is_file():
        raise FileNotFoundError(f"File not found at path: {file_path}")

    alg = algorithm.upper().replace("-", "")
    if alg == "SHA256":
        hasher = hashlib.sha256()
    elif alg == "SHA512":
        hasher = hashlib.sha512()
    elif alg == "MD5":
        hasher = hashlib.md5()
    else:
        hasher = hashlib.sha256()

    with open(path, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)

    return hasher.hexdigest().lower()


def calculate_bytes_hash(data: bytes, algorithm: str = "SHA-256") -> str:
    alg = algorithm.upper().replace("-", "")
    if alg == "SHA512":
        hasher = hashlib.sha512(data)
    elif alg == "MD5":
        hasher = hashlib.md5(data)
    else:
        hasher = hashlib.sha256(data)
    return hasher.hexdigest().lower()


def verify_file_integrity(
    file_path: str | Path,
    expected_hash: str,
    algorithm: str = "SHA-256",
) -> tuple[bool, str]:
    if not expected_hash:
        return False, "No expected hash provided"

    try:
        computed = calculate_file_hash(file_path, algorithm)
        is_valid = computed.lower() == expected_hash.lower()
        return is_valid, computed
    except Exception as e:
        return False, f"Error calculating hash: {str(e)}"
