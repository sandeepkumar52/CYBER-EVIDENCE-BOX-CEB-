from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Case, Evidence, User
from ..schemas import CaseCreate, CaseResponse, CaseUpdate
from ..security.auth import get_current_user, require_role
from ..services.audit_service import log_audit_event

router = APIRouter(prefix="/cases", tags=["Case Management"])


def _get_case_by_identifier(db: Session, case_identifier: str) -> Case | None:
    c = db.query(Case).filter(Case.case_id == case_identifier).first()
    if not c and case_identifier.isdigit():
        c = db.query(Case).filter(Case.id == int(case_identifier)).first()
    return c


@router.post("", response_model=CaseResponse, status_code=status.HTTP_201_CREATED)
def create_case(
    case_in: CaseCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Admin", "Investigator"])),
):
    existing = db.query(Case).filter(Case.case_id == case_in.case_id).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Case ID already exists",
        )

    creator_id = current_user.id
    if case_in.created_by and current_user.role == "Admin":
        target_user = db.query(User).filter(User.id == case_in.created_by).first()
        if target_user:
            creator_id = target_user.id

    new_case = Case(
        case_id=case_in.case_id,
        case_name=case_in.case_name,
        description=case_in.description,
        status=case_in.status,
        created_by=creator_id,
    )
    db.add(new_case)
    db.commit()
    db.refresh(new_case)

    log_audit_event(
        db=db,
        event="CASE_CREATED",
        details=f"Case '{new_case.case_id}' ({new_case.case_name}) created by {current_user.username}",
        user_id=current_user.id,
    )

    new_case.evidence_count = 0
    return new_case


@router.get("", response_model=list[CaseResponse])
def list_cases(
    search: Optional[str] = Query(None, description="Search in case ID or name"),
    status: Optional[str] = Query(None, description="Filter by case status"),
    include_archived: bool = Query(False, description="Include archived cases"),
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Case)

    if status == "Archived":
        query = query.filter((Case.is_archived == True) | (Case.status == "Archived"))
    elif status:
        query = query.filter(Case.status == status)
        if not include_archived:
            query = query.filter((Case.is_archived == False) | (Case.is_archived.is_(None)))
    elif not include_archived:
        query = query.filter((Case.is_archived == False) | (Case.is_archived.is_(None)))

    if search:
        search_pattern = f"%{search}%"
        query = query.filter(
            or_(
                Case.case_id.ilike(search_pattern),
                Case.case_name.ilike(search_pattern),
                Case.description.ilike(search_pattern),
            )
        )

    cases = query.order_by(Case.created_at.desc()).offset(skip).limit(limit).all()

    # Calculate evidence count for each case
    for c in cases:
        ev_count = db.query(func.count(Evidence.id)).filter(Evidence.case_id == c.id).scalar()
        c.evidence_count = ev_count or 0

    return cases


@router.get("/{case_identifier}", response_model=CaseResponse)
def get_case(
    case_identifier: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    c = _get_case_by_identifier(db, case_identifier)
    if not c:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Case not found",
        )

    ev_count = db.query(func.count(Evidence.id)).filter(Evidence.case_id == c.id).scalar()
    c.evidence_count = ev_count or 0
    return c


@router.put("/{case_identifier}", response_model=CaseResponse)
def update_case(
    case_identifier: str,
    case_in: CaseUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Admin", "Investigator"])),
):
    c = _get_case_by_identifier(db, case_identifier)
    if not c:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Case not found",
        )

    if case_in.case_name is not None:
        c.case_name = case_in.case_name
    if case_in.description is not None:
        c.description = case_in.description
    if case_in.status is not None:
        c.status = case_in.status
    if case_in.is_archived is not None:
        c.is_archived = case_in.is_archived
        if case_in.is_archived:
            c.status = "Archived"

    db.commit()
    db.refresh(c)

    log_audit_event(
        db=db,
        event="CASE_UPDATED",
        details=f"Case '{c.case_id}' updated by {current_user.username}",
        user_id=current_user.id,
    )

    ev_count = db.query(func.count(Evidence.id)).filter(Evidence.case_id == c.id).scalar()
    c.evidence_count = ev_count or 0
    return c


@router.delete("/{case_identifier}", response_model=CaseResponse)
def archive_case(
    case_identifier: str,
    permanent: bool = Query(False, description="Permanently delete case and cascade evidence"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Admin"])),
):
    c = _get_case_by_identifier(db, case_identifier)
    if not c:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Case not found",
        )

    if permanent:
        case_id_str = c.case_id
        db.delete(c)
        db.commit()

        log_audit_event(
            db=db,
            event="CASE_DELETED",
            details=f"Case '{case_id_str}' permanently deleted by Admin {current_user.username}",
            user_id=current_user.id,
        )
        return c

    c.is_archived = True
    c.status = "Archived"
    db.commit()
    db.refresh(c)

    log_audit_event(
        db=db,
        event="CASE_ARCHIVED",
        details=f"Case '{c.case_id}' archived by Admin {current_user.username}",
        user_id=current_user.id,
    )

    ev_count = db.query(func.count(Evidence.id)).filter(Evidence.case_id == c.id).scalar()
    c.evidence_count = ev_count or 0
    return c
