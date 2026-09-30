import os
from pathlib import Path
from fastapi import HTTPException, UploadFile, status
from ..config import STORAGE_DIR, CEB_STORAGE_PATH


def get_base_storage_dir() -> Path:
    storage_path = Path(STORAGE_DIR).resolve()
    storage_path.mkdir(parents=True, exist_ok=True)
    return storage_path


def validate_storage_path(target_path: Path) -> Path:
    base_dir = get_base_storage_dir()
    resolved_target = target_path.resolve()
    if not str(resolved_target).startswith(str(base_dir)):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid storage path: Path traversal detected",
        )
    return resolved_target


def save_evidence_file(case_id: str, evidence_id: str, upload_file: UploadFile) -> tuple[str, int]:
    base_dir = get_base_storage_dir()
    
    # Safe sanitization of directory identifiers
    safe_case = "".join(c for c in case_id if c.isalnum() or c in ("-", "_"))
    safe_evidence = "".join(c for c in evidence_id if c.isalnum() or c in ("-", "_"))
    safe_filename = "".join(c for c in (upload_file.filename or "evidence.bin") if c.isalnum() or c in (".", "-", "_"))

    target_dir = base_dir / safe_case / safe_evidence
    target_dir.mkdir(parents=True, exist_ok=True)

    file_path = validate_storage_path(target_dir / safe_filename)

    file_size = 0
    with open(file_path, "wb") as buffer:
        while chunk := upload_file.file.read(65536):
            buffer.write(chunk)
            file_size += len(chunk)

    relative_path = os.path.relpath(file_path, base_dir)
    return relative_path, file_size

def get_vault_storage_dir() -> Path:
    vault_path = Path(CEB_STORAGE_PATH).resolve()
    vault_path.mkdir(parents=True, exist_ok=True)
    return vault_path


def validate_vault_path(target_path: Path) -> Path:
    base_dir = get_vault_storage_dir()
    resolved_target = target_path.resolve()
    if not str(resolved_target).startswith(str(base_dir)):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid vault path: Path traversal detected",
        )
    return resolved_target


def get_evidence_vault_path(case_id: str, evidence_id: str) -> Path:
    base_dir = get_vault_storage_dir()
    
    safe_case = "".join(c for c in str(case_id) if c.isalnum() or c in ("-", "_"))
    safe_evidence = "".join(c for c in str(evidence_id) if c.isalnum() or c in ("-", "_"))

    target_dir = base_dir / safe_case / safe_evidence
    target_dir.mkdir(parents=True, exist_ok=True)

    return target_dir
