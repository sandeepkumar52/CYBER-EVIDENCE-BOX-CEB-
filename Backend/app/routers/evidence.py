from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
import hashlib
import logging
import os

logger = logging.getLogger("ceb.routers.evidence")

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy import or_
from sqlalchemy.orm import Session

from ..config import CEB_STORAGE_PATH, STORAGE_DIR, ACCESS_SESSION_TIMEOUT
from ..database import get_db
from ..models import Case, CustodyEvent, Evidence, EvidenceEncryption, User
from ..schemas import (
    EvidenceCreate,
    EvidenceResponse,
    EvidenceUpdate,
    EvidenceVerifyResponse,
    UnlockResponse,
)
from ..security.auth import get_current_user, require_role
from ..services.audit_service import log_audit_event
from ..services.biometric_service import get_biometric_service
from ..services.encryption_service import encryption_service
from ..services.hash_service import calculate_file_hash, verify_file_integrity
from ..services.key_manager import get_key_manager
from ..services.storage_service import (
    delete_evidence_file,
    get_base_storage_dir,
    get_evidence_vault_path,
    get_vault_storage_dir,
    save_evidence_file,
)
from ..services.vault_session import vault_sessions

router = APIRouter(prefix="/evidence", tags=["Evidence Management"])


def _get_evidence_by_identifier(db: Session, evidence_identifier: str) -> Evidence | None:
    ev = db.query(Evidence).filter(Evidence.evidence_id == evidence_identifier).first()
    if not ev and evidence_identifier.isdigit():
        ev = db.query(Evidence).filter(Evidence.id == int(evidence_identifier)).first()
    return ev


@router.post("", response_model=EvidenceResponse, status_code=status.HTTP_201_CREATED)
def register_evidence(
    evidence_in: EvidenceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Admin", "Investigator"])),
):
    case = db.query(Case).filter(Case.id == evidence_in.case_id).first()
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Associated case not found",
        )

    existing = db.query(Evidence).filter(Evidence.evidence_id == evidence_in.evidence_id).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Evidence ID already exists",
        )

    new_evidence = Evidence(
        evidence_id=evidence_in.evidence_id,
        case_id=evidence_in.case_id,
        evidence_type=evidence_in.evidence_type,
        description=evidence_in.description,
        hash_algorithm=evidence_in.hash_algorithm or "SHA-256",
        hash_value=evidence_in.hash_value,
        status="Registered",
    )
    db.add(new_evidence)
    db.commit()
    db.refresh(new_evidence)

    custody_event = CustodyEvent(
        evidence_id=new_evidence.id,
        user_id=current_user.id,
        action="Registered",
        location="Intake / Digital Lab",
        remarks=f"Initial registration of evidence item {new_evidence.evidence_id}",
    )
    db.add(custody_event)
    db.commit()

    log_audit_event(
        db=db,
        event="EVIDENCE_REGISTERED",
        details=f"Evidence '{new_evidence.evidence_id}' registered by {current_user.username}",
        user_id=current_user.id,
    )

    return new_evidence


