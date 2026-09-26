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
from ..services.storage_service import save_evidence_file

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

    # Save evidence file safely inside storage abstraction
    relative_path, file_size = save_evidence_file(case_code, ev.evidence_id, file)

    full_file_path = Path(STORAGE_DIR).resolve() / relative_path

    # Calculate SHA-256 hash automatically upon upload
    computed_hash = calculate_file_hash(full_file_path, ev.hash_algorithm or "SHA-256")

    ev.storage_path = relative_path
    ev.file_size_bytes = file_size
    ev.hash_value = computed_hash
    ev.status = "Acquired"

    db.commit()
    db.refresh(ev)

    # Log chain of custody event
    custody_event = CustodyEvent(
        evidence_id=ev.id,
        user_id=current_user.id,
        action="Evidence Acquired",
        location="Controlled Storage Vault",
        remarks=f"File '{file.filename}' uploaded ({file_size} bytes). {ev.hash_algorithm} hash: {computed_hash[:12]}...",
    )
    db.add(custody_event)
    db.commit()

    log_audit_event(
        db=db,
        event="HASH_CREATED",
        details=f"File uploaded & {ev.hash_algorithm} hash calculated for evidence '{ev.evidence_id}': {computed_hash}",
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

    if not ev.storage_path or not ev.hash_value:
        return EvidenceVerifyResponse(
            evidence_id=ev.evidence_id,
            is_valid=False,
            expected_hash=ev.hash_value,
            computed_hash=None,
            message="Evidence does not have a stored file or recorded hash value to verify.",
        )

    full_file_path = Path(STORAGE_DIR).resolve() / ev.storage_path

    if not full_file_path.exists():
        return EvidenceVerifyResponse(
            evidence_id=ev.evidence_id,
            is_valid=False,
            expected_hash=ev.hash_value,
            computed_hash=None,
            message="Evidence file not found on disk at stored path.",
        )

    is_valid, computed_hash = verify_file_integrity(
        full_file_path, ev.hash_value, ev.hash_algorithm or "SHA-256"
    )

    if is_valid:
        ev.status = "Verified"
        db.commit()

        custody_event = CustodyEvent(
            evidence_id=ev.id,
            user_id=current_user.id,
            action="Integrity Verified",
            location="Controlled Storage Vault",
            remarks=f"Cryptographic hash match confirmed ({ev.hash_algorithm}: {computed_hash[:12]}...)",
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
            message="Evidence integrity verified: Recorded hash matches file content.",
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
