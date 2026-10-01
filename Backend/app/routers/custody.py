from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import CustodyEvent, Evidence, User
from ..schemas import CustodyEventCreate, CustodyEventResponse
from ..security.auth import get_current_user, require_role
from ..services.audit_service import log_audit_event

router = APIRouter(tags=["Chain of Custody"])


def _get_evidence_by_identifier(db: Session, evidence_identifier: str) -> Evidence | None:
    ev = db.query(Evidence).filter(Evidence.evidence_id == evidence_identifier).first()
    if not ev and evidence_identifier.isdigit():
        ev = db.query(Evidence).filter(Evidence.id == int(evidence_identifier)).first()
    return ev


@router.post(
    "/evidence/{evidence_identifier}/custody",
    response_model=CustodyEventResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_custody_event(
    evidence_identifier: str,
    event_in: CustodyEventCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Admin", "Investigator"])),
):
    ev = _get_evidence_by_identifier(db, evidence_identifier)
    if not ev:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Evidence not found",
        )

    custody_event = CustodyEvent(
        evidence_id=ev.id,
        user_id=current_user.id,
        action=event_in.action,
        location=event_in.location,
        remarks=event_in.remarks,
    )
    db.add(custody_event)

    # Automatically update evidence status if action is custody transfer or security
    if "secured" in event_in.action.lower():
        ev.status = "Secured"
    elif "transfer" in event_in.action.lower():
        ev.status = "Transferred"
    elif "archive" in event_in.action.lower():
        ev.status = "Archived"

    db.commit()
    db.refresh(custody_event)

    log_audit_event(
        db=db,
        event="CUSTODY_EVENT_CREATED",
        details=f"Custody event '{event_in.action}' logged for evidence '{ev.evidence_id}' by {current_user.username}",
        user_id=current_user.id,
    )

    return custody_event


@router.get(
    "/evidence/{evidence_identifier}/custody",
    response_model=list[CustodyEventResponse],
)
def get_custody_history(
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

    return (
        db.query(CustodyEvent)
        .filter(CustodyEvent.evidence_id == ev.id)
        .order_by(CustodyEvent.timestamp.asc())
        .all()
    )


@router.get(
    "/custody",
    response_model=list[CustodyEventResponse],
)
def get_all_custody_history(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return (
        db.query(CustodyEvent)
        .order_by(CustodyEvent.timestamp.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