@router.get("", response_model=list[EvidenceResponse])
def get_all_evidence(
    case_id: Optional[int] = None,
    evidence_type: Optional[str] = None,
    status: Optional[str] = None,
    search: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Evidence)

    if case_id:
        query = query.filter(Evidence.case_id == case_id)
    if evidence_type:
        query = query.filter(Evidence.evidence_type == evidence_type)
    if status:
        query = query.filter(Evidence.status == status)
    if search:
        search_pattern = f"%{search}%"
        query = query.filter(
            or_(
                Evidence.evidence_id.ilike(search_pattern),
                Evidence.description.ilike(search_pattern),
            )
        )

    return (
        query.order_by(Evidence.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


@router.get("/{evidence_identifier}", response_model=EvidenceResponse)
def get_evidence(
    evidence_identifier: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ev = _get_evidence_by_identifier(db, evidence_identifier)
    if not ev:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Evidence not found",
        )
    return ev


@router.put("/{evidence_identifier}", response_model=EvidenceResponse)
def update_evidence(
    evidence_identifier: str,
    evidence_in: EvidenceUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Admin", "Investigator"])),
):
    ev = _get_evidence_by_identifier(db, evidence_identifier)
    if not ev:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Evidence not found",
        )

    update_data = evidence_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(ev, field, value)

    db.commit()
    db.refresh(ev)

    log_audit_event(
        db=db,
        event="EVIDENCE_UPDATED",
        details=f"Evidence '{ev.evidence_id}' updated by {current_user.username}",
        user_id=current_user.id,
    )

    return ev


@router.post("/{evidence_identifier}/upload", response_model=EvidenceResponse)
def upload_evidence_file(
    evidence_identifier: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Admin", "Investigator"])),
):
    ev = _get_evidence_by_identifier(db, evidence_identifier)
    if not ev:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Evidence not found",
        )

    case = db.query(Case).filter(Case.id == ev.case_id).first()
    case_code = case.case_id if case else "DEFAULT_CASE"

    # 1. Save unencrypted file to staging
    rel_path, size = save_evidence_file(case_code, ev.evidence_id, file)
    staging_file_path = (Path(STORAGE_DIR).resolve() / rel_path).resolve()

    # 2. Compute SHA-256 of plaintext
    plaintext_hash = calculate_file_hash(staging_file_path, "SHA-256")

    # 3. Setup vault directory
    vault_dir = get_evidence_vault_path(case_code, ev.evidence_id)
    vault_file_path = vault_dir / "vault.enc"

    # 4. Generate and wrap DEK
    key_manager = get_key_manager()
    dek = key_manager.generate_dek()
    wrapped_dek = key_manager.wrap_dek(dek)

    # 5. Encrypt file using AES-256-GCM
    nonce, tag = encryption_service.encrypt_evidence(dek, str(staging_file_path), str(vault_file_path))

    # 6. Compute SHA-256 of encrypted ciphertext
    ciphertext_hash = calculate_file_hash(vault_file_path, "SHA-256")

    # 7. Securely delete plaintext from staging
    if os.path.exists(staging_file_path):
        os.remove(staging_file_path)

    # 8. Record in DB
    rel_vault_path = os.path.relpath(vault_file_path, get_vault_storage_dir()).replace("\\", "/")
    ev.storage_path = rel_vault_path
    ev.file_size_bytes = size
    ev.hash_value = plaintext_hash
    ev.hash_algorithm = "SHA-256"
    ev.status = "Acquired"

    # Save or update Encryption metadata
    if ev.encryption_metadata:
        ev.encryption_metadata.encrypted_dek = wrapped_dek
        ev.encryption_metadata.nonce = nonce
        ev.encryption_metadata.authentication_tag = tag
        ev.encryption_metadata.encrypted_sha256 = ciphertext_hash
        ev.encryption_metadata.encrypted_at = datetime.now(timezone.utc)
    else:
        encryption_meta = EvidenceEncryption(
            evidence_id=ev.id,
            encryption_algorithm="AES-256-GCM",
            encrypted_dek=wrapped_dek,
            nonce=nonce,
            authentication_tag=tag,
            encrypted_sha256=ciphertext_hash
        )
        db.add(encryption_meta)

    db.commit()
    db.refresh(ev)

    custody_event = CustodyEvent(
        evidence_id=ev.id,
        user_id=current_user.id,
        action="File Encrypted to Vault",
        location="Digital Evidence Locker",
        remarks=f"Payload encrypted via AES-256-GCM. Plaintext SHA-256: {plaintext_hash[:12]}..., Ciphertext SHA-256: {ciphertext_hash[:12]}...",
    )
    db.add(custody_event)
    db.commit()

    log_audit_event(
        db=db,
        event="EVIDENCE_ENCRYPTED",
        details=f"Evidence '{ev.evidence_id}' encrypted via AES-256-GCM and stored in vault",
        user_id=current_user.id,
    )

    return ev


@router.get("/{evidence_identifier}/download")
def download_evidence_file(
    evidence_identifier: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ev = _get_evidence_by_identifier(db, evidence_identifier)
    if not ev:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Evidence not found",
        )

    if not ev.storage_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No file stored for this evidence",
        )

    # If encrypted, decrypt on the fly for authorized user
    if ev.is_encrypted and ev.encryption_metadata:
        key_manager = get_key_manager()
        try:
            dek = key_manager.unwrap_dek(ev.encryption_metadata.encrypted_dek)
        except Exception:
            dek = vault_sessions.get_session_dek(ev.id, current_user.id)

        if not dek:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Access denied. Unable to decrypt vault payload.",
            )

        vault_full_path = (Path(CEB_STORAGE_PATH).resolve() / ev.storage_path).resolve()
        if not vault_full_path.is_file():
            raise HTTPException(status_code=404, detail="Encrypted payload missing on disk")

        log_audit_event(db, "EVIDENCE_DOWNLOADED", f"Evidence '{ev.evidence_id}' decrypted and downloaded by {current_user.username}", current_user.id)

        filename = ev.description or f"{ev.evidence_id}.bin"
        return StreamingResponse(
            encryption_service.stream_decrypted_evidence(
                dek=dek,
                nonce=ev.encryption_metadata.nonce,
                tag=ev.encryption_metadata.authentication_tag,
                ciphertext_path=str(vault_full_path)
            ),
            media_type="application/octet-stream",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'}
        )

    # Unencrypted fallback file
    full_file_path = (get_base_storage_dir() / ev.storage_path).resolve()
    if not full_file_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Evidence file not found on disk",
        )

    return FileResponse(
        path=str(full_file_path),
        filename=full_file_path.name,
        media_type="application/octet-stream",
    )


