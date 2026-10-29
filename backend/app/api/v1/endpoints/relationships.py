"""Case relationship endpoints — Explainable Case Relationship Intelligence."""
import logging
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from app.core.security import get_current_active_user, require_roles
from app.db.session import get_db
from app.models.relationship import CaseRelationship, RelationshipReview, ReviewStatus, RelationshipType
from app.models.case import Case
from app.models.user import User, UserRole
from app.services.matching import detect_relationships, detect_cross_bureau_relationships
from app.services.audit import log_audit

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/relationships", tags=["relationships"])


class ReviewRequest(BaseModel):
    decision: str  # confirmed, rejected, corrected, escalated
    rationale: str
    corrected_type: Optional[str] = None


class CaseBrief(BaseModel):
    id: int
    case_number: str
    title: str
    category: str
    status: str
    class Config: from_attributes = True


class ReviewOut(BaseModel):
    id: int
    relationship_id: int
    decision: str
    reviewer_id: int
    corrected_type: Optional[str] = None
    rationale: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    class Config: from_attributes = True


class RelationshipOut(BaseModel):
    id: int
    case_a_id: int
    case_b_id: int
    case_a: Optional[CaseBrief] = None
    case_b: Optional[CaseBrief] = None
    relationship_type: str
    score: Optional[float] = None
    reasons: Optional[list] = None
    matching_evidence: Optional[dict] = None
    algorithm_version: Optional[str] = None
    review_status: str
    created_at: Optional[datetime] = None
    reviews: List[ReviewOut] = []
    class Config: from_attributes = True


class PaginatedRelationships(BaseModel):
    items: List[RelationshipOut]
    total: int
    skip: int
    limit: int


def _scope_relationship_query(query, current_user: User):
    """Keep bureau officers inside candidates involving their own bureau."""
    if current_user.role == UserRole.BUREAU_OFFICER:
        query = query.filter(or_(
            CaseRelationship.case_a.has(Case.bureau_id == current_user.bureau_id),
            CaseRelationship.case_b.has(Case.bureau_id == current_user.bureau_id),
        ))
    return query


