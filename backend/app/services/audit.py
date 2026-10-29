"""Audit logging service."""
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def log_audit(
    db,
    user_id: Optional[int],
    action: str,
    resource_type: str,
    resource_id: Optional[int],
    description: str,
    old_data=None,
    new_data=None,
):
    """Create an audit event. Never raises — logging failures must not break workflows."""
    try:
        from app.models.audit import AuditEvent
        event = AuditEvent(
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            description=description,
            old_data=old_data,
            new_data=new_data,
        )
        db.add(event)
        db.commit()
    except Exception as exc:
        logger.error("Audit log failed (non-fatal): %s", exc)
        try:
            db.rollback()
        except Exception:
            pass
