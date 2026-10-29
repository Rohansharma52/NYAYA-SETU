"""NYAYA SETU intelligence endpoints.

Identity resolution, overlap & conflict intelligence, lead-bureau coordination,
risk radar, alert scanning and the live pulse feed. Every output is advisory;
an authorised officer confirms every link, coordination and closure.
"""
import logging
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.core.security import get_current_active_user, require_roles
from app.db.session import get_db
from app.models.bureau import Bureau
from app.models.case import Case, CaseAction, CaseStatus
from app.models.coordination import (
    CoordinationItem, CoordinationParticipant, CoordinationStatus, CoordinationTask, CoordinationDecision,
)
from app.models.user import User, UserRole
from app.services import intelligence as intel
from app.services.audit import log_audit
from app.services.identity import resolve
from app.services.identity_benchmark import run_benchmark
from app.services.notification import create_notification

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/intelligence", tags=["intelligence"])

DATA_NOTE = "DEMO DATA — Synthetic prototype data. Not official AICTE records."


class ResolveRequest(BaseModel):
    text: str = ""
    name: Optional[str] = None
    email: Optional[str] = None
    website: Optional[str] = None
    pincode: Optional[str] = None
    phone: Optional[str] = None
    aicte_id: Optional[str] = None
    top_k: int = 5


class CoordinateRequest(BaseModel):
    lead_bureau_id: Optional[int] = None
    note: Optional[str] = None


def _scope_bureau(user: User) -> Optional[int]:
    return user.bureau_id if user.role == UserRole.BUREAU_OFFICER else None


# ─── Identity resolution ──────────────────────────────────────────────────────

