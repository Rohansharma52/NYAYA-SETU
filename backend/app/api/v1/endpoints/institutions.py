"""Institution management endpoints for NYAYA SETU."""
import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.security import get_current_active_user, require_roles
from app.db.session import get_db
from app.models.institution import Institution, InstitutionIdentifier, InstitutionStatus
from app.models.case import Case
from app.models.user import User, UserRole
from app.services.audit import log_audit

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/institutions", tags=["institutions"])

# ─── Schemas ──────────────────────────────────────────────────────────────────


class IdentifierResponse(BaseModel):
    id: int
    id_type: str
    id_value: str
    source_system: Optional[str] = None
    is_primary: bool
    is_verified: bool

    class Config:
        from_attributes = True


class InstitutionResponse(BaseModel):
    id: int
    canonical_name: str
    short_name: Optional[str] = None
    institution_type: Optional[str] = None
    status: str
    state: Optional[str] = None
    district: Optional[str] = None
    city: Optional[str] = None
    region: Optional[str] = None
    address: Optional[str] = None
    pincode: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    website: Optional[str] = None
    data_source: Optional[str] = None

    class Config:
        from_attributes = True


class InstitutionDetailResponse(InstitutionResponse):
    identifiers: List[IdentifierResponse] = []
    total_cases: int = 0
    open_cases: int = 0


class InstitutionListResponse(BaseModel):
    items: List[InstitutionResponse]
    total: int
    skip: int
    limit: int


class CaseMinimal(BaseModel):
    id: int
    case_number: str
    title: str
    status: str
    priority: str
    category: str

    class Config:
        from_attributes = True


class CaseListResponse(BaseModel):
    items: List[CaseMinimal]
    total: int
    skip: int
    limit: int


class CreateInstitutionRequest(BaseModel):
    canonical_name: str
    short_name: Optional[str] = None
    institution_type: Optional[str] = None
    status: Optional[InstitutionStatus] = InstitutionStatus.ACTIVE
    state: Optional[str] = None
    district: Optional[str] = None
    city: Optional[str] = None
    region: Optional[str] = None
    address: Optional[str] = None
    pincode: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    website: Optional[str] = None
    data_source: Optional[str] = None


class UpdateInstitutionRequest(BaseModel):
    canonical_name: Optional[str] = None
    short_name: Optional[str] = None
    institution_type: Optional[str] = None
    status: Optional[InstitutionStatus] = None
    state: Optional[str] = None
    district: Optional[str] = None
    city: Optional[str] = None
    region: Optional[str] = None
    address: Optional[str] = None
    pincode: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    website: Optional[str] = None


class AddIdentifierRequest(BaseModel):
    id_type: str
    id_value: str
    source_system: Optional[str] = None
    is_primary: bool = False


# ─── Endpoints ────────────────────────────────────────────────────────────────


