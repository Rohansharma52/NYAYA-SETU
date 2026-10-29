"""Coordination Closure Protocol (CCP) endpoints."""
import logging
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_
from pydantic import BaseModel
from sqlalchemy.orm import Session, joinedload

from app.core.security import get_current_active_user, require_roles
from app.db.session import get_db
from app.models.coordination import (
    CoordinationItem, CoordinationParticipant, CoordinationTask,
    CoordinationStatus, CoordinationDecision
)
from app.models.user import User, UserRole
from app.models.bureau import Bureau
from app.services.audit import log_audit
from app.services.notification import create_notification

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/coordination", tags=["coordination"])


# ─── Schemas ──────────────────────────────────────────────────────────────────

class ParticipantOut(BaseModel):
    id: int
    bureau_id: Optional[int] = None
    user_id: Optional[int] = None
    role_in_coordination: Optional[str] = None
    acknowledged: bool = False
    acknowledged_at: Optional[datetime] = None
    class Config: from_attributes = True


class TaskOut(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    assigned_to_id: Optional[int] = None
    due_date: Optional[datetime] = None
    is_completed: bool = False
    completed_at: Optional[datetime] = None
    completion_notes: Optional[str] = None
    created_at: Optional[datetime] = None
    class Config: from_attributes = True


class CoordinationOut(BaseModel):
    id: int
    reference_number: str
    title: str
    description: Optional[str] = None
    status: str
    decision: Optional[str] = None
    decision_rationale: Optional[str] = None
    owner_id: Optional[int] = None
    acknowledge_by: Optional[datetime] = None
    action_due_date: Optional[datetime] = None
    closure_notes: Optional[str] = None
    is_exception_closure: bool = False
    institution_id: Optional[int] = None
    lead_bureau_id: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    participants: List[ParticipantOut] = []
    tasks: List[TaskOut] = []
    class Config: from_attributes = True


class CreateCoordinationRequest(BaseModel):
    title: str
    description: Optional[str] = None
    source_relationship_id: Optional[int] = None
    owner_id: Optional[int] = None
    acknowledge_by: Optional[datetime] = None
    action_due_date: Optional[datetime] = None
    bureau_ids: List[int] = []
    participant_user_ids: List[int] = []


class AddParticipantRequest(BaseModel):
    bureau_id: Optional[int] = None
    user_id: Optional[int] = None
    role_in_coordination: Optional[str] = "participant"


class DecisionRequest(BaseModel):
    decision: str  # coordinate, link_related, keep_separate, dismiss, escalate
    rationale: Optional[str] = None


class AddTaskRequest(BaseModel):
    title: str
    description: Optional[str] = None
    assigned_to_id: Optional[int] = None
    due_date: Optional[datetime] = None


class CompleteTaskRequest(BaseModel):
    completion_notes: Optional[str] = None


class CloseRequest(BaseModel):
    closure_notes: str
    is_exception: bool = False
    exception_reason: Optional[str] = None


class PaginatedCoordination(BaseModel):
    items: List[CoordinationOut]
    total: int
    skip: int
    limit: int


# ─── Helper ───────────────────────────────────────────────────────────────────

def _get_coord_or_404(coord_id: int, db: Session, current_user: Optional[User] = None) -> CoordinationItem:
    base = _visible_coordination_query(db, current_user) if current_user else db.query(CoordinationItem)
    item = (
        base.options(joinedload(CoordinationItem.participants), joinedload(CoordinationItem.tasks))
        .filter(CoordinationItem.id == coord_id)
        .first()
    )
    if not item:
        raise HTTPException(status_code=404, detail="Coordination item not found")
    return item


def _visible_coordination_query(db: Session, current_user: User):
    query = db.query(CoordinationItem)
    if current_user.role == UserRole.BUREAU_OFFICER:
        query = query.filter(or_(
            CoordinationItem.owner_id == current_user.id,
            CoordinationItem.created_by_id == current_user.id,
            CoordinationItem.participants.any(or_(
                CoordinationParticipant.user_id == current_user.id,
                CoordinationParticipant.bureau_id == current_user.bureau_id,
            )),
        ))
    return query


def _ref_number(db: Session) -> str:
    from sqlalchemy import func
    count = db.query(func.count(CoordinationItem.id)).scalar() or 0
    year = datetime.now(timezone.utc).year
    return f"CCP-{year}-{count + 1:04d}"


# ─── Endpoints ────────────────────────────────────────────────────────────────

@router.get("/", response_model=PaginatedCoordination)
async def list_coordination(
    status: Optional[str] = Query(None),
    owner_id: Optional[int] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    query = _visible_coordination_query(db, current_user).options(
        joinedload(CoordinationItem.participants), joinedload(CoordinationItem.tasks)
    )
    if status:
        try:
            query = query.filter(CoordinationItem.status == CoordinationStatus(status))
        except ValueError:
            pass
    if owner_id:
        query = query.filter(CoordinationItem.owner_id == owner_id)
    total = query.count()
    items = query.order_by(CoordinationItem.created_at.desc()).offset(skip).limit(limit).all()
    return {"items": items, "total": total, "skip": skip, "limit": limit}


@router.get("/overdue", response_model=List[CoordinationOut])
async def list_overdue(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    now = datetime.now(timezone.utc)
    items = (
        _visible_coordination_query(db, current_user)
        .options(joinedload(CoordinationItem.participants), joinedload(CoordinationItem.tasks))
        .filter(
            CoordinationItem.status.notin_([CoordinationStatus.CLOSED, CoordinationStatus.DISMISSED]),
            (CoordinationItem.acknowledge_by < now) | (CoordinationItem.action_due_date < now)
        )
        .all()
    )
    return items


@router.post("/", response_model=CoordinationOut, status_code=201)
async def create_coordination(
    payload: CreateCoordinationRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    try:
        item = CoordinationItem(
            reference_number=_ref_number(db),
            title=payload.title,
            description=payload.description,
            source_relationship_id=payload.source_relationship_id,
            owner_id=payload.owner_id or current_user.id,
            status=CoordinationStatus.DETECTED,
            acknowledge_by=payload.acknowledge_by,
            action_due_date=payload.action_due_date,
            created_by_id=current_user.id,
        )
        db.add(item)
        db.flush()

        # Add bureau participants
        for bureau_id in payload.bureau_ids:
            p = CoordinationParticipant(
                coordination_item_id=item.id, bureau_id=bureau_id, role_in_coordination="participant"
            )
            db.add(p)

        # Add user participants
        for uid in payload.participant_user_ids:
            p = CoordinationParticipant(
                coordination_item_id=item.id, user_id=uid, role_in_coordination="participant"
            )
            db.add(p)

        db.commit()
        db.refresh(item)
    except Exception as e:
        db.rollback()
        logger.error("Coordination creation failed: %s", e)
        raise HTTPException(status_code=500, detail="Failed to create coordination item")

    log_audit(db, current_user.id, "coordination_created", "coordination", item.id, item.title)
    return item


@router.get("/{coord_id}", response_model=CoordinationOut)
async def get_coordination(
    coord_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    return _get_coord_or_404(coord_id, db, current_user)


@router.put("/{coord_id}", response_model=CoordinationOut)
async def update_coordination(
    coord_id: int,
    payload: dict,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    item = _get_coord_or_404(coord_id, db, current_user)
    allowed_fields = {"title", "description", "acknowledge_by", "action_due_date"}
    for field, value in payload.items():
        if field in allowed_fields:
            setattr(item, field, value)
    try:
        db.commit()
        db.refresh(item)
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Update failed")
    return item


@router.post("/{coord_id}/participants", status_code=201)
async def add_participant(
    coord_id: int,
    payload: AddParticipantRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    item = _get_coord_or_404(coord_id, db, current_user)
    p = CoordinationParticipant(
        coordination_item_id=item.id,
        bureau_id=payload.bureau_id,
        user_id=payload.user_id,
        role_in_coordination=payload.role_in_coordination,
    )
    db.add(p)
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to add participant")
    return {"message": "Participant added"}


@router.post("/{coord_id}/acknowledge")
async def acknowledge(
    coord_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Mark current user's participation as acknowledged."""
    item = _get_coord_or_404(coord_id, db, current_user)
    participant = db.query(CoordinationParticipant).filter(
        CoordinationParticipant.coordination_item_id == coord_id,
        CoordinationParticipant.user_id == current_user.id,
    ).first()
    if not participant and current_user.bureau_id:
        # Bureau-level participation (One-Voice coordination): any officer of the bureau acknowledges
        participant = db.query(CoordinationParticipant).filter(
            CoordinationParticipant.coordination_item_id == coord_id,
            CoordinationParticipant.bureau_id == current_user.bureau_id,
        ).first()
    if not participant:
        raise HTTPException(status_code=404, detail="You are not a participant in this coordination item")
    participant.acknowledged = True
    participant.acknowledged_at = datetime.now(timezone.utc)

    # If all participants acknowledged, update status
    all_acked = all(p.acknowledged for p in item.participants if p.user_id is not None)
    if all_acked and item.status == CoordinationStatus.UNDER_REVIEW:
        item.status = CoordinationStatus.ACKNOWLEDGED

    try:
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Acknowledgement failed")
    log_audit(db, current_user.id, "coordination_acknowledged", "coordination", coord_id, "")
    return {"message": "Acknowledged successfully"}


@router.post("/{coord_id}/decision")
async def record_decision(
    coord_id: int,
    payload: DecisionRequest,
    current_user: User = Depends(
        require_roles(UserRole.COORDINATION_REVIEWER, UserRole.SYSTEM_ADMIN, UserRole.SENIOR_MANAGEMENT)
    ),
    db: Session = Depends(get_db),
):
    item = _get_coord_or_404(coord_id, db, current_user)
    try:
        decision = CoordinationDecision(payload.decision)
    except ValueError:
        raise HTTPException(status_code=422, detail=f"Invalid decision: {payload.decision}")

    item.decision = decision
    item.decision_rationale = payload.rationale
    item.decision_by_id = current_user.id
    item.decision_at = datetime.now(timezone.utc)
    item.status = CoordinationStatus.ACTIVE if decision == CoordinationDecision.COORDINATE else CoordinationStatus.DISMISSED

    try:
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Decision recording failed")
    log_audit(db, current_user.id, "coordination_decision", "coordination", coord_id,
              f"Decision: {decision.value}")
    return {"message": "Decision recorded", "decision": decision.value}


@router.post("/{coord_id}/tasks", status_code=201)
async def add_task(
    coord_id: int,
    payload: AddTaskRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    _get_coord_or_404(coord_id, db, current_user)
    task = CoordinationTask(
        coordination_item_id=coord_id,
        title=payload.title,
        description=payload.description,
        assigned_to_id=payload.assigned_to_id,
        due_date=payload.due_date,
        created_by_id=current_user.id,
    )
    db.add(task)
    try:
        db.commit()
        db.refresh(task)
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to add task")
    if payload.assigned_to_id:
        create_notification(db, payload.assigned_to_id, "Coordination Task Assigned",
                           f"You have been assigned a task in coordination item.",
                           "task_assigned", "medium", f"/coordination/{coord_id}", None, coord_id)
    return {"message": "Task added", "task_id": task.id}


@router.put("/{coord_id}/tasks/{task_id}")
async def update_task(
    coord_id: int,
    task_id: int,
    payload: CompleteTaskRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    task = db.query(CoordinationTask).filter(
        CoordinationTask.id == task_id, CoordinationTask.coordination_item_id == coord_id
    ).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    task.is_completed = True
    task.completed_at = datetime.now(timezone.utc)
    task.completed_by_id = current_user.id
    task.completion_notes = payload.completion_notes
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Task update failed")
    return {"message": "Task marked complete"}


@router.post("/{coord_id}/close")
async def close_coordination(
    coord_id: int,
    payload: CloseRequest,
    current_user: User = Depends(
        require_roles(UserRole.COORDINATION_REVIEWER, UserRole.SYSTEM_ADMIN)
    ),
    db: Session = Depends(get_db),
):
    """Close a coordination item. Validates all participants acknowledged.
    
    IMPORTANT: Closing coordination does NOT dispose underlying complaints.
    Case ownership and authority remain unchanged.
    """
    item = _get_coord_or_404(coord_id, db, current_user)

    if item.status in [CoordinationStatus.CLOSED, CoordinationStatus.DISMISSED]:
        raise HTTPException(status_code=422, detail="Coordination item is already closed/dismissed")

    # Check acknowledgements (unless exception)
    if not payload.is_exception:
        unacked = [p for p in item.participants if not p.acknowledged]
        if unacked:
            raise HTTPException(
                status_code=422,
                detail=f"{len(unacked)} participant(s) have not acknowledged. Use is_exception=true with a reason to override."
            )

    item.status = CoordinationStatus.CLOSED
    item.closure_notes = payload.closure_notes
    item.closed_by_id = current_user.id
    item.closed_at = datetime.now(timezone.utc)
    item.is_exception_closure = payload.is_exception
    if payload.is_exception:
        item.exception_reason = payload.exception_reason

    try:
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Closure failed")

    log_audit(db, current_user.id, "coordination_closed", "coordination", coord_id,
              f"Closed: {payload.closure_notes}")
    return {
        "message": "Coordination item closed",
        "note": "Underlying complaint cases remain in their original ownership and status.",
        "is_exception": payload.is_exception,
    }
