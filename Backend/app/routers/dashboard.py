from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import AuditLog, Case, CustodyEvent, Evidence, User
from ..schemas import DashboardStatsResponse
from ..security.auth import get_current_user

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/stats", response_model=DashboardStatsResponse)
def get_dashboard_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    total_cases = db.query(func.count(Case.id)).filter(Case.is_archived == False).scalar() or 0
    active_cases = (
        db.query(func.count(Case.id))
        .filter(Case.status == "Active", Case.is_archived == False)
        .scalar()
        or 0
    )

    total_evidence = db.query(func.count(Evidence.id)).scalar() or 0
    verified_evidence = (
        db.query(func.count(Evidence.id)).filter(Evidence.status == "Verified").scalar() or 0
    )

    storage_used_bytes = (
        db.query(func.sum(Evidence.file_size_bytes)).scalar() or 0
    )

    recent_custody_events = (
        db.query(CustodyEvent)
        .order_by(CustodyEvent.timestamp.desc())
        .limit(5)
        .all()
    )

    recent_audit_logs = (
        db.query(AuditLog)
        .order_by(AuditLog.timestamp.desc())
        .limit(5)
        .all()
    )

    return DashboardStatsResponse(
        total_cases=total_cases,
        active_cases=active_cases,
        total_evidence=total_evidence,
        verified_evidence=verified_evidence,
        storage_used_bytes=storage_used_bytes,
        recent_custody_events=recent_custody_events,
        recent_audit_logs=recent_audit_logs,
    )
