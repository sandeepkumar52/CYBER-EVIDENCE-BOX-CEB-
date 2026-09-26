from sqlalchemy.orm import Session
from ..models import AuditLog


def log_audit_event(
    db: Session,
    event: str,
    details: str | None = None,
    user_id: int | None = None,
) -> AuditLog:
    log_entry = AuditLog(
        user_id=user_id,
        event=event,
        details=details,
    )
    db.add(log_entry)
    db.commit()
    db.refresh(log_entry)
    return log_entry