@router.post("/resolve")
async def resolve_institution(
    payload: ResolveRequest,
    _: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Rank registry institutions for a complaint snippet (name variants, Hindi, IDs, e-mail, address)."""
    if not any([payload.text.strip(), payload.name, payload.email, payload.website,
                payload.pincode, payload.phone, payload.aicte_id]):
        raise HTTPException(status_code=422, detail="Provide complaint text or at least one identifying field")
    profiles = intel.institution_profiles(db)
    result = resolve(
        profiles, text=payload.text, top_k=max(1, min(payload.top_k, 10)),
        name=payload.name, email=payload.email, website=payload.website,
        pincode=payload.pincode, phone=payload.phone, aicte_id=payload.aicte_id,
    )
    by_id = {p.id: p for p in profiles}
    for cand in result["candidates"]:
        p = by_id.get(cand["institution_id"])
        if p:
            cand.update({"short_name": p.short_name, "city": p.city, "state": p.state, "region": p.region,
                         "aicte_id": p.identifiers.get("aicte_permanent_id")})
    result["registry_size"] = len(profiles)
    return result


@lru_cache(maxsize=1)
def _cached_benchmark():
    return run_benchmark()


@router.get("/benchmark")
async def identity_benchmark(_: User = Depends(get_current_active_user)):
    """Reproducible precision/recall of identity resolution vs. baselines."""
    return {**_cached_benchmark(), "data_note": DATA_NOTE}


# ─── Overlap & conflict intelligence ──────────────────────────────────────────

@router.get("/overlaps")
async def list_overlaps(
    severity: Optional[str] = Query(None, description="critical | high | medium | low"),
    bureau_id: Optional[int] = Query(None),
    limit: int = Query(200, ge=0, le=5000, description="Max institutions returned; summary always covers all"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    scope = _scope_bureau(current_user) or bureau_id
    clusters = intel.overlap_clusters(db, bureau_id=scope)
    if severity:
        clusters = [c for c in clusters if c["analysis"]["severity"] == severity]
    summary = {"institutions": len(clusters), "critical": 0, "high": 0, "medium": 0, "low": 0,
               "conflicts": 0, "duplicates": 0, "awaiting_coordination": 0}
    for c in clusters:
        sev = c["analysis"]["severity"]
        if sev in summary:
            summary[sev] += 1
        counts = c["analysis"]["classification_counts"]
        summary["conflicts"] += counts.get("action_conflict", 0)
        summary["duplicates"] += counts.get("duplicate", 0)
        if c["analysis"]["coordination_required"] and not c["coordination"]:
            summary["awaiting_coordination"] += 1
    return {"summary": summary, "items": clusters[:limit], "total": len(clusters),
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "data_note": DATA_NOTE}


@router.get("/overlaps/{institution_id}")
async def get_overlap(
    institution_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    for c in intel.overlap_clusters(db, bureau_id=_scope_bureau(current_user)):
        if c["institution"]["id"] == institution_id:
            return c
    raise HTTPException(status_code=404, detail="No cross-bureau overlap for this institution")


@router.post("/overlaps/{institution_id}/coordinate", status_code=201)
async def start_one_voice_coordination(
    institution_id: int,
    payload: CoordinateRequest,
    current_user: User = Depends(require_roles(
        UserRole.SYSTEM_ADMIN, UserRole.SENIOR_MANAGEMENT, UserRole.COORDINATION_REVIEWER, UserRole.BUREAU_OFFICER)),
    db: Session = Depends(get_db),
):
    """Open a 'One Institution, One Voice' coordination item with a lead bureau."""
    cluster = next((c for c in intel.overlap_clusters(db) if c["institution"]["id"] == institution_id), None)
    if not cluster:
        raise HTTPException(status_code=404, detail="No cross-bureau overlap for this institution")
    if current_user.role == UserRole.BUREAU_OFFICER and current_user.bureau_id not in {
            c["bureau_id"] for c in cluster["cases"]}:
        raise HTTPException(status_code=403, detail="Your bureau is not involved in this overlap")
    if cluster["coordination"]:
        raise HTTPException(status_code=409, detail=f"Coordination {cluster['coordination']['reference_number']} is already open")

    analysis = cluster["analysis"]
    lead = analysis.get("lead_bureau") or {}
    lead_bureau_id = payload.lead_bureau_id or lead.get("bureau_id")
    lead_bureau = db.query(Bureau).filter(Bureau.id == lead_bureau_id).first() if lead_bureau_id else None
    if not lead_bureau:
        raise HTTPException(status_code=422, detail="A lead bureau is required")
    # Only bureaus whose files actually overlap take part; unrelated ("independent") files stay out.
    linked_pairs = [p for p in analysis["pairs"] if p.get("classification") != "independent"] or analysis["pairs"]
    linked_ids = {p["case_a_id"] for p in linked_pairs} | {p["case_b_id"] for p in linked_pairs}
    linked_cases = [c for c in cluster["cases"] if c["id"] in linked_ids] or cluster["cases"]
    bureau_ids = sorted({c["bureau_id"] for c in linked_cases if c["bureau_id"]} | {lead_bureau.id})

    count = db.query(func.count(CoordinationItem.id)).scalar() or 0
    ref = f"CCP-{datetime.now(timezone.utc).year}-{count + 1:04d}"
    now = datetime.now(timezone.utc)
    inst = cluster["institution"]
    lines = [analysis.get("banner") or "Cross-bureau coordination", ""]
    lines += [f"• {p['case_a_number']} ({p['bureau_a']}) ↔ {p['case_b_number']} ({p['bureau_b']}): {p['headline']}"
              for p in linked_pairs[:6]]
    if payload.note:
        lines += ["", f"Note: {payload.note}"]
    item = CoordinationItem(
        reference_number=ref,
        title=f"One-Voice Coordination — {inst['short_name'] or inst['canonical_name']}",
        description="\n".join(lines),
        owner_id=current_user.id,
        status=CoordinationStatus.ACTIVE,
        decision=CoordinationDecision.COORDINATE,
        decision_rationale="; ".join(lead.get("reasons", [])) or None,
        decision_by_id=current_user.id,
        decision_at=now,
        acknowledge_by=now + timedelta(days=3),
        action_due_date=now + timedelta(days=15),
        created_by_id=current_user.id,
        institution_id=institution_id,
        lead_bureau_id=lead_bureau.id,
    )
    db.add(item)
    db.flush()
    for bid in bureau_ids:
        db.add(CoordinationParticipant(
            coordination_item_id=item.id, bureau_id=bid,
            role_in_coordination="lead" if bid == lead_bureau.id else "supporting",
        ))
    tasks = [
        (f"{lead_bureau.code}: consolidate position of all bureaus", 5),
        ("Supporting bureaus: share file notes with the lead bureau", 3),
        (f"{lead_bureau.code}: issue one consolidated communication to the institution", 10),
        ("All bureaus: close source files with cross-reference to this coordination", 15),
    ]
    for title, days in tasks:
        db.add(CoordinationTask(coordination_item_id=item.id, title=title, due_date=now + timedelta(days=days),
                                created_by_id=current_user.id))
    for c in linked_cases:
        db.add(CaseAction(case_id=c["id"], action_type="coordination_linked",
                          description=f"Linked to {ref} — lead bureau {lead_bureau.code} (One Institution, One Voice)",
                          performed_by_id=current_user.id))
    try:
        db.commit()
    except Exception as exc:
        db.rollback()
        logger.error("Coordination creation failed: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to create coordination")

    officers = {u.id for u in db.query(User).filter(User.bureau_id.in_(bureau_ids), User.is_active == True).all()}  # noqa: E712
    for uid in officers:
        create_notification(db, uid, f"Coordination {ref} opened",
                            f"{lead_bureau.code} is lead bureau for {inst['canonical_name']}. Acknowledge within 3 days.",
                            "coordination", "high", f"/coordination/{item.id}", None, item.id)
    log_audit(db, current_user.id, "one_voice_coordination_created", "coordination_item", item.id,
              f"{ref} for institution {institution_id}; lead {lead_bureau.code}")
    return {"id": item.id, "reference_number": ref, "lead_bureau": lead_bureau.code,
            "message": f"{ref} opened with {lead_bureau.code} as lead bureau"}


# ─── Institution 360 & risk ───────────────────────────────────────────────────

@router.get("/institutions/{institution_id}/360")
async def institution_360(
    institution_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    data = intel.institution_360(db, institution_id)
    if not data:
        raise HTTPException(status_code=404, detail="Institution not found")
    # Cross-bureau visibility is intentional: avoiding duplicate action requires every
    # authorised officer to see which other Bureau/Cell is handling the institution.
    data["data_note"] = DATA_NOTE
    return data


@router.get("/risk")
async def risk_radar(
    limit: int = Query(50, ge=1, le=500),
    _: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    rows = intel.risk_board(db, limit=limit)
    levels = {"critical": 0, "high": 0, "elevated": 0, "low": 0}
    for r in rows:
        levels[r["risk"]["level"]] += 1
    return {"items": rows, "levels": levels, "generated_at": datetime.now(timezone.utc).isoformat(),
            "data_note": DATA_NOTE}


# ─── Alerts & live pulse ──────────────────────────────────────────────────────

@router.post("/alerts/scan")
async def scan_alerts(
    current_user: User = Depends(require_roles(
        UserRole.SYSTEM_ADMIN, UserRole.SENIOR_MANAGEMENT, UserRole.COORDINATION_REVIEWER, UserRole.DATA_ADMIN)),
    db: Session = Depends(get_db),
):
    result = intel.run_alert_scan(db)
    log_audit(db, current_user.id, "alert_scan", "notification", None, f"{result['total']} alerts generated")
    return result


@router.get("/pulse")
async def live_pulse(
    limit: int = Query(15, ge=1, le=50),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Latest workflow events across bureaus — polled by the UI for the live feed."""
    q = (
        db.query(CaseAction)
        .join(Case, CaseAction.case_id == Case.id)
        .options(joinedload(CaseAction.case).joinedload(Case.bureau),
                 joinedload(CaseAction.case).joinedload(Case.institution),
                 joinedload(CaseAction.performed_by))
        .filter(Case.is_active == True)  # noqa: E712
    )
    scope = _scope_bureau(current_user)
    if scope:
        q = q.filter(Case.bureau_id == scope)
    events = q.order_by(CaseAction.created_at.desc(), CaseAction.id.desc()).limit(limit).all()
    now = datetime.now(timezone.utc)
    return {
        "events": [{
            "id": e.id,
            "case_id": e.case_id,
            "case_number": e.case.case_number,
            "bureau_code": e.case.bureau.code if e.case.bureau else None,
            "institution": (e.case.institution.short_name or e.case.institution.canonical_name) if e.case.institution else None,
            "action_type": e.action_type,
            "description": e.description,
            "performed_by": e.performed_by.full_name if e.performed_by else None,
            "created_at": e.created_at.isoformat() if e.created_at else None,
        } for e in events],
        "server_time": now.isoformat(),
    }