@router.get("/", response_model=InstitutionListResponse)
async def list_institutions(
    q: Optional[str] = None,
    state: Optional[str] = None,
    region: Optional[str] = None,
    institution_type: Optional[str] = None,
    inst_status: Optional[str] = Query(None, alias="status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    sort_by: str = Query("canonical_name"),
    _: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """List institutions with search and filter options."""
    try:
        query = db.query(Institution)
        if q:
            pattern = f"%{q}%"
            query = query.filter(
                or_(
                    Institution.canonical_name.ilike(pattern),
                    Institution.short_name.ilike(pattern),
                    Institution.city.ilike(pattern),
                )
            )
        if state:
            query = query.filter(Institution.state == state)
        if region:
            query = query.filter(Institution.region == region)
        if institution_type:
            query = query.filter(Institution.institution_type == institution_type)
        if inst_status:
            query = query.filter(Institution.status == inst_status)

        total = query.count()
        # Simple sorting
        sort_col = getattr(Institution, sort_by, Institution.canonical_name)
        institutions = query.order_by(sort_col).offset(skip).limit(limit).all()
        ids = [i.id for i in institutions]
        from sqlalchemy import func as _f
        totals = dict(db.query(Case.institution_id, _f.count(Case.id)).filter(
            Case.institution_id.in_(ids or [-1]), Case.is_active == True).group_by(Case.institution_id).all())  # noqa: E712
        open_statuses = ["received", "triaged", "assigned", "under_process", "awaiting_information",
                         "decision_review", "escalated", "reopened", "transfer_requested"]
        opens = dict(db.query(Case.institution_id, _f.count(Case.id)).filter(
            Case.institution_id.in_(ids or [-1]), Case.is_active == True,  # noqa: E712
            Case.status.in_(open_statuses)).group_by(Case.institution_id).all())
        items = [
            InstitutionResponse.model_validate(i).model_copy(update={
                "total_cases": totals.get(i.id, 0), "open_cases": opens.get(i.id, 0)})
            for i in institutions
        ]
        return InstitutionListResponse(items=items, total=total, skip=skip, limit=limit)
    except Exception as exc:
        logger.error("list_institutions error: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to fetch institutions.")


@router.post("/", response_model=InstitutionResponse, status_code=status.HTTP_201_CREATED)
async def create_institution(
    payload: CreateInstitutionRequest,
    current_user: User = Depends(require_roles(
        UserRole.SYSTEM_ADMIN.value, UserRole.DATA_ADMIN.value
    )),
    db: Session = Depends(get_db),
):
    """Create a new institution."""
    try:
        inst = Institution(
            canonical_name=payload.canonical_name,
            short_name=payload.short_name,
            institution_type=payload.institution_type,
            status=payload.status,
            state=payload.state,
            district=payload.district,
            city=payload.city,
            region=payload.region,
            address=payload.address,
            pincode=payload.pincode,
            phone=payload.phone,
            email=payload.email,
            website=payload.website,
            data_source=payload.data_source,
            created_by_id=current_user.id,
        )
        db.add(inst)
        db.commit()
        db.refresh(inst)
        log_audit(db, current_user.id, "create_institution", "institution", inst.id, f"Created {inst.canonical_name}")
        return inst
    except Exception as exc:
        db.rollback()
        logger.error("create_institution error: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to create institution.")


@router.get("/{institution_id}", response_model=InstitutionDetailResponse)
async def get_institution(
    institution_id: int,
    _: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Get institution detail with identifiers and case stats."""
    inst = db.query(Institution).filter(Institution.id == institution_id).first()
    if not inst:
        raise HTTPException(status_code=404, detail="Institution not found.")

    total_cases = db.query(Case).filter(Case.institution_id == institution_id).count()
    open_statuses = ["received", "triaged", "assigned", "under_process",
                     "awaiting_information", "decision_review", "escalated", "reopened"]
    open_cases = (
        db.query(Case)
        .filter(Case.institution_id == institution_id, Case.status.in_(open_statuses))
        .count()
    )

    return InstitutionDetailResponse(
        **{c.name: getattr(inst, c.name) for c in inst.__table__.columns},
        identifiers=inst.identifiers,
        total_cases=total_cases,
        open_cases=open_cases,
    )


@router.put("/{institution_id}", response_model=InstitutionResponse)
async def update_institution(
    institution_id: int,
    payload: UpdateInstitutionRequest,
    current_user: User = Depends(require_roles(
        UserRole.SYSTEM_ADMIN.value, UserRole.DATA_ADMIN.value
    )),
    db: Session = Depends(get_db),
):
    """Update institution details."""
    inst = db.query(Institution).filter(Institution.id == institution_id).first()
    if not inst:
        raise HTTPException(status_code=404, detail="Institution not found.")
    try:
        for field, value in payload.model_dump(exclude_none=True).items():
            setattr(inst, field, value)
        db.commit()
        db.refresh(inst)
        log_audit(db, current_user.id, "update_institution", "institution", inst.id, "Updated")
        return inst
    except Exception as exc:
        db.rollback()
        logger.error("update_institution error: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to update institution.")


@router.post("/{institution_id}/identifiers", response_model=IdentifierResponse, status_code=status.HTTP_201_CREATED)
async def add_identifier(
    institution_id: int,
    payload: AddIdentifierRequest,
    current_user: User = Depends(require_roles(
        UserRole.SYSTEM_ADMIN.value, UserRole.DATA_ADMIN.value
    )),
    db: Session = Depends(get_db),
):
    """Add an identifier to an institution."""
    inst = db.query(Institution).filter(Institution.id == institution_id).first()
    if not inst:
        raise HTTPException(status_code=404, detail="Institution not found.")
    try:
        identifier = InstitutionIdentifier(
            institution_id=institution_id,
            id_type=payload.id_type,
            id_value=payload.id_value,
            source_system=payload.source_system,
            is_primary=payload.is_primary,
        )
        db.add(identifier)
        db.commit()
        db.refresh(identifier)
        return identifier
    except Exception as exc:
        db.rollback()
        logger.error("add_identifier error: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to add identifier.")


@router.delete("/{institution_id}/identifiers/{identifier_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_identifier(
    institution_id: int,
    identifier_id: int,
    current_user: User = Depends(require_roles(
        UserRole.SYSTEM_ADMIN.value, UserRole.DATA_ADMIN.value
    )),
    db: Session = Depends(get_db),
):
    """Remove an identifier from an institution."""
    identifier = db.query(InstitutionIdentifier).filter(
        InstitutionIdentifier.id == identifier_id,
        InstitutionIdentifier.institution_id == institution_id,
    ).first()
    if not identifier:
        raise HTTPException(status_code=404, detail="Identifier not found.")
    try:
        db.delete(identifier)
        db.commit()
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to remove identifier.")


@router.get("/{institution_id}/cases", response_model=CaseListResponse)
async def get_institution_cases(
    institution_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    _: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Get paginated cases for an institution."""
    inst = db.query(Institution).filter(Institution.id == institution_id).first()
    if not inst:
        raise HTTPException(status_code=404, detail="Institution not found.")

    q = db.query(Case).filter(Case.institution_id == institution_id)
    total = q.count()
    cases = q.offset(skip).limit(limit).all()
    return CaseListResponse(items=cases, total=total, skip=skip, limit=limit)
