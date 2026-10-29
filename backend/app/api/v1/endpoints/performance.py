"""Monitoring & performance analytics required by PS 26264 §4 and §8.

* /analytics/overview     — the single-window dashboard numbers
* /analytics/performance  — monthly / quarterly performance with disposal rate
* /analytics/regions      — region-wise report
All figures are computed live from the case table and are role-scoped.
"""
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session, joinedload

from app.core.security import get_current_active_user
from app.db.session import get_db
from app.models.bureau import Bureau
from app.models.case import Case, CaseStatus
from app.models.user import User, UserRole

router = APIRouter(prefix="/analytics", tags=["analytics"])

DATA_NOTE = "DEMO DATA — Synthetic prototype data. Not official AICTE records."

PENDING = {"received", "triaged", "assigned", "awaiting_information", "reopened"}
UNDER_PROCESS = {"under_process", "decision_review"}
ESCALATED = {"escalated"}
TRANSFERRED = {"transfer_requested", "transferred"}
DISPOSED = {"disposed", "closed"}
OPEN = PENDING | UNDER_PROCESS | ESCALATED | {"transfer_requested"}


def _aware(dt):
    if dt is None:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _st(c) -> str:
    return getattr(c.status, "value", c.status)


def _cases(db: Session, user: User, bureau_id: Optional[int] = None, region: Optional[str] = None):
    q = db.query(Case).options(joinedload(Case.bureau), joinedload(Case.institution)).filter(Case.is_active == True)  # noqa: E712
    if user.role == UserRole.BUREAU_OFFICER:
        q = q.filter(Case.bureau_id == user.bureau_id)
    elif bureau_id:
        q = q.filter(Case.bureau_id == bureau_id)
    rows = q.all()
    if region:
        rows = [c for c in rows if c.institution and (c.institution.region or "").lower() == region.lower()]
    return rows


def _bucket(status: str) -> str:
    if status in PENDING:
        return "pending"
    if status in UNDER_PROCESS:
        return "under_process"
    if status in ESCALATED:
        return "escalated"
    if status in TRANSFERRED:
        return "transferred"
    if status in DISPOSED:
        return "disposed"
    return "pending"


def _disposal_days(c) -> Optional[float]:
    if not c.disposed_date:
        return None
    start = _aware(c.received_date or c.created_at)
    return max((_aware(c.disposed_date) - start).total_seconds() / 86400, 0) if start else None