@router.get("/inbox", response_model=PaginatedRelationships)
async def review_inbox(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Pending review inbox for coordination reviewers and admins."""
    query = (
        db.query(CaseRelationship)
        .options(joinedload(CaseRelationship.case_a), joinedload(CaseRelationship.case_b))
        .filter(CaseRelationship.review_status == ReviewStatus.PENDING)
        .order_by(CaseRelationship.created_at.desc())
    )
    query = _scope_relationship_query(query, current_user)
    total = query.count()
    items = query.offset(skip).limit(limit).all()
    return {"items": items, "total": total, "skip": skip, "limit": limit}


@router.get("/", response_model=PaginatedRelationships)
async def list_relationships(
    review_status: Optional[str] = Query(None),
    relationship_type: Optional[str] = Query(None),
    case_id: Optional[int] = Query(None),
    institution_id: Optional[int] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    query = db.query(CaseRelationship).options(
        joinedload(CaseRelationship.case_a), joinedload(CaseRelationship.case_b)
    )
    query = _scope_relationship_query(query, current_user)
    if review_status:
        try:
            query = query.filter(CaseRelationship.review_status == ReviewStatus(review_status))
        except ValueError:
            pass
    if relationship_type:
        try:
            query = query.filter(CaseRelationship.relationship_type == RelationshipType(relationship_type))
        except ValueError:
            pass
    if case_id:
        query = query.filter(
            (CaseRelationship.case_a_id == case_id) | (CaseRelationship.case_b_id == case_id)
        )
    if institution_id:
        query = query.filter(or_(
            CaseRelationship.case_a.has(Case.institution_id == institution_id),
            CaseRelationship.case_b.has(Case.institution_id == institution_id),
        ))
    total = query.count()
    items = query.order_by(CaseRelationship.created_at.desc()).offset(skip).limit(limit).all()
    return {"items": items, "total": total, "skip": skip, "limit": limit}


@router.get("/{rel_id}", response_model=RelationshipOut)
async def get_relationship(
    rel_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    rel = (
        db.query(CaseRelationship)
        .options(joinedload(CaseRelationship.case_a), joinedload(CaseRelationship.case_b),
                 joinedload(CaseRelationship.reviews))
        .filter(CaseRelationship.id == rel_id)
        .first()
    )
    if rel and current_user.role == UserRole.BUREAU_OFFICER and not (
        rel.case_a.bureau_id == current_user.bureau_id or
        rel.case_b.bureau_id == current_user.bureau_id
    ):
        rel = None
    if not rel:
        raise HTTPException(status_code=404, detail="Relationship not found")
    return rel


@router.post("/{rel_id}/review")
async def review_relationship(
    rel_id: int,
    payload: ReviewRequest,
    current_user: User = Depends(
        require_roles(UserRole.COORDINATION_REVIEWER, UserRole.SYSTEM_ADMIN, UserRole.SENIOR_MANAGEMENT)
    ),
    db: Session = Depends(get_db),
):
    """Submit human review for a relationship candidate.
    
    AI suggestions are NEVER automatically acted upon.
    Only human review changes the status.
    """
    rel = db.query(CaseRelationship).filter(CaseRelationship.id == rel_id).first()
    if not rel:
        raise HTTPException(status_code=404, detail="Relationship not found")

    try:
        decision = ReviewStatus(payload.decision)
    except ValueError:
        raise HTTPException(status_code=422, detail=f"Invalid decision: {payload.decision}")
    if decision == ReviewStatus.PENDING:
        raise HTTPException(status_code=422, detail="A review decision is required")
    if not payload.rationale.strip():
        raise HTTPException(status_code=422, detail="Rationale is required for a review decision")

    corrected_type = None
    if payload.corrected_type:
        try:
            corrected_type = RelationshipType(payload.corrected_type)
        except ValueError:
            raise HTTPException(status_code=422, detail=f"Invalid corrected_type: {payload.corrected_type}")

    review = RelationshipReview(
        relationship_id=rel_id,
        reviewer_id=current_user.id,
        decision=decision,
        corrected_type=corrected_type,
        rationale=payload.rationale,
    )
    db.add(review)

    # Update relationship status — but NEVER auto-merge/close cases
    rel.review_status = decision
    if corrected_type:
        rel.relationship_type = corrected_type

    try:
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Review submission failed")

    log_audit(db, current_user.id, "relationship_reviewed", "case_relationship", rel_id,
        f"Decision: {decision.value}; Rationale: {payload.rationale}")

    return {
        "message": "Review recorded successfully",
        "decision": decision.value,
        "note": "Underlying cases remain unchanged. No auto-merge or auto-close was performed.",
    }


@router.post("/detect/{case_id}")
async def trigger_detection(
    case_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Manually trigger relationship matching for a case."""
    case = db.query(Case).filter(Case.id == case_id, Case.is_active == True).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    if current_user.role == UserRole.BUREAU_OFFICER and case.bureau_id != current_user.bureau_id:
        raise HTTPException(status_code=404, detail="Case not found")

    try:
        results = detect_relationships(case, db)
    except Exception as e:
        logger.error("Matching failed: %s", e)
        return {"message": "Matching service unavailable", "candidates_found": 0, "service_available": False}

    return {
        "message": f"Detection complete",
        "candidates_found": len(results),
        "service_available": True,
        "candidates": [
            {"case_b_id": r["case_b_id"], "type": r["relationship_type"].value,
             "score": r["score"], "reasons": r["reasons"]}
            for r in results
        ]
    }


@router.post("/detect-all")
async def detect_all_relationships(
    current_user: User = Depends(
        require_roles(UserRole.SYSTEM_ADMIN, UserRole.DATA_ADMIN)
    ),
    db: Session = Depends(get_db),
):
    """Admin/Data Admin: trigger full cross-bureau relationship detection run.
    Returns summary of new relationships created."""
    try:
        summary = detect_cross_bureau_relationships(db)
    except Exception as exc:
        logger.error("detect_all_relationships failed: %s", exc)
        raise HTTPException(status_code=500, detail="Cross-bureau detection run failed")

    log_audit(
        db,
        current_user.id,
        "detect_all_relationships",
        "case_relationship",
        None,
        f"Cross-bureau detection run: {summary.get('new_relationships_created', 0)} new, "
        f"{summary.get('institutions_checked', 0)} institutions checked.",
    )

    return {
        **summary,
        "message": (
            f"Cross-bureau detection complete. "
            f"{summary.get('new_relationships_created', 0)} new relationship(s) created "
            f"across {summary.get('institutions_checked', 0)} institution(s)."
        ),
        "data_note": "DEMO DATA — Synthetic prototype data. Not official AICTE records.",
    }
