"""Case management endpoints for NYAYA SETU."""
import logging
from datetime import datetime, timezone
from typing import List, Optional

import hashlib
import os
import re
import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy import or_, and_, func
from sqlalchemy.orm import Session, joinedload

from app.core.security import get_current_active_user, require_roles
from app.db.session import get_db
from app.models.case import Case, CaseAction, CaseAssignment, CaseStatus, CasePriority
from app.models.user import User, UserRole
from app.models.bureau import Bureau
from app.models.institution import Institution, InstitutionIdentifier
from app.models.transfer import TransferRequest, TransferStatus
from app.services.audit import log_audit
from app.services.matching import detect_relationships
from app.services.notification import create_notification
from app.models.attachment import CaseAttachment

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/cases", tags=["cases"])

# ─── Schemas ──────────────────────────────────────────────────────────────────

VALID_TRANSITIONS = {
    CaseStatus.RECEIVED: [CaseStatus.TRIAGED, CaseStatus.ESCALATED],
    CaseStatus.TRIAGED: [CaseStatus.ASSIGNED, CaseStatus.ESCALATED],
    CaseStatus.ASSIGNED: [CaseStatus.UNDER_PROCESS, CaseStatus.TRANSFER_REQUESTED, CaseStatus.ESCALATED],
    CaseStatus.UNDER_PROCESS: [CaseStatus.AWAITING_INFORMATION, CaseStatus.DECISION_REVIEW, CaseStatus.DISPOSED, CaseStatus.TRANSFER_REQUESTED, CaseStatus.ESCALATED],
    CaseStatus.AWAITING_INFORMATION: [CaseStatus.UNDER_PROCESS, CaseStatus.ESCALATED],
    CaseStatus.DECISION_REVIEW: [CaseStatus.DISPOSED, CaseStatus.UNDER_PROCESS],
    CaseStatus.DISPOSED: [CaseStatus.REOPENED],
    CaseStatus.TRANSFER_REQUESTED: [CaseStatus.TRANSFERRED, CaseStatus.ASSIGNED],
    CaseStatus.TRANSFERRED: [CaseStatus.ASSIGNED],
    CaseStatus.ESCALATED: [CaseStatus.ASSIGNED, CaseStatus.UNDER_PROCESS],
    CaseStatus.REOPENED: [CaseStatus.TRIAGED],
    CaseStatus.CLOSED: [CaseStatus.REOPENED],
}


class OfficerBrief(BaseModel):
    id: int
    full_name: str
    email: str
    role: str
    class Config: from_attributes = True


class BureauBrief(BaseModel):
    id: int
    code: str
    name: str
    class Config: from_attributes = True


class InstitutionBrief(BaseModel):
    id: int
    canonical_name: str
    state: Optional[str] = None
    class Config: from_attributes = True


class CaseActionOut(BaseModel):
    id: int
    action_type: str
    description: str
    old_status: Optional[str] = None
    new_status: Optional[str] = None
    performed_by: Optional[OfficerBrief] = None
    created_at: Optional[datetime] = None
    class Config: from_attributes = True


class CaseOut(BaseModel):
    id: int
    case_number: str
    source_case_id: Optional[str] = None
    title: str
    summary: Optional[str] = None
    category: str
    sub_category: Optional[str] = None
    status: str
    priority: str
    institution_id: int
    institution: Optional[InstitutionBrief] = None
    bureau_id: Optional[int] = None
    bureau: Optional[BureauBrief] = None
    assigned_officer_id: Optional[int] = None
    assigned_officer: Optional[OfficerBrief] = None
    complainant_name: Optional[str] = None
    received_date: Optional[datetime] = None
    due_date: Optional[datetime] = None
    disposed_date: Optional[datetime] = None
    next_action: Optional[str] = None
    last_action_date: Optional[datetime] = None
    last_action: Optional[str] = None
    overlap_bureaus: List[str] = []
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    class Config: from_attributes = True


class CaseDetailOut(CaseOut):
    actions: List[CaseActionOut] = []
    complainant_email: Optional[str] = None
    complainant_phone: Optional[str] = None
    can_act: bool = True  # False = another Bureau/Cell's file, shown read-only


