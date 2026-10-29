"""Notification service."""
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def create_notification(
    db,
    user_id: int,
    title: str,
    message: str,
    notification_type: str = "info",
    priority: str = "medium",
    link_url: Optional[str] = None,
    related_case_id: Optional[int] = None,
    related_coordination_id: Optional[int] = None,
):
    """Create a notification. Never raises — notification failures must not break workflows."""
    try:
        from app.models.notification import Notification, NotificationPriority
        try:
            prio = NotificationPriority(priority)
        except ValueError:
            prio = NotificationPriority.MEDIUM
        notif = Notification(
            user_id=user_id,
            title=title,
            message=message,
            notification_type=notification_type,
            priority=prio,
            link_url=link_url,
            related_case_id=related_case_id,
            related_coordination_id=related_coordination_id,
        )
        db.add(notif)
        db.commit()
    except Exception as exc:
        logger.error("Notification creation failed (non-fatal): %s", exc)
        try:
            db.rollback()
        except Exception:
            pass
