"""Transfer workflow: inbox of pending transfer requests and accept / reject (PS §2, §5)."""
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session, joinedload

from app.api.v1.endpoints.cases import _transfer_out
from app.core.security import get_current_active_user
from app.db.session import get_db
from app.models.case import Case, CaseAction, CaseStatus
from app.models.transfer import TransferRequest, TransferStatus
from app.models.user import User, UserRole
from app.services.audit import log_audit
from app.services.notification import create_notification

router = APIRouter(prefix="/transfers", tags=["transfers"])


class TransferDecision(BaseModel):
    accept: bool
    notes: Optional[str] = None
    to_officer_id: Optional[int] = None


@router.get("/")
async def list_transfers(
    status: Optional[str] = Query("requested"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    q = db.query(TransferRequest).options(
        joinedload(TransferRequest.case), joinedload(TransferRequest.from_bureau),
        joinedload(TransferRequest.to_bureau), joinedload(TransferRequest.requested_by),
        joinedload(TransferRequest.responded_by),
    )
    if status:
        try:
            q = q.filter(TransferRequest.status == TransferStatus(status))
        except ValueError:
            pass
    if current_user.role == UserRole.BUREAU_OFFICER:
        q = q.filter((TransferRequest.to_bureau_id == current_user.bureau_id) |
                     (TransferRequest.from_bureau_id == current_user.bureau_id))
    rows = q.order_by(TransferRequest.requested_at.desc()).all()
    return {"items": [_transfer_out(t) for t in rows], "total": len(rows)}


@router.post("/{transfer_id}/respond")
async def respond_transfer(
    transfer_id: int,
    payload: TransferDecision,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    tr = db.query(TransferRequest).options(joinedload(TransferRequest.to_bureau)).filter(
        TransferRequest.id == transfer_id).first()
    if not tr:
        raise HTTPException(status_code=404, detail="Transfer request not found")
    if tr.status != TransferStatus.REQUESTED:
        raise HTTPException(status_code=409, detail=f"Transfer already {tr.status.value}")
    allowed = current_user.role in (UserRole.SYSTEM_ADMIN, UserRole.SENIOR_MANAGEMENT) or (
        current_user.role == UserRole.BUREAU_OFFICER and current_user.bureau_id == tr.to_bureau_id)
    if not allowed:
        raise HTTPException(status_code=403, detail="Only the receiving bureau or management can respond")
    if not payload.accept and not (payload.notes or "").strip():
        raise HTTPException(status_code=422, detail="A reason is required to reject a transfer")
    case = db.query(Case).filter(Case.id == tr.case_id).first()
    now = datetime.now(timezone.utc)
    tr.status = TransferStatus.ACCEPTED if payload.accept else TransferStatus.REJECTED
    tr.responded_by_id = current_user.id
    tr.responded_at = now
    tr.response_notes = payload.notes
    old_status = case.status
    if payload.accept:
        case.bureau_id = tr.to_bureau_id
        case.assigned_officer_id = payload.to_officer_id or tr.to_officer_id
        case.status = CaseStatus.TRANSFERRED
        desc = f"Transfer accepted by {tr.to_bureau.code if tr.to_bureau else 'receiving bureau'}"
    else:
        case.status = CaseStatus.ASSIGNED if case.assigned_officer_id else CaseStatus.TRIAGED
        desc = "Transfer rejected"
    if payload.notes:
        desc += f" — {payload.notes}"
    case.last_action_date = now
    db.add(CaseAction(case_id=case.id, action_type="transfer_accepted" if payload.accept else "transfer_rejected",
                      description=desc, old_status=old_status, new_status=case.status,
                      performed_by_id=current_user.id))
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to record transfer decision")
    if tr.requested_by_id:
        create_notification(db, tr.requested_by_id, "Transfer " + ("accepted" if payload.accept else "rejected"),
                            f"{case.case_number}: {desc}", "transfer", "medium", f"/cases/{case.id}", case.id, None)
    log_audit(db, current_user.id, "transfer_" + ("accepted" if payload.accept else "rejected"),
              "transfer_request", tr.id, desc)
    return {"message": desc, "case_status": case.status.value, "bureau_id": case.bureau_id}
