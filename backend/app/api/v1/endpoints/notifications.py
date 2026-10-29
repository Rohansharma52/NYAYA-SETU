"""Notification endpoints for NYAYA SETU."""
import logging
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.security import get_current_active_user
from app.db.session import get_db
from app.models.notification import Notification
from app.models.user import User

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/notifications", tags=["notifications"])

# ─── Schemas ──────────────────────────────────────────────────────────────────


class NotificationResponse(BaseModel):
    id: int
    title: str
    message: str
    notification_type: Optional[str] = None
    priority: str
    is_read: bool
    read_at: Optional[datetime] = None
    link_url: Optional[str] = None
    related_case_id: Optional[int] = None
    related_coordination_id: Optional[int] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class NotificationListResponse(BaseModel):
    items: List[NotificationResponse]
    total: int
    skip: int
    limit: int


# ─── Endpoints ────────────────────────────────────────────────────────────────


@router.get("/unread-count")
async def get_unread_count(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Return count of unread notifications for current user."""
    count = (
        db.query(Notification)
        .filter(Notification.user_id == current_user.id, Notification.is_read == False)
        .count()
    )
    return {"unread_count": count}


@router.get("/", response_model=NotificationListResponse)
async def list_notifications(
    unread_only: bool = False,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """List notifications for the current user."""
    try:
        q = db.query(Notification).filter(Notification.user_id == current_user.id)
        if unread_only:
            q = q.filter(Notification.is_read == False)
        q = q.order_by(Notification.created_at.desc())
        total = q.count()
        items = q.offset(skip).limit(limit).all()
        return NotificationListResponse(items=items, total=total, skip=skip, limit=limit)
    except Exception as exc:
        logger.error("list_notifications error: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to fetch notifications.")


@router.post("/{notification_id}/read")
async def mark_read(
    notification_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Mark a single notification as read."""
    notif = db.query(Notification).filter(
        Notification.id == notification_id,
        Notification.user_id == current_user.id,
    ).first()
    if not notif:
        raise HTTPException(status_code=404, detail="Notification not found.")
    try:
        notif.is_read = True
        notif.read_at = datetime.now(timezone.utc)
        db.commit()
        return {"message": "Marked as read."}
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to mark as read.")


@router.post("/read-all")
async def mark_all_read(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Mark all unread notifications as read."""
    try:
        now = datetime.now(timezone.utc)
        db.query(Notification).filter(
            Notification.user_id == current_user.id,
            Notification.is_read == False,
        ).update({"is_read": True, "read_at": now})
        db.commit()
        return {"message": "All notifications marked as read."}
    except Exception as exc:
        db.rollback()
        logger.error("mark_all_read error: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to mark all as read.")
