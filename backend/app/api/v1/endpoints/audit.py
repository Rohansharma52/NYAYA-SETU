"""Audit log endpoints."""
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.core.security import require_roles
from app.db.session import get_db
from app.models.audit import AuditEvent
from app.models.user import UserRole

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("/")
async def list_audit_events(
    resource_type: Optional[str] = Query(None),
    action: Optional[str] = Query(None),
    user_id: Optional[int] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    current_user=Depends(require_roles(UserRole.SYSTEM_ADMIN, UserRole.SENIOR_MANAGEMENT)),
    db: Session = Depends(get_db),
):
    query = db.query(AuditEvent)
    if resource_type:
        query = query.filter(AuditEvent.resource_type == resource_type)
    if action:
        query = query.filter(AuditEvent.action.ilike(f"%{action}%"))
    if user_id:
        query = query.filter(AuditEvent.user_id == user_id)
    total = query.count()
    events = query.order_by(AuditEvent.created_at.desc()).offset(skip).limit(limit).all()
    from app.models.user import User
    names = {u.id: u.full_name for u in db.query(User).filter(User.id.in_({e.user_id for e in events if e.user_id} or {-1})).all()}
    return {
        "items": [
            {"id": e.id, "user_id": e.user_id, "user_name": names.get(e.user_id), "action": e.action,
             "resource_type": e.resource_type, "resource_id": e.resource_id,
             "description": e.description, "created_at": e.created_at}
            for e in events
        ],
        "total": total, "skip": skip, "limit": limit
    }
