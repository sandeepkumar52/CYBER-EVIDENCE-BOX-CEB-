from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import AuditLog, User
from ..schemas import AuditLogResponse
from ..security.auth import get_current_user, require_role

router = APIRouter(prefix="/audit-logs", tags=["Audit Logging"])


@router.get("", response_model=list[AuditLogResponse])
def list_audit_logs(
    user_id: Optional[int] = Query(None, description="Filter by user ID"),
    event: Optional[str] = Query(None, description="Filter by event action code"),
    search: Optional[str] = Query(None, description="Search event or details"),
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Admin", "Investigator"])),
):
    query = db.query(AuditLog)

    if user_id:
        query = query.filter(AuditLog.user_id == user_id)

    if event:
        query = query.filter(AuditLog.event == event)

    if search:
        pattern = f"%{search}%"
        query = query.filter(
            (AuditLog.event.ilike(pattern)) | (AuditLog.details.ilike(pattern))
        )

    return query.order_by(AuditLog.timestamp.desc()).offset(skip).limit(limit).all()
