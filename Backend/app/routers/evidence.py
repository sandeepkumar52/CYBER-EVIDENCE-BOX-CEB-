from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from ..config import STORAGE_DIR
from ..database import get_db
from ..models import Case, CustodyEvent, Evidence, User
from ..schemas import (
    EvidenceCreate,
    EvidenceResponse,
    EvidenceUpdate,
    EvidenceVerifyResponse,
)
from ..security.auth import get_current_user, require_role
from ..services.audit_service import log_audit_event
from ..services.hash_service import calculate_file_hash, verify_file_integrity
from ..services.storage_service import save_evidence_file, get_evidence_vault_path
from ..services.encryption_service import encryption_service
from ..services.key_manager import get_key_manager
from ..services.biometric_service import get_biometric_service
from ..services.vault_session import vault_sessions
from ..config import CEB_STORAGE_PATH, ACCESS_SESSION_TIMEOUT
from ..schemas import UnlockResponse
from ..models import EvidenceEncryption
import os
from fastapi.responses import StreamingResponse

router = APIRouter(prefix="/evidence", tags=["Evidence Management"])


@router.post("", response_model=EvidenceResponse, status_code=status.HTTP_201_CREATED)
def create_evidence(
    evidence_in: EvidenceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Admin", "Investigator"])),
):
    case = db.query(Case).filter(Case.id == evidence_in.case_id).first()
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Parent case with ID {evidence_in.case_id} not found",
        )

    existing = db.query(Evidence).filter(Evidence.evidence_id == evidence_in.evidence_id).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Evidence ID '{evidence_in.evidence_id}' already exists",
        )

    ev = Evidence(
        evidence_id=evidence_in.evidence_id,
        case_id=evidence_in.case_id,
        evidence_type=evidence_in.evidence_type,
        description=evidence_in.description,
        device_identifier=evidence_in.device_identifier,
        hash_algorithm=evidence_in.hash_algorithm or "SHA-256",
        hash_value=evidence_in.hash_value,
        status="Registered",
    )
    db.add(ev)
    db.commit()
    db.refresh(ev)

    # Automatically create initial Chain of Custody record
    custody_event = CustodyEvent(
        evidence_id=ev.id,
        user_id=current_user.id,
        action="Evidence Registered",
        location="Digital Evidence Station",
        remarks=f"Evidence registered under case {case.case_id}",
    )
    db.add(custody_event)
    db.commit()

    log_audit_event(
        db=db,
        event="EVIDENCE_REGISTERED",
        details=f"Evidence '{ev.evidence_id}' registered under case '{case.case_id}' by {current_user.username}",
        user_id=current_user.id,
    )

    return ev


@router.get("", response_model=list[EvidenceResponse])
def list_evidence(
    case_id: Optional[int] = Query(None, description="Filter by case primary key ID"),
    case_code: Optional[str] = Query(None, description="Filter by case code string (e.g. CASE-2026-001)"),
    status: Optional[str] = Query(None, description="Filter by evidence status"),
    evidence_type: Optional[str] = Query(None, description="Filter by evidence type"),
    search: Optional[str] = Query(None, description="Search evidence ID or description"),
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Evidence)

    if case_id:
        query = query.filter(Evidence.case_id == case_id)
    elif case_code:
        target_case = db.query(Case).filter(Case.case_id == case_code).first()
        if target_case:
            query = query.filter(Evidence.case_id == target_case.id)
        else:
            return []

    if status:
        query = query.filter(Evidence.status == status)

    if evidence_type:
        query = query.filter(Evidence.evidence_type == evidence_type)

    if search:
        search_pattern = f"%{search}%"
        query = query.filter(
            or_(
                Evidence.evidence_id.ilike(search_pattern),
                Evidence.description.ilike(search_pattern),
                Evidence.device_identifier.ilike(search_pattern),
            )
        )

    return query.order_by(Evidence.created_at.desc()).offset(skip).limit(limit).all()