@router.delete("/{evidence_identifier}", status_code=status.HTTP_200_OK)
def delete_evidence(
    evidence_identifier: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Admin"])),
):
    ev = _get_evidence_by_identifier(db, evidence_identifier)
    if not ev:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Evidence not found",
        )

    evidence_id_str = ev.evidence_id
    if ev.storage_path:
        if ev.is_encrypted:
            try:
                vpath = (get_vault_storage_dir() / ev.storage_path).resolve()
                if vpath.is_file():
                    vpath.unlink()
                    parent = vpath.parent
                    if parent != get_vault_storage_dir() and not any(parent.iterdir()):
                        parent.rmdir()
            except Exception as e:
                print(f"[CEB Vault] Deletion note: {e}")
        else:
            delete_evidence_file(ev.storage_path)

    db.delete(ev)
    db.commit()

    log_audit_event(
        db=db,
        event="EVIDENCE_DELETED",
        details=f"Evidence '{evidence_id_str}' deleted by Admin {current_user.username}",
        user_id=current_user.id,
    )

    return {"message": f"Evidence '{evidence_id_str}' deleted successfully"}


@router.post("/{evidence_identifier}/verify", response_model=EvidenceVerifyResponse)
def verify_evidence(
    evidence_identifier: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ev = _get_evidence_by_identifier(db, evidence_identifier)
    if not ev:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Evidence not found",
        )

    if not ev.storage_path:
        return EvidenceVerifyResponse(
            evidence_id=ev.evidence_id,
            is_valid=False,
            expected_hash=ev.hash_value,
            computed_hash=None,
            message="Evidence does not have a stored file to verify.",
        )

    # 1. Handle Encrypted Vault Evidence
    if ev.is_encrypted and ev.encryption_metadata:
        full_file_path = (Path(CEB_STORAGE_PATH).resolve() / ev.storage_path).resolve()
        if not full_file_path.is_file():
            return EvidenceVerifyResponse(
                evidence_id=ev.evidence_id,
                is_valid=False,
                expected_hash=ev.hash_value,
                computed_hash=None,
                message="Encrypted evidence file not found on disk at vault path.",
            )

        # Verify encrypted ciphertext integrity
        expected_cipher_hash = ev.encryption_metadata.encrypted_sha256 or ev.encrypted_sha256
        cipher_valid, computed_cipher_hash = verify_file_integrity(
            full_file_path, expected_cipher_hash, "SHA-256"
        )
        if not cipher_valid:
            custody_event = CustodyEvent(
                evidence_id=ev.id,
                user_id=current_user.id,
                action="Integrity Verification Failed",
                location="Controlled Storage Vault",
                remarks=f"CRITICAL: Ciphertext hash mismatch! Expected {expected_cipher_hash[:12] if expected_cipher_hash else 'N/A'}, computed {computed_cipher_hash[:12]}",
            )
            db.add(custody_event)
            db.commit()

            log_audit_event(
                db=db,
                event="HASH_MISMATCH_DETECTED",
                details=f"Ciphertext hash verification FAILED for evidence '{ev.evidence_id}'. Expected {expected_cipher_hash}, got {computed_cipher_hash}",
                user_id=current_user.id,
            )
            return EvidenceVerifyResponse(
                evidence_id=ev.evidence_id,
                is_valid=False,
                expected_hash=ev.hash_value,
                computed_hash=computed_cipher_hash,
                message="INTEGRITY ALERT: Vault ciphertext hash verification failed! File content has changed.",
            )

        # Verify decrypted plaintext hash against original acquisition hash
        try:
            key_mgr = get_key_manager()
            dek = key_mgr.unwrap_dek(ev.encryption_metadata.encrypted_dek)
            hasher = hashlib.sha256()
            for chunk in encryption_service.stream_decrypted_evidence(
                dek=dek,
                nonce=ev.encryption_metadata.nonce,
                tag=ev.encryption_metadata.authentication_tag,
                ciphertext_path=str(full_file_path),
            ):
                hasher.update(chunk)
            computed_plaintext_hash = hasher.hexdigest().lower()
            expected_plaintext_hash = (ev.hash_value or "").strip().lower()

            if computed_plaintext_hash == expected_plaintext_hash:
                ev.status = "Verified"
                db.commit()

                custody_event = CustodyEvent(
                    evidence_id=ev.id,
                    user_id=current_user.id,
                    action="Integrity Verified",
                    location="Encrypted Vault",
                    remarks=f"Cryptographic hash match confirmed (SHA-256: {computed_plaintext_hash[:12]}...)",
                )
                db.add(custody_event)
                db.commit()

                log_audit_event(
                    db=db,
                    event="HASH_VERIFIED",
                    details=f"Decrypted plaintext hash verification PASSED for evidence '{ev.evidence_id}'",
                    user_id=current_user.id,
                )

                return EvidenceVerifyResponse(
                    evidence_id=ev.evidence_id,
                    is_valid=True,
                    expected_hash=ev.hash_value,
                    computed_hash=computed_plaintext_hash,
                    message="Evidence integrity verified: Vault ciphertext and decrypted plaintext SHA-256 match recorded forensic hashes.",
                )
            else:
                custody_event = CustodyEvent(
                    evidence_id=ev.id,
                    user_id=current_user.id,
                    action="Integrity Verification Failed",
                    location="Controlled Storage Vault",
                    remarks=f"CRITICAL: Plaintext hash mismatch! Expected {expected_plaintext_hash[:12]}, computed {computed_plaintext_hash[:12]}",
                )
                db.add(custody_event)
                db.commit()

                log_audit_event(
                    db=db,
                    event="HASH_MISMATCH_DETECTED",
                    details=f"Decrypted plaintext hash verification FAILED for evidence '{ev.evidence_id}'. Expected {expected_plaintext_hash}, got {computed_plaintext_hash}",
                    user_id=current_user.id,
                )

                return EvidenceVerifyResponse(
                    evidence_id=ev.evidence_id,
                    is_valid=False,
                    expected_hash=ev.hash_value,
                    computed_hash=computed_plaintext_hash,
                    message="INTEGRITY ALERT: Decrypted plaintext hash verification failed! Original content modified.",
                )
        except Exception as e:
            logger.error(f"Error during decrypted verification of {ev.evidence_id}: {e}")
            return EvidenceVerifyResponse(
                evidence_id=ev.evidence_id,
                is_valid=False,
                expected_hash=ev.hash_value,
                computed_hash=None,
                message=f"Decryption verification error: {str(e)}",
            )

    # 2. Handle Unencrypted Storage Evidence
    unenc_file_path = (get_base_storage_dir() / ev.storage_path).resolve()
    if not unenc_file_path.is_file():
        return EvidenceVerifyResponse(
            evidence_id=ev.evidence_id,
            is_valid=False,
            expected_hash=ev.hash_value,
            computed_hash=None,
            message="Evidence file not found on disk at storage path.",
        )

    is_valid, computed_hash = verify_file_integrity(
        unenc_file_path, ev.hash_value or "", ev.hash_algorithm or "SHA-256"
    )

    if is_valid:
        ev.status = "Verified"
        db.commit()

        custody_event = CustodyEvent(
            evidence_id=ev.id,
            user_id=current_user.id,
            action="Integrity Verified",
            location="Storage Locker",
            remarks=f"Cryptographic hash match confirmed (SHA-256: {computed_hash[:12]}...)",
        )
        db.add(custody_event)
        db.commit()

        log_audit_event(
            db=db,
            event="HASH_VERIFIED",
            details=f"Hash verification PASSED for evidence '{ev.evidence_id}'",
            user_id=current_user.id,
        )

        return EvidenceVerifyResponse(
            evidence_id=ev.evidence_id,
            is_valid=True,
            expected_hash=ev.hash_value,
            computed_hash=computed_hash,
            message="Evidence integrity verified: Recorded SHA-256 matches file content.",
        )
    else:
        custody_event = CustodyEvent(
            evidence_id=ev.id,
            user_id=current_user.id,
            action="Integrity Verification Failed",
            location="Storage Locker",
            remarks=f"CRITICAL: Hash mismatch! Expected {ev.hash_value[:12] if ev.hash_value else 'N/A'}, computed {computed_hash[:12]}",
        )
        db.add(custody_event)
        db.commit()

        log_audit_event(
            db=db,
            event="HASH_MISMATCH_DETECTED",
            details=f"Hash verification FAILED for evidence '{ev.evidence_id}'. Expected {ev.hash_value}, got {computed_hash}",
            user_id=current_user.id,
        )

        return EvidenceVerifyResponse(
            evidence_id=ev.evidence_id,
            is_valid=False,
            expected_hash=ev.hash_value,
            computed_hash=computed_hash,
            message="INTEGRITY ALERT: Hash verification failed! File content has changed.",
        )