class CreateCaseRequest(BaseModel):
    title: str
    summary: Optional[str] = None
    category: str
    sub_category: Optional[str] = None
    priority: str = "medium"
    institution_id: int
    bureau_id: Optional[int] = None
    source_case_id: Optional[str] = None
    complainant_name: Optional[str] = None
    complainant_email: Optional[str] = None
    complainant_phone: Optional[str] = None
    received_date: Optional[datetime] = None
    due_date: Optional[datetime] = None
    next_action: Optional[str] = None


class UpdateCaseRequest(BaseModel):
    title: Optional[str] = None
    summary: Optional[str] = None
    category: Optional[str] = None
    sub_category: Optional[str] = None
    priority: Optional[str] = None
    bureau_id: Optional[int] = None
    due_date: Optional[datetime] = None
    next_action: Optional[str] = None
    complainant_name: Optional[str] = None
    complainant_email: Optional[str] = None
    complainant_phone: Optional[str] = None


class StatusChangeRequest(BaseModel):
    new_status: str
    reason: str


class AssignRequest(BaseModel):
    officer_id: int
    notes: Optional[str] = None


class NoteRequest(BaseModel):
    description: str
    action_type: str = "note"


class TransferCreateRequest(BaseModel):
    to_bureau_id: Optional[int] = None
    to_officer_id: Optional[int] = None
    reason: str


class PaginatedCases(BaseModel):
    items: List[CaseOut]
    total: int
    skip: int
    limit: int


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _generate_case_number(db: Session) -> str:
    year = datetime.now(timezone.utc).year
    count = db.query(func.count(Case.id)).scalar() or 0
    return f"AICTE-NS-{year}-{count + 1:05d}"


def _can_act(case: Case, user: Optional[User]) -> bool:
    """Only the handling Bureau/Cell (or oversight roles) may change a case."""
    return not (user and user.role == UserRole.BUREAU_OFFICER and case.bureau_id != user.bureau_id)


def _get_case_or_404(case_id: int, db: Session, current_user: Optional[User] = None, read_only: bool = False) -> Case:
    """Fetch a case. Other bureaus' files are readable (to avoid duplicate action across
    Bureaus/Cells, PS 26264) but every change is limited to the handling bureau."""
    case = db.query(Case).filter(Case.id == case_id, Case.is_active == True).first()  # noqa: E712
    if not case:
        raise HTTPException(status_code=404, detail=f"Case {case_id} not found")
    if not read_only and not _can_act(case, current_user):
        code = case.bureau.code if case.bureau else "another Bureau/Cell"
        raise HTTPException(status_code=403,
                            detail=f"This case is handled by {code}. Only that bureau can act on it — use coordination instead.")
    return case


OPEN_STATUSES = [
    CaseStatus.RECEIVED, CaseStatus.TRIAGED, CaseStatus.ASSIGNED, CaseStatus.UNDER_PROCESS,
    CaseStatus.AWAITING_INFORMATION, CaseStatus.DECISION_REVIEW, CaseStatus.ESCALATED,
    CaseStatus.TRANSFER_REQUESTED, CaseStatus.REOPENED,
]


def _enrich_cases(items: List[Case], db: Session) -> None:
    """Attach last action + cross-bureau overlap flags (PS §2 and §3) with two grouped queries."""
    if not items:
        return
    ids = [c.id for c in items]
    latest = (
        db.query(CaseAction.case_id, func.max(CaseAction.id))
        .filter(CaseAction.case_id.in_(ids))
        .group_by(CaseAction.case_id)
        .all()
    )
    action_ids = [aid for _, aid in latest]
    actions = {a.id: a for a in db.query(CaseAction).filter(CaseAction.id.in_(action_ids or [-1])).all()}
    last_by_case = {cid: actions.get(aid) for cid, aid in latest}
    inst_ids = {c.institution_id for c in items}
    open_rows = (
        db.query(Case.institution_id, Bureau.code)
        .join(Bureau, Case.bureau_id == Bureau.id)
        .filter(Case.institution_id.in_(inst_ids), Case.is_active == True, Case.status.in_(OPEN_STATUSES))
        .distinct()
        .all()
    )
    bureaus_by_inst: dict = {}
    for inst_id, code in open_rows:
        bureaus_by_inst.setdefault(inst_id, set()).add(code)
    for c in items:
        last = last_by_case.get(c.id)
        if last is not None:
            c.last_action = last.description
            if not c.last_action_date:
                c.last_action_date = last.created_at
        own = c.bureau.code if c.bureau else None
        c.overlap_bureaus = sorted(b for b in bureaus_by_inst.get(c.institution_id, set()) if b != own)