@router.get("/overview")
async def overview(
    bureau_id: Optional[int] = Query(None),
    region: Optional[str] = Query(None),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    now = datetime.now(timezone.utc)
    cases = _cases(db, current_user, bureau_id, region)
    totals = {"received": len(cases), "pending": 0, "under_process": 0, "escalated": 0,
              "transferred": 0, "disposed": 0}
    overdue = approaching = 0
    for c in cases:
        totals[_bucket(_st(c))] += 1
        if _st(c) in OPEN and c.due_date:
            due = _aware(c.due_date)
            if due < now:
                overdue += 1
            elif due <= now + timedelta(days=7):
                approaching += 1
    disposed = [c for c in cases if _st(c) in DISPOSED]
    days = [d for d in (_disposal_days(c) for c in disposed) if d is not None]
    on_time = [c for c in disposed if c.disposed_date and c.due_date and _aware(c.disposed_date) <= _aware(c.due_date)]

    # Bureau workload
    bureaus: Dict[int, dict] = {}
    for b in db.query(Bureau).all():
        bureaus[b.id] = {"bureau_id": b.id, "code": b.code, "name": b.name, "total": 0, "open": 0,
                         "overdue": 0, "disposed": 0, "escalated": 0}
    for c in cases:
        row = bureaus.get(c.bureau_id)
        if not row:
            continue
        row["total"] += 1
        st = _st(c)
        if st in OPEN:
            row["open"] += 1
            if c.due_date and _aware(c.due_date) < now:
                row["overdue"] += 1
        if st in DISPOSED:
            row["disposed"] += 1
        if st in ESCALATED:
            row["escalated"] += 1
    workload = [dict(r, disposal_rate=round(r["disposed"] / r["total"] * 100, 1) if r["total"] else 0.0)
                for r in bureaus.values() if r["total"] or current_user.role != UserRole.BUREAU_OFFICER]
    workload.sort(key=lambda r: -r["total"])

    # Status-wise
    by_status: Dict[str, int] = {}
    for c in cases:
        by_status[_st(c)] = by_status.get(_st(c), 0) + 1

    # Institution-wise status (top 10 by open cases)
    inst_rows: Dict[int, dict] = {}
    for c in cases:
        if not c.institution:
            continue
        r = inst_rows.setdefault(c.institution_id, {
            "institution_id": c.institution_id, "name": c.institution.canonical_name,
            "short_name": c.institution.short_name, "region": c.institution.region,
            "total": 0, "open": 0, "overdue": 0, "disposed": 0, "bureaus": set()})
        r["total"] += 1
        if _st(c) in OPEN:
            r["open"] += 1
            if c.due_date and _aware(c.due_date) < now:
                r["overdue"] += 1
        if _st(c) in DISPOSED:
            r["disposed"] += 1
        if c.bureau:
            r["bureaus"].add(c.bureau.code)
    institutions = sorted(inst_rows.values(), key=lambda r: (-r["open"], -r["total"]))[:10]
    for r in institutions:
        r["bureaus"] = sorted(r["bureaus"])

    # Ageing of open cases
    ageing = {"0-7 days": 0, "8-30 days": 0, "31-60 days": 0, "61-90 days": 0, "90+ days": 0}
    for c in cases:
        if _st(c) not in OPEN:
            continue
        start = _aware(c.received_date or c.created_at)
        if not start:
            continue
        age = (now - start).days
        key = ("0-7 days" if age <= 7 else "8-30 days" if age <= 30 else "31-60 days" if age <= 60
               else "61-90 days" if age <= 90 else "90+ days")
        ageing[key] += 1

    # 12-month trend
    trend = []
    for i in range(11, -1, -1):
        y, m = now.year, now.month - i
        while m <= 0:
            m += 12
            y -= 1
        start = datetime(y, m, 1, tzinfo=timezone.utc)
        end = datetime(y + (m // 12), (m % 12) + 1, 1, tzinfo=timezone.utc)
        rec = sum(1 for c in cases if start <= (_aware(c.received_date or c.created_at) or now) < end)
        dis = sum(1 for c in cases if c.disposed_date and start <= _aware(c.disposed_date) < end)
        trend.append({"month": start.strftime("%b %y"), "received": rec, "disposed": dis})

    return {
        "totals": totals,
        "pending_beyond_timeline": overdue,
        "approaching_timeline": approaching,
        "disposal_rate": round(len(disposed) / len(cases) * 100, 1) if cases else 0.0,
        "avg_disposal_days": round(sum(days) / len(days), 1) if days else None,
        "on_time_disposal_rate": round(len(on_time) / len(disposed) * 100, 1) if disposed else None,
        "bureau_workload": workload,
        "by_status": by_status,
        "institutions": institutions,
        "ageing": [{"bucket": k, "count": v} for k, v in ageing.items()],
        "trend": trend,
        "generated_at": now.isoformat(),
        "filters": {"bureau_id": bureau_id, "region": region, "role_scope": current_user.role.value},
        "data_note": DATA_NOTE,
    }


def _period_key(dt: datetime, period: str) -> str:
    if period == "quarterly":
        # Indian financial year quarters: Q1 = Apr-Jun
        fy = dt.year if dt.month >= 4 else dt.year - 1
        q = ((dt.month - 4) % 12) // 3 + 1
        return f"FY{str(fy)[2:]}-{str(fy + 1)[2:]} Q{q}"
    return dt.strftime("%Y-%m")


def _period_label(key: str, period: str) -> str:
    if period == "quarterly":
        return key
    return datetime.strptime(key, "%Y-%m").strftime("%b %Y")


@router.get("/performance")
async def performance(
    period: str = Query("monthly", pattern="^(monthly|quarterly)$"),
    months: int = Query(12, ge=3, le=36),
    bureau_id: Optional[int] = Query(None),
    region: Optional[str] = Query(None),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Monthly / quarterly performance report: receipt, disposal, clearance rate, time-to-dispose."""
    now = datetime.now(timezone.utc)
    window_start = now - timedelta(days=int(months * 30.44))
    cases = _cases(db, current_user, bureau_id, region)
    keys: List[str] = []
    cursor = datetime(window_start.year, window_start.month, 1, tzinfo=timezone.utc)
    while cursor <= now:
        k = _period_key(cursor, period)
        if k not in keys:
            keys.append(k)
        cursor = datetime(cursor.year + (cursor.month // 12), (cursor.month % 12) + 1, 1, tzinfo=timezone.utc)
    rows = {k: {"period": k, "label": _period_label(k, period), "received": 0, "disposed": 0,
                "disposed_on_time": 0, "_days": []} for k in keys}
    for c in cases:
        rec = _aware(c.received_date or c.created_at)
        if rec and rec >= window_start:
            k = _period_key(rec, period)
            if k in rows:
                rows[k]["received"] += 1
        if c.disposed_date:
            dd = _aware(c.disposed_date)
            if dd >= window_start:
                k = _period_key(dd, period)
                if k in rows:
                    rows[k]["disposed"] += 1
                    d = _disposal_days(c)
                    if d is not None:
                        rows[k]["_days"].append(d)
                    if c.due_date and dd <= _aware(c.due_date):
                        rows[k]["disposed_on_time"] += 1
    out = []
    pending_running = sum(1 for c in cases if _aware(c.received_date or c.created_at) and
                          _aware(c.received_date or c.created_at) < window_start and
                          (not c.disposed_date or _aware(c.disposed_date) >= window_start))
    for k in keys:
        r = rows[k]
        days = r.pop("_days")
        pending_running += r["received"] - r["disposed"]
        out.append({
            **r,
            "clearance_rate": round(r["disposed"] / r["received"] * 100, 1) if r["received"] else None,
            "avg_disposal_days": round(sum(days) / len(days), 1) if days else None,
            "on_time_rate": round(r["disposed_on_time"] / r["disposed"] * 100, 1) if r["disposed"] else None,
            "pending_end": max(pending_running, 0),
        })

    by_bureau: Dict[str, dict] = {}
    for c in cases:
        code = c.bureau.code if c.bureau else "—"
        row = by_bureau.setdefault(code, {"bureau_code": code, "bureau_name": c.bureau.name if c.bureau else "Unassigned",
                                          "received": 0, "disposed": 0, "on_time": 0, "_days": []})
        rec = _aware(c.received_date or c.created_at)
        if rec and rec >= window_start:
            row["received"] += 1
        if c.disposed_date and _aware(c.disposed_date) >= window_start:
            row["disposed"] += 1
            d = _disposal_days(c)
            if d is not None:
                row["_days"].append(d)
            if c.due_date and _aware(c.disposed_date) <= _aware(c.due_date):
                row["on_time"] += 1
    bureau_rows = []
    for r in by_bureau.values():
        days = r.pop("_days")
        bureau_rows.append({**r,
                            "clearance_rate": round(r["disposed"] / r["received"] * 100, 1) if r["received"] else None,
                            "avg_disposal_days": round(sum(days) / len(days), 1) if days else None,
                            "on_time_rate": round(r["on_time"] / r["disposed"] * 100, 1) if r["disposed"] else None})
    bureau_rows.sort(key=lambda r: -r["received"])
    tot_rec = sum(r["received"] for r in out)
    tot_dis = sum(r["disposed"] for r in out)
    return {
        "period": period,
        "rows": out,
        "by_bureau": bureau_rows,
        "summary": {
            "received": tot_rec, "disposed": tot_dis,
            "clearance_rate": round(tot_dis / tot_rec * 100, 1) if tot_rec else None,
        },
        "definitions": {
            "clearance_rate": "Cases disposed in the period ÷ cases received in the period × 100",
            "on_time_rate": "Share of disposals completed on or before the expected disposal date",
            "quarters": "Indian financial-year quarters (Q1 = Apr–Jun)",
        },
        "generated_at": now.isoformat(),
        "data_note": DATA_NOTE,
    }


@router.get("/regions")
async def regions(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    now = datetime.now(timezone.utc)
    cases = _cases(db, current_user)
    out: Dict[str, dict] = {}
    for c in cases:
        reg = (c.institution.region if c.institution else None) or "Unmapped"
        r = out.setdefault(reg, {"region": reg, "total": 0, "open": 0, "overdue": 0, "disposed": 0,
                                 "institutions": set()})
        r["total"] += 1
        r["institutions"].add(c.institution_id)
        if _st(c) in OPEN:
            r["open"] += 1
            if c.due_date and _aware(c.due_date) < now:
                r["overdue"] += 1
        if _st(c) in DISPOSED:
            r["disposed"] += 1
    rows = []
    for r in out.values():
        rows.append({**r, "institutions": len(r["institutions"]),
                     "disposal_rate": round(r["disposed"] / r["total"] * 100, 1) if r["total"] else 0.0})
    rows.sort(key=lambda r: -r["total"])
    return {"items": rows, "generated_at": now.isoformat(), "data_note": DATA_NOTE}
