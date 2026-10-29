"""Bureau management endpoints for NYAYA SETU."""
import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.security import get_current_active_user, require_roles
from app.db.session import get_db
from app.models.bureau import Bureau
from app.models.case import Case
from app.models.user import User, UserRole
from app.services.audit import log_audit

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/bureaus", tags=["bureaus"])

# ─── Schemas ──────────────────────────────────────────────────────────────────


class BureauResponse(BaseModel):
    id: int
    code: str
    name: str
    description: Optional[str] = None
    head_name: Optional[str] = None
    head_email: Optional[str] = None
    is_active: bool

    class Config:
        from_attributes = True


class BureauDetailResponse(BureauResponse):
    total_cases: int = 0
    open_cases: int = 0


class BureauListResponse(BaseModel):
    items: List[BureauResponse]
    total: int
    skip: int
    limit: int


class CreateBureauRequest(BaseModel):
    code: str
    name: str
    description: Optional[str] = None
    head_name: Optional[str] = None
    head_email: Optional[str] = None


class UpdateBureauRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    head_name: Optional[str] = None
    head_email: Optional[str] = None
    is_active: Optional[bool] = None


# ─── Endpoints ────────────────────────────────────────────────────────────────


@router.get("/", response_model=BureauListResponse)
async def list_bureaus(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    _: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """List all bureaus."""
    try:
        q = db.query(Bureau)
        total = q.count()
        bureaus = q.offset(skip).limit(limit).all()
        return BureauListResponse(items=bureaus, total=total, skip=skip, limit=limit)
    except Exception as exc:
        logger.error("list_bureaus error: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to fetch bureaus.")


@router.post("/", response_model=BureauResponse, status_code=status.HTTP_201_CREATED)
async def create_bureau(
    payload: CreateBureauRequest,
    admin: User = Depends(require_roles(UserRole.SYSTEM_ADMIN.value)),
    db: Session = Depends(get_db),
):
    """Create a new bureau. Admin only."""
    existing = db.query(Bureau).filter(Bureau.code == payload.code).first()
    if existing:
        raise HTTPException(status_code=400, detail="Bureau code already exists.")
    try:
        bureau = Bureau(
            code=payload.code,
            name=payload.name,
            description=payload.description,
            head_name=payload.head_name,
            head_email=payload.head_email,
        )
        db.add(bureau)
        db.commit()
        db.refresh(bureau)
        log_audit(db, admin.id, "create_bureau", "bureau", bureau.id, f"Created bureau {bureau.code}")
        return bureau
    except Exception as exc:
        db.rollback()
        logger.error("create_bureau error: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to create bureau.")


@router.get("/{bureau_id}", response_model=BureauDetailResponse)
async def get_bureau(
    bureau_id: int,
    _: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Get bureau details with case statistics."""
    bureau = db.query(Bureau).filter(Bureau.id == bureau_id).first()
    if not bureau:
        raise HTTPException(status_code=404, detail="Bureau not found.")

    total_cases = db.query(Case).filter(Case.bureau_id == bureau_id).count()
    open_statuses = ["received", "triaged", "assigned", "under_process",
                     "awaiting_information", "decision_review", "escalated", "reopened"]
    open_cases = (
        db.query(Case)
        .filter(Case.bureau_id == bureau_id, Case.status.in_(open_statuses))
        .count()
    )

    return BureauDetailResponse(
        id=bureau.id,
        code=bureau.code,
        name=bureau.name,
        description=bureau.description,
        head_name=bureau.head_name,
        head_email=bureau.head_email,
        is_active=bureau.is_active,
        total_cases=total_cases,
        open_cases=open_cases,
    )


@router.put("/{bureau_id}", response_model=BureauResponse)
async def update_bureau(
    bureau_id: int,
    payload: UpdateBureauRequest,
    admin: User = Depends(require_roles(UserRole.SYSTEM_ADMIN.value)),
    db: Session = Depends(get_db),
):
    """Update bureau details. Admin only."""
    bureau = db.query(Bureau).filter(Bureau.id == bureau_id).first()
    if not bureau:
        raise HTTPException(status_code=404, detail="Bureau not found.")
    try:
        if payload.name is not None:
            bureau.name = payload.name
        if payload.description is not None:
            bureau.description = payload.description
        if payload.head_name is not None:
            bureau.head_name = payload.head_name
        if payload.head_email is not None:
            bureau.head_email = payload.head_email
        if payload.is_active is not None:
            bureau.is_active = payload.is_active
        db.commit()
        db.refresh(bureau)
        log_audit(db, admin.id, "update_bureau", "bureau", bureau.id, "Bureau updated")
        return bureau
    except Exception as exc:
        db.rollback()
        logger.error("update_bureau error: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to update bureau.")