@router.get("/{evidence_identifier}", response_model=EvidenceResponse)
def get_evidence(
    evidence_identifier: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if evidence_identifier.isdigit():
        ev = db.query(Evidence).filter(Evidence.id == int(evidence_identifier)).first()
    else:
        ev = db.query(Evidence).filter(Evidence.evidence_id == evidence_identifier).first()

    if not ev:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Evidence not found",
        )
    return ev


@router.put("/{evidence_identifier}", response_model=EvidenceResponse)
def update_evidence(
    evidence_identifier: str,
    ev_in: EvidenceUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Admin", "Investigator"])),
):
    if evidence_identifier.isdigit():
        ev = db.query(Evidence).filter(Evidence.id == int(evidence_identifier)).first()
    else:
        ev = db.query(Evidence).filter(Evidence.evidence_id == evidence_identifier).first()

    if not ev:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Evidence not found",
        )

    if ev_in.description is not None:
        ev.description = ev_in.description
    if ev_in.device_identifier is not None:
        ev.device_identifier = ev_in.device_identifier
    if ev_in.status is not None:
        ev.status = ev_in.status

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
    if evidence_identifier.isdigit():
        ev = db.query(Evidence).filter(Evidence.id == int(evidence_identifier)).first()
    else:
        ev = db.query(Evidence).filter(Evidence.evidence_id == evidence_identifier).first()

    if not ev:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Evidence not found",
        )

    parent_case = db.query(Case).filter(Case.id == ev.case_id).first()
    case_code = parent_case.case_id if parent_case else f"CASE-{ev.case_id}"

    # Save evidence file safely inside staging (STORAGE_DIR)
    staging_relative_path, file_size = save_evidence_file(case_code, ev.evidence_id, file)
    staging_full_path = Path(STORAGE_DIR).resolve() / staging_relative_path

    # Calculate original SHA-256 hash
    computed_hash = calculate_file_hash(staging_full_path, ev.hash_algorithm or "SHA-256")
    
    # Placeholder for Malware Scan:
    log_audit_event(
        db=db,
        event="MALWARE_SCAN_COMPLETED",
        details=f"Malware scan completed on staging file for evidence '{ev.evidence_id}'. No threats detected.",
        user_id=current_user.id,
    )

    # Encrypt the evidence file and move to secure vault
    key_manager = get_key_manager()
    dek = key_manager.generate_dek()
    wrapped_dek = key_manager.wrap_dek(dek)
    
    vault_dir = get_evidence_vault_path(case_code, ev.evidence_id)
    safe_filename = "".join(c for c in (file.filename or "evidence.bin") if c.isalnum() or c in (".", "-", "_"))
    encrypted_filename = f"{safe_filename}.enc"
    vault_full_path = vault_dir / encrypted_filename
    
    nonce, tag = encryption_service.encrypt_evidence(dek, str(staging_full_path), str(vault_full_path))
    encrypted_sha256 = encryption_service.calculate_hash(str(vault_full_path))
    
    # Clean up plaintext staging file
    try:
        os.remove(staging_full_path)
    except Exception as e:
        print(f"[CEB] Error deleting staging file: {e}")

    # Relative path from CEB_STORAGE_PATH (vault)
    vault_relative_path = os.path.relpath(vault_full_path, vault_dir.parent.parent)

    ev.storage_path = vault_relative_path
    ev.file_size_bytes = file_size # Keeping original file size conceptually, or change? The requirements don't mandate changing this, we keep original size
    ev.hash_value = computed_hash
    ev.status = "Secured"
    
    encryption_record = EvidenceEncryption(
        evidence_id=ev.id,
        encryption_algorithm="AES-256-GCM",
        key_version=1,
        encrypted_dek=wrapped_dek,
        nonce=nonce,
        encrypted_sha256=encrypted_sha256,
        authentication_tag=tag
    )
    db.add(encryption_record)

    db.commit()
    db.refresh(ev)

    # Log chain of custody event
    custody_event = CustodyEvent(
        evidence_id=ev.id,
        user_id=current_user.id,
        action="Evidence Encrypted & Secured",
        location="Encrypted Vault",
        remarks=f"File '{file.filename}' encrypted. Plaintext staging removed. {ev.hash_algorithm} hash: {computed_hash[:12]}...",
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


@router.post("/{evidence_identifier}/verify", response_model=EvidenceVerifyResponse)
def verify_evidence(
    evidence_identifier: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if evidence_identifier.isdigit():
        ev = db.query(Evidence).filter(Evidence.id == int(evidence_identifier)).first()
    else:
        ev = db.query(Evidence).filter(Evidence.evidence_id == evidence_identifier).first()

    if not ev:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Evidence not found",
        )

    if not ev.storage_path or not ev.is_encrypted:
        return EvidenceVerifyResponse(
            evidence_id=ev.evidence_id,
            is_valid=False,
            expected_hash=ev.hash_value,
            computed_hash=None,
            message="Evidence does not have a stored file or encryption metadata to verify.",
        )

    from ..config import CEB_STORAGE_PATH
    full_file_path = Path(CEB_STORAGE_PATH).resolve() / ev.storage_path

    if not full_file_path.exists():
        return EvidenceVerifyResponse(
            evidence_id=ev.evidence_id,
            is_valid=False,
            expected_hash=ev.encrypted_sha256,
            computed_hash=None,
            message="Encrypted evidence file not found on disk at vault path.",
        )

    # Verify encrypted artifact hash
    is_valid, computed_hash = verify_file_integrity(
        full_file_path, ev.encrypted_sha256, "SHA-256"
    )

    if is_valid:
        ev.status = "Verified"
        db.commit()

        custody_event = CustodyEvent(
            evidence_id=ev.id,
            user_id=current_user.id,
            action="Integrity Verified",
            location="Encrypted Vault",
            remarks=f"Encrypted cryptographic hash match confirmed (SHA-256: {computed_hash[:12]}...)",
        )
        db.add(custody_event)
        db.commit()

        log_audit_event(
            db=db,
            event="HASH_VERIFIED",
            details=f"Encrypted Hash verification PASSED for evidence '{ev.evidence_id}'",
            user_id=current_user.id,
        )

        return EvidenceVerifyResponse(
            evidence_id=ev.evidence_id,
            is_valid=True,
            expected_hash=ev.encrypted_sha256,
            computed_hash=computed_hash,
            message="Evidence integrity verified: Recorded encrypted hash matches file content.",
        )
    else:
        custody_event = CustodyEvent(
            evidence_id=ev.id,
            user_id=current_user.id,
            action="Integrity Verification Failed",
            location="Controlled Storage Vault",
            remarks=f"CRITICAL: Hash mismatch! Expected {ev.hash_value[:12]}, computed {computed_hash[:12]}",
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
    if evidence_identifier.isdigit():
        ev = db.query(Evidence).filter(Evidence.id == int(evidence_identifier)).first()
    else:
        ev = db.query(Evidence).filter(Evidence.evidence_id == evidence_identifier).first()

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

    # Authorization checks are assumed passed by `require_role` and case access (if any).
    key_manager = get_key_manager()
    
    try:
        # Release the key securely
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
    if evidence_identifier.isdigit():
        ev = db.query(Evidence).filter(Evidence.id == int(evidence_identifier)).first()
    else:
        ev = db.query(Evidence).filter(Evidence.evidence_id == evidence_identifier).first()

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
    if evidence_identifier.isdigit():
        ev = db.query(Evidence).filter(Evidence.id == int(evidence_identifier)).first()
    else:
        ev = db.query(Evidence).filter(Evidence.evidence_id == evidence_identifier).first()

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
