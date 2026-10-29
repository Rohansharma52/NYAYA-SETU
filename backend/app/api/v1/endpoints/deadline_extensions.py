"""Deadline extension request endpoints."""
import logging
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.security import get_current_active_user, require_roles
from app.db.session import get_db
from app.models.case import Case, CaseAction
from app.models.deadline_extension import DeadlineExtensionRequest, ExtensionStatus
from app.models.user import User, UserRole
from app.services.audit import log_audit

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/cases", tags=["deadline-extensions"])


# ─── Schemas ──────────────────────────────────────────────────────────────────

class ExtensionRequestIn(BaseModel):
    requested_due_date: datetime
    reason: str


class ExtensionReviewIn(BaseModel):
    approved: bool
    review_notes: Optional[str] = None


class ExtensionOut(BaseModel):
    id: int
    case_id: int
    original_due_date: Optional[datetime] = None
    requested_due_date: datetime
    reason: str
    status: str
    review_notes: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ─── Endpoints ────────────────────────────────────────────────────────────────

@router.post("/{case_id}/extension-requests", response_model=ExtensionOut, status_code=201)
async def request_extension(
    case_id: int,
    payload: ExtensionRequestIn,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Request a deadline extension. Bureau/regional officers and admins only."""
    allowed_roles = [UserRole.BUREAU_OFFICER, UserRole.REGIONAL_OFFICER, UserRole.SYSTEM_ADMIN]
    if current_user.role not in allowed_roles:
        raise HTTPException(status_code=403, detail="Not authorized to request deadline extension")

    case = db.query(Case).filter(Case.id == case_id, Case.is_active == True).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    if not payload.reason or not payload.reason.strip():
        raise HTTPException(status_code=422, detail="Reason is required for deadline extension")

    if payload.requested_due_date <= datetime.now(timezone.utc):
        raise HTTPException(status_code=422, detail="New due date must be in the future")

    ext = DeadlineExtensionRequest(
        case_id=case_id,
        requested_by_id=current_user.id,
        original_due_date=case.due_date,
        requested_due_date=payload.requested_due_date,
        reason=payload.reason.strip(),
        status=ExtensionStatus.PENDING,
    )
    db.add(ext)
    try:
        db.commit()
        db.refresh(ext)
    except Exception as e:
        db.rollback()
        logger.error("Extension request failed: %s", e)
        raise HTTPException(status_code=500, detail="Failed to create extension request")

    log_audit(db, current_user.id, "extension_requested", "case", case_id,
              f"Deadline extension requested: {payload.reason[:100]}")
    return ext


@router.get("/{case_id}/extension-requests", response_model=List[ExtensionOut])
async def list_extensions(
    case_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """List all extension requests for a case."""
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    exts = (
        db.query(DeadlineExtensionRequest)
        .filter(DeadlineExtensionRequest.case_id == case_id)
        .order_by(DeadlineExtensionRequest.created_at.desc())
        .all()
    )
    return exts


@router.post("/{case_id}/extension-requests/{ext_id}/review", response_model=ExtensionOut)
async def review_extension(
    case_id: int,
    ext_id: int,
    payload: ExtensionReviewIn,
    current_user: User = Depends(
        require_roles(UserRole.SYSTEM_ADMIN, UserRole.SENIOR_MANAGEMENT)
    ),
    db: Session = Depends(get_db),
):
    """Approve or reject an extension request. System admin and senior management only.
    
    On approval: case.due_date is updated and a CaseAction is logged.
    Original due date is preserved in the extension request record.
    """
    ext = db.query(DeadlineExtensionRequest).filter(
        DeadlineExtensionRequest.id == ext_id,
        DeadlineExtensionRequest.case_id == case_id,
    ).first()
    if not ext:
        raise HTTPException(status_code=404, detail="Extension request not found")

    if ext.status != ExtensionStatus.PENDING:
        raise HTTPException(
            status_code=422,
            detail=f"Extension request is already {ext.status.value} — cannot review again"
        )

    ext.status = ExtensionStatus.APPROVED if payload.approved else ExtensionStatus.REJECTED
    ext.reviewed_by_id = current_user.id
    ext.reviewed_at = datetime.now(timezone.utc)
    ext.review_notes = payload.review_notes

    if payload.approved:
        case = db.query(Case).filter(Case.id == case_id).first()
        if case:
            old_due = case.due_date
            case.due_date = ext.requested_due_date
            old_str = old_due.strftime('%d %b %Y') if old_due else 'none'
            new_str = ext.requested_due_date.strftime('%d %b %Y')
            action = CaseAction(
                case_id=case_id,
                action_type="deadline_extended",
                description=(
                    f"Deadline extended from {old_str} to {new_str}. "
                    f"Reason: {ext.reason}. Approved by: {current_user.full_name}"
                ),
                performed_by_id=current_user.id,
            )
            db.add(action)

    try:
        db.commit()
        db.refresh(ext)
    except Exception as e:
        db.rollback()
        logger.error("Extension review failed: %s", e)
        raise HTTPException(status_code=500, detail="Failed to process review")

    action_type = "extension_approved" if payload.approved else "extension_rejected"
    log_audit(db, current_user.id, action_type, "case", case_id,
              f"Extension {ext.status.value}: {payload.review_notes or 'no notes'}")
    return ext