def _notify_escalation(db: Session, case: Case, reason: str, actor: User) -> None:
    targets = db.query(User).filter(
        User.is_active == True,
        User.role.in_([UserRole.SENIOR_MANAGEMENT, UserRole.SYSTEM_ADMIN]),
    ).all()
    for u in targets:
        if u.id == actor.id:
            continue
        create_notification(
            db, u.id, "Escalation alert",
            f"{case.case_number} was escalated by {actor.full_name}: {reason}",
            "escalation", "high", f"/cases/{case.id}", case.id, None,
        )


# ─── Endpoints ────────────────────────────────────────────────────────────────

@router.get("/", response_model=PaginatedCases)
async def list_cases(
    q: Optional[str] = Query(None, description="Search case and institution text"),
    status: Optional[str] = Query(None),
    bureau_id: Optional[int] = Query(None),
    institution_id: Optional[int] = Query(None),
    priority: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    region: Optional[str] = Query(None),
    aicte_id: Optional[str] = Query(None, description="Institution AICTE permanent ID"),
    overdue: Optional[bool] = Query(None),
    # Advanced filters
    date_from: Optional[str] = Query(None, description="ISO date, filter received_date >="),
    date_to: Optional[str] = Query(None, description="ISO date, filter received_date <="),
    statuses: Optional[str] = Query(None, description="Comma-separated statuses e.g. received,triaged"),
    ageing_bracket: Optional[str] = Query(None, description="0_7 | 8_30 | 31_90 | over_90"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    query = db.query(Case).filter(Case.is_active == True)

    if q:
        query = query.filter(or_(
            Case.title.ilike(f"%{q}%"),
            Case.case_number.ilike(f"%{q}%"),
            Case.summary.ilike(f"%{q}%"),
            Case.institution_id.in_(
                db.query(Institution.id).filter(
                    or_(
                        Institution.canonical_name.ilike(f"%{q}%"),
                        Institution.short_name.ilike(f"%{q}%"),
                    )
                )
            ),
        ))
    if aicte_id:
        query = query.filter(
            Case.institution_id.in_(
                db.query(InstitutionIdentifier.institution_id).filter(
                    InstitutionIdentifier.id_type.ilike("%aicte%"),
                    InstitutionIdentifier.id_value.ilike(f"%{aicte_id}%"),
                )
            )
        )
    if status:
        try:
            query = query.filter(Case.status == CaseStatus(status))
        except ValueError:
            pass
    if bureau_id:
        query = query.filter(Case.bureau_id == bureau_id)
    if institution_id:
        query = query.filter(Case.institution_id == institution_id)
    if priority:
        try:
            query = query.filter(Case.priority == CasePriority(priority))
        except ValueError:
            pass
    if category:
        query = query.filter(Case.category.ilike(f"%{category}%"))
    if region:
        query = query.filter(
            Case.institution_id.in_(
                db.query(Institution.id).filter(Institution.region.ilike(f"%{region}%"))
            )
        )
    if overdue is True:
        query = query.filter(
            Case.due_date < datetime.now(timezone.utc),
            Case.status.notin_([CaseStatus.DISPOSED, CaseStatus.CLOSED, CaseStatus.TRANSFERRED])
        )

    # ── Advanced filters ───────────────────────────────────────────────────────
    from datetime import timedelta
    if date_from:
        try:
            df = datetime.fromisoformat(date_from.replace('Z', '+00:00'))
            query = query.filter(Case.received_date >= df)
        except ValueError:
            pass

    if date_to:
        try:
            dt = datetime.fromisoformat(date_to.replace('Z', '+00:00'))
            query = query.filter(Case.received_date <= dt)
        except ValueError:
            pass

    if statuses:
        status_list = [s.strip() for s in statuses.split(',') if s.strip()]
        valid_statuses = []
        for s in status_list:
            try:
                valid_statuses.append(CaseStatus(s))
            except ValueError:
                pass
        if valid_statuses:
            query = query.filter(Case.status.in_(valid_statuses))

    if ageing_bracket:
        now_ab = datetime.now(timezone.utc)
        if ageing_bracket == "0_7":
            query = query.filter(Case.received_date >= now_ab - timedelta(days=7))
        elif ageing_bracket == "8_30":
            query = query.filter(
                Case.received_date >= now_ab - timedelta(days=30),
                Case.received_date < now_ab - timedelta(days=7)
            )
        elif ageing_bracket == "31_90":
            query = query.filter(
                Case.received_date >= now_ab - timedelta(days=90),
                Case.received_date < now_ab - timedelta(days=30)
            )
        elif ageing_bracket == "over_90":
            query = query.filter(Case.received_date < now_ab - timedelta(days=90))

    # Scope: bureau officers only see their bureau
    if current_user.role == UserRole.BUREAU_OFFICER:
        query = query.filter(Case.bureau_id == current_user.bureau_id)

    total = query.count()
    items = (
        query.options(
            joinedload(Case.institution),
            joinedload(Case.bureau),
            joinedload(Case.assigned_officer),
        )
        .order_by(Case.received_date.desc().nullslast(), Case.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    _enrich_cases(items, db)
    return {"items": items, "total": total, "skip": skip, "limit": limit}


@router.post("/", response_model=CaseOut, status_code=201)
async def create_case(
    payload: CreateCaseRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    # Validate institution
    inst = db.query(Institution).filter(Institution.id == payload.institution_id).first()
    if not inst:
        raise HTTPException(status_code=404, detail="Institution not found")

    try:
        case = Case(
            case_number=_generate_case_number(db),
            title=payload.title,
            summary=payload.summary,
            category=payload.category,
            sub_category=payload.sub_category,
            priority=CasePriority(payload.priority),
            institution_id=payload.institution_id,
            bureau_id=payload.bureau_id or current_user.bureau_id,
            source_case_id=payload.source_case_id,
            complainant_name=payload.complainant_name,
            complainant_email=payload.complainant_email,
            complainant_phone=payload.complainant_phone,
            received_date=payload.received_date or datetime.now(timezone.utc),
            due_date=payload.due_date,
            next_action=payload.next_action,
            status=CaseStatus.RECEIVED,
            created_by_id=current_user.id,
        )
        if (
            current_user.role == UserRole.BUREAU_OFFICER
            and case.bureau_id != current_user.bureau_id
        ):
            raise HTTPException(status_code=403, detail="You may only create cases in your bureau")
        db.add(case)
        db.flush()

        # Initial action
        action = CaseAction(
            case_id=case.id,
            action_type="created",
            description=f"Case created by {current_user.full_name}",
            new_status=CaseStatus.RECEIVED,
            performed_by_id=current_user.id,
        )
        db.add(action)
        db.commit()
        db.refresh(case)

        # Trigger relationship matching (non-blocking)
        try:
            detect_relationships(case, db)
        except Exception as e:
            logger.warning("Relationship detection failed (non-fatal): %s", e)
        try:
            from app.services.intelligence import notify_case_overlap
            notify_case_overlap(db, case)
        except Exception as e:
            logger.warning("Overlap notification failed (non-fatal): %s", e)

        log_audit(db, current_user.id, "case_created", "case", case.id,
                  f"Case {case.case_number} created")
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error("Case creation failed: %s", e)
        raise HTTPException(status_code=500, detail="Failed to create case")

    return case


@router.get("/{case_id}", response_model=CaseDetailOut)
async def get_case(
    case_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    case = (
        db.query(Case)
        .options(
            joinedload(Case.institution),
            joinedload(Case.bureau),
            joinedload(Case.assigned_officer),
            joinedload(Case.actions).joinedload(CaseAction.performed_by),
        )
        .filter(Case.id == case_id, Case.is_active == True)
        .first()
    )
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    _enrich_cases([case], db)
    out = CaseDetailOut.model_validate(case)
    out.can_act = _can_act(case, current_user)
    if not out.can_act:
        # Cross-bureau read-only view: hide the complainant's contact details
        out.complainant_email = None
        out.complainant_phone = None
    return out


@router.put("/{case_id}", response_model=CaseOut)
async def update_case(
    case_id: int,
    payload: UpdateCaseRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    case = _get_case_or_404(case_id, db, current_user)
    changes = []
    for field, value in payload.model_dump(exclude_none=True).items():
        old = getattr(case, field, None)
        if old != value:
            setattr(case, field, value)
            changes.append(f"{field}: {old} → {value}")
    if changes:
        action = CaseAction(
            case_id=case.id,
            action_type="updated",
            description="Updated: " + "; ".join(changes),
            performed_by_id=current_user.id,
        )
        db.add(action)
        try:
            db.commit()
            db.refresh(case)
        except Exception as e:
            db.rollback()
            raise HTTPException(status_code=500, detail="Update failed")
    return case


@router.post("/{case_id}/status")
async def change_status(
    case_id: int,
    payload: StatusChangeRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    case = _get_case_or_404(case_id, db, current_user)
    try:
        new_status = CaseStatus(payload.new_status)
    except ValueError:
        raise HTTPException(status_code=422, detail=f"Invalid status: {payload.new_status}")

    allowed = VALID_TRANSITIONS.get(case.status, [])
    if new_status not in allowed:
        raise HTTPException(
            status_code=422,
            detail=f"Transition {case.status.value} → {new_status.value} is not permitted. Allowed: {[s.value for s in allowed]}"
        )
    if not payload.reason or not payload.reason.strip():
        raise HTTPException(status_code=422, detail="Reason is required for status change")

    old_status = case.status
    case.status = new_status
    case.last_action_date = datetime.now(timezone.utc)
    if new_status in (CaseStatus.DISPOSED, CaseStatus.CLOSED):
        case.disposed_date = datetime.now(timezone.utc)
    elif new_status == CaseStatus.REOPENED:
        case.disposed_date = None
    action = CaseAction(
        case_id=case.id,
        action_type="status_change",
        description=payload.reason,
        old_status=old_status,
        new_status=new_status,
        performed_by_id=current_user.id,
    )
    db.add(action)
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Status change failed")
    log_audit(db, current_user.id, "status_changed", "case", case_id,
              f"{old_status.value} → {new_status.value}: {payload.reason}")
    if new_status == CaseStatus.ESCALATED:
        _notify_escalation(db, case, payload.reason, current_user)
    return {"message": "Status updated", "old_status": old_status.value, "new_status": new_status.value}


@router.post("/{case_id}/assign")
async def assign_case(
    case_id: int,
    payload: AssignRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    case = _get_case_or_404(case_id, db, current_user)
    officer = db.query(User).filter(User.id == payload.officer_id, User.is_active == True).first()
    if not officer:
        raise HTTPException(status_code=404, detail="Officer not found")
    if (
        current_user.role == UserRole.BUREAU_OFFICER
        and officer.bureau_id != case.bureau_id
    ):
        raise HTTPException(status_code=403, detail="You may only assign officers in your bureau")

    # Close previous assignment
    db.query(CaseAssignment).filter(
        CaseAssignment.case_id == case_id, CaseAssignment.is_current == True
    ).update({"is_current": False, "ended_at": datetime.now(timezone.utc)})

    case.assigned_officer_id = officer.id
    assignment = CaseAssignment(
        case_id=case.id,
        assigned_to_id=officer.id,
        assigned_by_id=current_user.id,
        bureau_id=case.bureau_id,
        notes=payload.notes,
    )
    db.add(assignment)
    action = CaseAction(
        case_id=case.id,
        action_type="assigned",
        description=f"Assigned to {officer.full_name}" + (f" — {payload.notes}" if payload.notes else ""),
        performed_by_id=current_user.id,
    )
    db.add(action)
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Assignment failed")

    create_notification(db, officer.id, "Case Assigned",
                        f"Case {case.case_number} has been assigned to you.",
                        "case_assigned", "medium", f"/cases/{case_id}", case_id, None)
    return {"message": "Case assigned successfully"}


@router.get("/{case_id}/timeline", response_model=List[CaseActionOut])
async def get_timeline(
    case_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    _get_case_or_404(case_id, db, current_user, read_only=True)
    actions = (
        db.query(CaseAction)
        .options(joinedload(CaseAction.performed_by))
        .filter(CaseAction.case_id == case_id)
        .order_by(CaseAction.created_at)
        .all()
    )
    return actions


@router.post("/{case_id}/actions")
async def add_action(
    case_id: int,
    payload: NoteRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    case = _get_case_or_404(case_id, db, current_user)
    action = CaseAction(
        case_id=case.id,
        action_type=payload.action_type,
        description=payload.description,
        performed_by_id=current_user.id,
    )
    db.add(action)
    case.last_action_date = datetime.now(timezone.utc)
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to add action")
    return {"message": "Action recorded"}


@router.post("/{case_id}/transfer", status_code=201)
async def request_transfer(
    case_id: int,
    payload: TransferCreateRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    case = _get_case_or_404(case_id, db, current_user)
    tr = TransferRequest(
        case_id=case_id,
        from_bureau_id=case.bureau_id,
        to_bureau_id=payload.to_bureau_id,
        from_officer_id=case.assigned_officer_id,
        to_officer_id=payload.to_officer_id,
        reason=payload.reason,
        requested_by_id=current_user.id,
    )
    db.add(tr)
    action = CaseAction(
        case_id=case.id,
        action_type="transfer_requested",
        description=f"Transfer requested: {payload.reason}",
        performed_by_id=current_user.id,
    )
    db.add(action)
    old_status = case.status
    action.old_status = old_status
    action.new_status = CaseStatus.TRANSFER_REQUESTED
    case.status = CaseStatus.TRANSFER_REQUESTED
    case.last_action_date = datetime.now(timezone.utc)
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Transfer request failed")
    if payload.to_bureau_id:
        for u in db.query(User).filter(User.bureau_id == payload.to_bureau_id, User.is_active == True).all():
            create_notification(db, u.id, "Incoming transfer request",
                                f"{case.case_number} — {case.title}: {payload.reason}",
                                "transfer", "high", "/transfers", case.id, None)
    log_audit(db, current_user.id, "transfer_requested", "case", case_id, payload.reason)
    return {"message": "Transfer request submitted", "transfer_id": tr.id}


# ─── Transfer history ─────────────────────────────────────────────────────────

@router.get("/{case_id}/transfers")
async def case_transfers(
    case_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    _get_case_or_404(case_id, db, current_user, read_only=True)
    rows = (
        db.query(TransferRequest)
        .options(joinedload(TransferRequest.from_bureau), joinedload(TransferRequest.to_bureau),
                 joinedload(TransferRequest.requested_by), joinedload(TransferRequest.responded_by))
        .filter(TransferRequest.case_id == case_id)
        .order_by(TransferRequest.requested_at.desc())
        .all()
    )
    return [_transfer_out(t) for t in rows]


def _transfer_out(t: TransferRequest) -> dict:
    return {
        "id": t.id,
        "case_id": t.case_id,
        "case_number": t.case.case_number if t.case else None,
        "case_title": t.case.title if t.case else None,
        "from_bureau": t.from_bureau.code if t.from_bureau else None,
        "to_bureau": t.to_bureau.code if t.to_bureau else None,
        "to_bureau_id": t.to_bureau_id,
        "reason": t.reason,
        "status": t.status.value if t.status else None,
        "response_notes": t.response_notes,
        "requested_by": t.requested_by.full_name if t.requested_by else None,
        "responded_by": t.responded_by.full_name if t.responded_by else None,
        "requested_at": t.requested_at.isoformat() if t.requested_at else None,
        "responded_at": t.responded_at.isoformat() if t.responded_at else None,
    }


# ─── Supporting documents (PS §5) ─────────────────────────────────────────────

UPLOAD_DIR = os.environ.get("UPLOAD_DIR", os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "uploads"))
MAX_UPLOAD_BYTES = 10 * 1024 * 1024
ALLOWED_EXT = {".pdf", ".png", ".jpg", ".jpeg", ".doc", ".docx", ".xls", ".xlsx", ".txt", ".csv"}


def _attachment_out(a: CaseAttachment) -> dict:
    return {
        "id": a.id, "case_id": a.case_id, "action_id": a.action_id, "filename": a.filename,
        "content_type": a.content_type, "size_bytes": a.size_bytes, "sha256": a.sha256,
        "remarks": a.remarks,
        "uploaded_by": a.uploaded_by.full_name if a.uploaded_by else None,
        "created_at": a.created_at.isoformat() if a.created_at else None,
    }


@router.post("/{case_id}/attachments", status_code=201)
async def upload_attachment(
    case_id: int,
    file: UploadFile = File(...),
    remarks: Optional[str] = Form(None),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    case = _get_case_or_404(case_id, db, current_user)
    original = os.path.basename(file.filename or "document")
    ext = os.path.splitext(original)[1].lower()
    if ext not in ALLOWED_EXT:
        raise HTTPException(status_code=415, detail=f"File type {ext or '(none)'} is not allowed")
    data = await file.read()
    if not data:
        raise HTTPException(status_code=422, detail="Empty file")
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="File exceeds 10 MB limit")
    digest = hashlib.sha256(data).hexdigest()
    safe = re.sub(r"[^A-Za-z0-9._-]", "_", original)[:120]
    folder = os.path.abspath(os.path.join(UPLOAD_DIR, str(case_id)))
    os.makedirs(folder, exist_ok=True)
    stored = os.path.join(folder, f"{uuid.uuid4().hex}_{safe}")
    with open(stored, "wb") as fh:
        fh.write(data)

    action = CaseAction(
        case_id=case.id,
        action_type="document_attached",
        description=f"Supporting document attached: {original}" + (f" — {remarks}" if remarks else ""),
        performed_by_id=current_user.id,
    )
    db.add(action)
    db.flush()
    att = CaseAttachment(
        case_id=case.id, action_id=action.id, filename=original, content_type=file.content_type,
        size_bytes=len(data), sha256=digest, storage_path=stored, remarks=remarks,
        uploaded_by_id=current_user.id,
    )
    db.add(att)
    case.last_action_date = datetime.now(timezone.utc)
    try:
        db.commit()
        db.refresh(att)
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to store attachment")
    log_audit(db, current_user.id, "attachment_uploaded", "case", case_id, f"{original} ({digest[:12]}…)")
    return _attachment_out(att)


@router.get("/{case_id}/attachments")
async def list_attachments(
    case_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    _get_case_or_404(case_id, db, current_user, read_only=True)
    rows = (
        db.query(CaseAttachment).options(joinedload(CaseAttachment.uploaded_by))
        .filter(CaseAttachment.case_id == case_id)
        .order_by(CaseAttachment.created_at.desc())
        .all()
    )
    return [_attachment_out(a) for a in rows]


@router.get("/{case_id}/attachments/{attachment_id}/download")
async def download_attachment(
    case_id: int,
    attachment_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    _get_case_or_404(case_id, db, current_user)
    att = db.query(CaseAttachment).filter(
        CaseAttachment.id == attachment_id, CaseAttachment.case_id == case_id).first()
    if not att or not os.path.exists(att.storage_path):
        raise HTTPException(status_code=404, detail="Attachment not found")
    log_audit(db, current_user.id, "attachment_downloaded", "case", case_id, att.filename)
    return FileResponse(att.storage_path, filename=att.filename,
                        media_type=att.content_type or "application/octet-stream")