@router.post("/{evidence_identifier}/unlock", response_model=UnlockResponse)
def unlock_evidence(
    evidence_identifier: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Admin", "Investigator"])),
):
    ev = _get_evidence_by_identifier(db, evidence_identifier)
    if not ev or not ev.is_encrypted:
        raise HTTPException(status_code=400, detail="Evidence not found or not encrypted")

    biometric_service = get_biometric_service()

    log_audit_event(db, "BIOMETRIC_AUTH_STARTED", f"Biometric auth requested for user {current_user.id}", current_user.id)

    # Biometric Challenge
    is_verified = biometric_service.verify_user(current_user.id)
    if not is_verified:
        log_audit_event(db, "BIOMETRIC_AUTH_FAILED", f"Biometric verification failed for user {current_user.id}", current_user.id)
        raise HTTPException(status_code=403, detail="Biometric Authentication Failed")

    log_audit_event(db, "BIOMETRIC_AUTH_SUCCESS", f"Biometric verification succeeded for user {current_user.id}", current_user.id)

    key_manager = get_key_manager()

    try:
        dek = key_manager.unwrap_dek(ev.encryption_metadata.encrypted_dek)
        vault_sessions.create_session(ev.id, current_user.id, dek, timeout_minutes=ACCESS_SESSION_TIMEOUT)

        log_audit_event(db, "EVIDENCE_ACCESS_REQUESTED", f"Evidence '{ev.evidence_id}' unlocked securely for {ACCESS_SESSION_TIMEOUT} minutes.", current_user.id)

        return UnlockResponse(
            evidence_id=ev.evidence_id,
            unlocked=True,
            message=f"Evidence unlocked for {ACCESS_SESSION_TIMEOUT} minutes.",
            expires_in_minutes=ACCESS_SESSION_TIMEOUT
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to unwrap DEK securely.")


@router.post("/{evidence_identifier}/lock")
def lock_evidence(
    evidence_identifier: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ev = _get_evidence_by_identifier(db, evidence_identifier)
    if not ev:
        raise HTTPException(status_code=404, detail="Evidence not found")

    revoked = vault_sessions.revoke_session(ev.id, current_user.id)
    if revoked:
        log_audit_event(db, "EVIDENCE_LOCKED", f"Evidence '{ev.evidence_id}' locked. Session terminated.", current_user.id)
        return {"status": "locked", "message": "Evidence session successfully terminated and memory wiped."}
    return {"status": "unlocked", "message": "No active session found to lock."}


@router.get("/{evidence_identifier}/stream")
def stream_evidence(
    evidence_identifier: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Admin", "Investigator"])),
):
    ev = _get_evidence_by_identifier(db, evidence_identifier)
    if not ev or not ev.is_encrypted:
        raise HTTPException(status_code=404, detail="Evidence not found or not encrypted")

    dek = vault_sessions.get_session_dek(ev.id, current_user.id)
    if not dek:
        log_audit_event(db, "EVIDENCE_ACCESS_EXPIRED", f"Unauthorized or expired access attempt for '{ev.evidence_id}' stream.", current_user.id)
        raise HTTPException(status_code=401, detail="Access denied. Biometric authentication required or session expired.")

    vault_full_path = Path(CEB_STORAGE_PATH).resolve() / ev.storage_path
    if not vault_full_path.exists():
        raise HTTPException(status_code=404, detail="Encrypted payload missing.")

    log_audit_event(db, "EVIDENCE_VIEWED", f"Evidence '{ev.evidence_id}' being streamed to viewer.", current_user.id)

    return StreamingResponse(
        encryption_service.stream_decrypted_evidence(
            dek=dek,
            nonce=ev.encryption_metadata.nonce,
            tag=ev.encryption_metadata.authentication_tag,
            ciphertext_path=str(vault_full_path)
        ),
        media_type="application/octet-stream"
    )
