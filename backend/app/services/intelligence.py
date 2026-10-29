"""
DB-facing glue for the NYAYA SETU intelligence layer.

Turns ORM records into the pure-python facts consumed by
``identity.py`` (Institution Identity Resolution) and ``overlap.py``
(Overlap & Conflict Intelligence, Risk Radar), and implements the alert
scanner that turns timelines, escalations and overlaps into notifications.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, Iterable, List, Optional, Sequence

from sqlalchemy.orm import Session, joinedload

from app.services.identity import InstitutionProfile, profile_from_orm
from app.services.overlap import CaseFacts, analyze_institution, risk_profile, SEVERITY_ORDER

logger = logging.getLogger(__name__)

OPEN_EXCLUDED = ("disposed", "closed", "transferred")
OVERSIGHT_ROLES = ("system_admin", "senior_management", "coordination_reviewer")


def _aware(dt: Optional[datetime]) -> Optional[datetime]:
    if dt is None:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _status(value) -> str:
    return getattr(value, "value", value) or ""


def case_to_facts(case) -> CaseFacts:
    bureau = getattr(case, "bureau", None)
    actions = [a.description or "" for a in (getattr(case, "actions", None) or [])]
    if getattr(case, "next_action", None):
        actions.append(case.next_action)
    officer = getattr(case, "assigned_officer", None)
    return CaseFacts(
        id=case.id,
        case_number=case.case_number,
        bureau_id=case.bureau_id,
        bureau_code=bureau.code if bureau else "—",
        bureau_name=bureau.name if bureau else "Unassigned",
        category=case.category or "",
        title=case.title or "",
        summary=case.summary or "",
        status=_status(case.status),
        received_date=_aware(case.received_date or case.created_at),
        due_date=_aware(case.due_date),
        complainant_name=case.complainant_name,
        complainant_email=case.complainant_email,
        actions=actions,
        officer_name=officer.full_name if officer else None,
        institution_name=" ".join(filter(None, [getattr(getattr(case, "institution", None), "canonical_name", ""),
                                                  getattr(getattr(case, "institution", None), "city", "")])),
    )


# Files closed more than this many days ago are history: they stay in reports and in
# Institution 360°, but are not re-analysed for live overlap / risk on every request.
LIVE_WINDOW_DAYS = 180

_CACHE: Dict[tuple, tuple] = {}


def _data_signature(db: Session) -> tuple:
    """Cheap fingerprint of case + coordination data; any write changes it."""
    from sqlalchemy import func
    from app.models.case import Case, CaseAction
    from app.models.coordination import CoordinationItem
    return (
        db.query(func.count(Case.id), func.max(Case.created_at), func.max(Case.updated_at)).one(),
        db.query(func.max(CaseAction.id)).scalar(),
        db.query(func.count(CoordinationItem.id), func.max(CoordinationItem.updated_at)).one(),
        datetime.now(timezone.utc).date(),  # day-based rules (overdue, recency) roll over daily
    )


def _cached(db: Session, key: tuple, compute):
    sig = _data_signature(db)
    hit = _CACHE.get(key)
    if hit and hit[0] == sig:
        return hit[1]
    value = compute()
    _CACHE[key] = (sig, value)
    return value


def _live_filter(q, now: Optional[datetime] = None):
    """Open cases, plus cases closed or touched within LIVE_WINDOW_DAYS."""
    from sqlalchemy import or_
    from app.models.case import Case, CaseStatus
    now = now or datetime.now(timezone.utc)
    cutoff = now - timedelta(days=LIVE_WINDOW_DAYS)
    closed = [CaseStatus(s) for s in OPEN_EXCLUDED]
    return q.filter(or_(Case.status.notin_(closed), Case.disposed_date >= cutoff,
                        Case.last_action_date >= cutoff, Case.received_date >= cutoff))


def live_institution_ids(db: Session, min_bureaus: int = 1) -> List[int]:
    """Institutions with at least one open case and >= min_bureaus bureaus among their live cases."""
    from sqlalchemy import case as sql_case, func
    from app.models.case import Case, CaseStatus
    closed = [CaseStatus(s) for s in OPEN_EXCLUDED]
    q = db.query(Case.institution_id).filter(Case.is_active == True)  # noqa: E712
    q = _live_filter(q).group_by(Case.institution_id).having(
        func.sum(sql_case((Case.status.notin_(closed), 1), else_=0)) >= 1)
    if min_bureaus > 1:
        q = q.having(func.count(func.distinct(Case.bureau_id)) >= min_bureaus)
    return [i for (i,) in q.all()]


def load_cases(db: Session, institution_ids: Optional[Iterable[int]] = None, live_only: bool = False):
    from app.models.case import Case
    q = (
        db.query(Case)
        .options(
            joinedload(Case.bureau),
            joinedload(Case.actions),
            joinedload(Case.assigned_officer),
            joinedload(Case.institution),
        )
        .filter(Case.is_active == True)  # noqa: E712
    )
    if institution_ids is not None:
        ids = list(institution_ids)
        if not ids:
            return []
        q = q.filter(Case.institution_id.in_(ids))
    if live_only:
        q = _live_filter(q)
    return q.unique().all() if hasattr(q, "unique") else q.all()


def group_by_institution(cases) -> Dict[int, list]:
    groups: Dict[int, list] = {}
    for c in cases:
        groups.setdefault(c.institution_id, []).append(c)
    return groups


def case_brief(case) -> dict:
    last = None
    acts = sorted(case.actions or [], key=lambda a: _aware(a.created_at) or datetime.min.replace(tzinfo=timezone.utc))
    if acts:
        last = acts[-1]
    return {
        "id": case.id,
        "case_number": case.case_number,
        "source_case_id": case.source_case_id,
        "title": case.title,
        "category": case.category,
        "status": _status(case.status),
        "priority": _status(case.priority),
        "bureau_id": case.bureau_id,
        "bureau_code": case.bureau.code if case.bureau else None,
        "bureau_name": case.bureau.name if case.bureau else None,
        "officer": case.assigned_officer.full_name if case.assigned_officer else None,
        "received_date": _aware(case.received_date).isoformat() if case.received_date else None,
        "due_date": _aware(case.due_date).isoformat() if case.due_date else None,
        "last_action": last.description if last else None,
        "last_action_date": _aware(last.created_at).isoformat() if last and last.created_at else None,
        "next_action": case.next_action,
    }


def institution_brief(inst) -> dict:
    aicte = next((i.id_value for i in (inst.identifiers or []) if i.id_type == "aicte_permanent_id"), None)
    return {
        "id": inst.id,
        "canonical_name": inst.canonical_name,
        "short_name": inst.short_name,
        "city": inst.city,
        "state": inst.state,
        "region": inst.region,
        "aicte_id": aicte,
    }


_INST_CACHE: Dict[int, tuple] = {}


def _institution_signatures(db: Session, ids: List[int]) -> Dict[int, tuple]:
    """Per-institution fingerprint of its live cases: changes whenever one of them changes."""
    from sqlalchemy import func
    from app.models.case import Case
    if not ids:
        return {}
    today = datetime.now(timezone.utc).date()
    out: Dict[int, tuple] = {}
    for k in range(0, len(ids), 900):  # stay under SQLite's bound-parameter limit
        q = db.query(Case.institution_id, func.count(Case.id), func.max(Case.updated_at), func.max(Case.created_at),
                     func.max(Case.last_action_date)).filter(Case.is_active == True,  # noqa: E712
                                                             Case.institution_id.in_(ids[k:k + 900]))
        for iid, n, upd, cre, last in _live_filter(q).group_by(Case.institution_id).all():
            out[iid] = (n, upd, cre, last, today)
    return out


def _analysis_for(db: Session, ids: List[int]) -> Dict[int, Optional[dict]]:
    """Overlap analysis per institution, recomputed only for institutions whose cases changed."""
    sigs = _institution_signatures(db, ids)
    stale = [i for i in ids if _INST_CACHE.get(i, (None,))[0] != sigs.get(i)]
    for k in range(0, len(stale), 900):
        chunk = stale[k:k + 900]
        groups = group_by_institution(load_cases(db, chunk, live_only=True))
        for iid in chunk:
            items = groups.get(iid, [])
            entry = None
            if len({c.bureau_id for c in items if c.bureau_id}) >= 2 and \
                    any(_status(c.status) not in OPEN_EXCLUDED for c in items):
                analysis = analyze_institution([case_to_facts(c) for c in items])
                counts = analysis["classification_counts"]
                if len(analysis["active_bureaus"]) >= 2 or counts.get("action_conflict") or counts.get("duplicate"):
                    entry = {
                        "institution": institution_brief(items[0].institution),
                        "case_count": len(items),
                        "open_case_count": sum(1 for c in items if _status(c.status) not in OPEN_EXCLUDED),
                        "cases": [case_brief(c) for c in sorted(items, key=lambda c: c.case_number)],
                        "analysis": analysis,
                        "bureau_ids": sorted({c.bureau_id for c in items if c.bureau_id}),
                    }
            _INST_CACHE[iid] = (sigs.get(iid), entry)
    return {i: _INST_CACHE[i][1] for i in ids}


def overlap_clusters(db: Session, bureau_id: Optional[int] = None, include_low: bool = True) -> List[dict]:
    """Institutions whose complaints are handled by more than one bureau/cell.

    Analyses are cached per institution and recomputed only when that institution's
    cases change, so the radar stays fast at tens of thousands of cases.
    """
    from app.models.coordination import CoordinationItem, CoordinationStatus
    ids = live_institution_ids(db, min_bureaus=2)
    analyses = _analysis_for(db, ids)
    open_coords = {
        c.institution_id: c for c in db.query(CoordinationItem).filter(
            CoordinationItem.institution_id.isnot(None),
            CoordinationItem.status.notin_([CoordinationStatus.CLOSED, CoordinationStatus.DISMISSED]),
        ).all()
    }
    clusters = []
    for iid in ids:
        entry = analyses.get(iid)
        if not entry:
            continue
        if bureau_id and bureau_id not in entry["bureau_ids"]:
            continue
        if not include_low and entry["analysis"]["severity"] in ("low", "none"):
            continue
        coord = open_coords.get(iid)
        cluster = {k: v for k, v in entry.items() if k != "bureau_ids"}
        cluster["coordination"] = {
            "id": coord.id, "reference_number": coord.reference_number,
            "status": _status(coord.status), "lead_bureau_id": coord.lead_bureau_id,
        } if coord else None
        clusters.append(cluster)
    clusters.sort(key=lambda c: (-SEVERITY_ORDER[c["analysis"]["severity"]], -c["open_case_count"]))
    return clusters


_PROFILE_CACHE: Dict[str, tuple] = {}


def institution_profiles(db: Session) -> List[InstitutionProfile]:
    """Registry profiles for identity resolution, rebuilt only when the registry changes."""
    from sqlalchemy import func
    from app.models.institution import Institution, InstitutionIdentifier
    sig = (db.query(func.count(Institution.id), func.max(Institution.updated_at), func.max(Institution.created_at)).one(),
           db.query(func.count(InstitutionIdentifier.id), func.max(InstitutionIdentifier.id)).one())
    hit = _PROFILE_CACHE.get("all")
    if hit and hit[0] == sig:
        return hit[1]
    insts = db.query(Institution).options(joinedload(Institution.identifiers)).all()
    profiles = [profile_from_orm(i) for i in insts]
    _PROFILE_CACHE["all"] = (sig, profiles)
    return profiles


_RISK_CACHE: Dict[int, tuple] = {}


def risk_board(db: Session, limit: int = 50) -> List[dict]:
    """Risk score for institutions with open complaints; recomputed only where cases changed."""
    ids = live_institution_ids(db)
    sigs = _institution_signatures(db, ids)
    now = datetime.now(timezone.utc)
    stale = [i for i in ids if _RISK_CACHE.get(i, (None,))[0] != sigs.get(i)]
    for k in range(0, len(stale), 900):
        chunk = stale[k:k + 900]
        groups = group_by_institution(load_cases(db, chunk, live_only=True))
        for iid in chunk:
            items = groups.get(iid, [])
            if not items:
                _RISK_CACHE[iid] = (sigs.get(iid), None)
                continue
            facts = [case_to_facts(c) for c in items]
            overlap = analyze_institution(facts) if len({f.bureau_id for f in facts}) > 1 else None
            _RISK_CACHE[iid] = (sigs.get(iid), {
                "institution": institution_brief(items[0].institution),
                "risk": risk_profile(facts, now=now, overlap=overlap),
                "case_count": len(items),
                "bureaus": sorted({f.bureau_code for f in facts}),
            })
    rows = [_RISK_CACHE[i][1] for i in ids if _RISK_CACHE.get(i, (None, None))[1]]
    rows.sort(key=lambda r: -r["risk"]["score"])
    return rows[:limit]


def institution_360(db: Session, institution_id: int) -> Optional[dict]:
    from app.models.institution import Institution
    from app.models.coordination import CoordinationItem
    inst = db.query(Institution).options(joinedload(Institution.identifiers)).filter(
        Institution.id == institution_id).first()
    if not inst:
        return None
    items = load_cases(db, [institution_id])
    facts = [case_to_facts(c) for c in items]
    overlap = analyze_institution(facts) if len({f.bureau_id for f in facts if f.bureau_id}) > 1 else None
    risk = risk_profile(facts, overlap=overlap)
    timeline = []
    for c in items:
        for a in c.actions or []:
            timeline.append({
                "case_id": c.id, "case_number": c.case_number,
                "bureau_code": c.bureau.code if c.bureau else None,
                "action_type": a.action_type, "description": a.description,
                "performed_by": a.performed_by.full_name if a.performed_by else None,
                "created_at": _aware(a.created_at).isoformat() if a.created_at else None,
            })
    timeline.sort(key=lambda t: t["created_at"] or "", reverse=True)
    by_bureau: Dict[str, dict] = {}
    for c in items:
        code = c.bureau.code if c.bureau else "—"
        row = by_bureau.setdefault(code, {"bureau_code": code, "bureau_name": c.bureau.name if c.bureau else "Unassigned",
                                          "total": 0, "open": 0})
        row["total"] += 1
        if _status(c.status) not in OPEN_EXCLUDED:
            row["open"] += 1
    coords = db.query(CoordinationItem).filter(CoordinationItem.institution_id == institution_id).all()
    profile = profile_from_orm(inst)
    return {
        "institution": {
            **institution_brief(inst),
            "institution_type": inst.institution_type, "district": inst.district,
            "address": inst.address, "pincode": inst.pincode, "email": inst.email,
            "website": inst.website, "phone": inst.phone, "status": _status(inst.status),
            "data_source": inst.data_source,
            "identifiers": [{"id_type": i.id_type, "id_value": i.id_value, "is_verified": i.is_verified,
                             "source_system": i.source_system} for i in inst.identifiers],
            "known_aliases": profile.aliases,
        },
        "cases": [case_brief(c) for c in sorted(items, key=lambda c: _aware(c.received_date or c.created_at) or datetime.min.replace(tzinfo=timezone.utc), reverse=True)],
        "by_bureau": sorted(by_bureau.values(), key=lambda r: -r["total"]),
        "overlap": overlap,
        "risk": risk,
        "timeline": timeline[:80],
        "coordination": [{"id": c.id, "reference_number": c.reference_number, "title": c.title,
                          "status": _status(c.status), "lead_bureau_id": c.lead_bureau_id} for c in coords],
    }


# ─── Alerts ───────────────────────────────────────────────────────────────────

def _recently_notified(db: Session, user_id: int, ntype: str, case_id: Optional[int], hours: int = 20) -> bool:
    from app.models.notification import Notification
    since = datetime.now(timezone.utc) - timedelta(hours=hours)
    q = db.query(Notification).filter(
        Notification.user_id == user_id,
        Notification.notification_type == ntype,
        Notification.created_at >= since,
    )
    if case_id is not None:
        q = q.filter(Notification.related_case_id == case_id)
    return db.query(q.exists()).scalar()


def _notify(db: Session, user_id: int, title: str, message: str, ntype: str, priority: str,
            link: Optional[str], case_id: Optional[int], dedupe: bool = True) -> bool:
    from app.models.notification import Notification, NotificationPriority
    if dedupe and _recently_notified(db, user_id, ntype, case_id):
        return False
    try:
        prio = NotificationPriority(priority)
    except ValueError:
        prio = NotificationPriority.MEDIUM
    db.add(Notification(user_id=user_id, title=title, message=message, notification_type=ntype,
                        priority=prio, link_url=link, related_case_id=case_id))
    return True


def _oversight_users(db: Session):
    from app.models.user import User, UserRole
    return db.query(User).filter(
        User.is_active == True,  # noqa: E712
        User.role.in_([UserRole.SYSTEM_ADMIN, UserRole.SENIOR_MANAGEMENT, UserRole.COORDINATION_REVIEWER]),
    ).all()


def _bureau_users(db: Session, bureau_id: Optional[int]):
    from app.models.user import User
    if not bureau_id:
        return []
    return db.query(User).filter(User.is_active == True, User.bureau_id == bureau_id).all()  # noqa: E712


def run_alert_scan(db: Session) -> dict:
    """Generate timeline/SLA, reminder, escalation and overlap alerts. Idempotent per ~day."""
    now = datetime.now(timezone.utc)
    created = {"sla_breach": 0, "sla_approaching": 0, "pending_reminder": 0, "escalation": 0, "overlap": 0}
    from app.models.case import Case, CaseStatus
    cases = (db.query(Case).options(joinedload(Case.institution))
             .filter(Case.is_active == True, Case.status.notin_([CaseStatus(x) for x in OPEN_EXCLUDED])).all())  # noqa: E712
    oversight = _oversight_users(db)
    bureau_users: Dict[Optional[int], set] = {}
    for c in cases:
        status = _status(c.status)
        if c.bureau_id not in bureau_users:
            bureau_users[c.bureau_id] = {u.id for u in _bureau_users(db, c.bureau_id)}
        recipients = set(bureau_users[c.bureau_id])
        if c.assigned_officer_id:
            recipients.add(c.assigned_officer_id)
        due = _aware(c.due_date)
        link = f"/cases/{c.id}"
        if due and due < now:
            days = (now - due).days
            for uid in recipients:
                if _notify(db, uid, "Timeline breached",
                           f"{c.case_number} ({c.institution.short_name or c.institution.canonical_name}) is {days} day(s) past its prescribed timeline.",
                           "sla_breach", "high" if days < 15 else "urgent", link, c.id):
                    created["sla_breach"] += 1
        elif due and due <= now + timedelta(days=7):
            days = max((due - now).days, 0)
            for uid in recipients:
                if _notify(db, uid, "Approaching timeline",
                           f"{c.case_number} is due in {days} day(s). Next action: {c.next_action or 'not recorded'}.",
                           "sla_approaching", "medium", link, c.id):
                    created["sla_approaching"] += 1
        last = _aware(c.last_action_date) or _aware(c.received_date) or _aware(c.created_at)
        if last and (now - last).days >= 14:
            for uid in recipients:
                if _notify(db, uid, "Pending case reminder",
                           f"No action recorded on {c.case_number} for {(now - last).days} days.",
                           "pending_reminder", "medium", link, c.id):
                    created["pending_reminder"] += 1
        if status == "escalated":
            for u in oversight:
                if _notify(db, u.id, "Escalated case",
                           f"{c.case_number} — {c.title} has been escalated and needs senior attention.",
                           "escalation", "high", link, c.id):
                    created["escalation"] += 1
    for cluster in overlap_clusters(db):
        sev = cluster["analysis"]["severity"]
        if sev not in ("critical", "high"):
            continue
        inst = cluster["institution"]
        targets = {u.id for u in oversight}
        for cb in cluster["cases"]:
            targets |= {u.id for u in _bureau_users(db, cb["bureau_id"])}
        first_case = cluster["cases"][0]["id"] if cluster["cases"] else None
        for uid in targets:
            if _notify(db, uid, "Potential Overlapping Cases – Coordination Required",
                       f"{inst['short_name'] or inst['canonical_name']}: "
                       f"{(cluster['analysis']['pairs'][0]['headline'] if cluster['analysis']['pairs'] else 'related complaints')} "
                       f"— {', '.join(cluster['analysis']['bureaus_involved'])} involved ({sev}).",
                       "overlap", "urgent" if sev == "critical" else "high",
                       f"/overlaps?institution={inst['id']}", first_case):
                created["overlap"] += 1
    try:
        db.commit()
    except Exception as exc:  # pragma: no cover
        logger.error("Alert scan commit failed: %s", exc)
        db.rollback()
    return {"created": created, "total": sum(created.values()), "scanned_at": now.isoformat()}


def notify_case_overlap(db: Session, case) -> Optional[dict]:
    """Called when a case is created: alert other bureaus if the institution already has open files."""
    from app.models.case import Case
    others = db.query(Case).options(joinedload(Case.bureau)).filter(
        Case.institution_id == case.institution_id,
        Case.id != case.id,
        Case.is_active == True,  # noqa: E712
        Case.bureau_id != case.bureau_id,
    ).all()
    others = [o for o in others if _status(o.status) not in OPEN_EXCLUDED]
    if not others:
        return None
    bureaus = sorted({o.bureau.code for o in others if o.bureau})
    targets = {u.id for u in _oversight_users(db)}
    for o in others:
        if o.assigned_officer_id:
            targets.add(o.assigned_officer_id)
        targets |= {u.id for u in _bureau_users(db, o.bureau_id)}
    targets |= {u.id for u in _bureau_users(db, case.bureau_id)}
    for uid in targets:
        _notify(db, uid, "Potential Overlapping Cases – Coordination Required",
                f"New case {case.case_number} concerns an institution already handled by {', '.join(bureaus)}.",
                "overlap", "high", f"/overlaps?institution={case.institution_id}", case.id, dedupe=False)
    try:
        db.commit()
    except Exception:  # pragma: no cover
        db.rollback()
    return {"bureaus": bureaus, "open_cases": [o.case_number for o in others]}
