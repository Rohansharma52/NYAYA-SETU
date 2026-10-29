"""Reports and exports: case register (CSV/PDF), coordination register, Institution 360° dossier."""
import csv
import io
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy import func as sqlfunc
from sqlalchemy.orm import Session, joinedload, selectinload

from app.core.security import get_current_active_user
from app.db.session import get_db
from app.models.bureau import Bureau
from app.models.case import Case, CasePriority, CaseStatus
from app.models.coordination import CoordinationItem, CoordinationParticipant
from app.models.institution import Institution
from app.models.user import User, UserRole
from app.services.audit import log_audit

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/reports", tags=["reports"])


# ─── Shared helpers ──────────────────────────────────────────────────────────

STATUS_LABELS = {
    "received": "Received", "triaged": "Triaged", "assigned": "Assigned", "under_process": "Under process",
    "awaiting_information": "Awaiting information", "decision_review": "Decision review", "disposed": "Disposed",
    "transfer_requested": "Transfer requested", "transferred": "Transferred", "escalated": "Escalated",
    "reopened": "Reopened", "closed": "Closed",
}
FINISHED = {"disposed", "closed", "transferred"}
PENDING_GROUP = {"received", "triaged", "assigned", "awaiting_information", "reopened"}
IST_OFFSET = timedelta(hours=5, minutes=30)
DEMO_NOTE = "DEMO DATA - synthetic records for the SIH prototype. Not official AICTE data."


def _aware(dt: Optional[datetime]) -> Optional[datetime]:
    if dt is None:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _d(dt: Optional[datetime]) -> str:
    """Date as dd-mm-yyyy in IST (the way AICTE officers read dates)."""
    dt = _aware(dt)
    return (dt + IST_OFFSET).strftime("%d-%m-%Y") if dt else ""



def _status(c: Case) -> str:
    return c.status.value if hasattr(c.status, "value") else str(c.status)


def _days_overdue(c: Case, now: datetime) -> Optional[int]:
    due = _aware(c.due_date)
    if not due or _status(c) in FINISHED:
        return None
    days = (now - due).days
    return days if days > 0 else None


def _aicte_id(inst) -> str:
    if not inst:
        return ""
    for ident in inst.identifiers or []:
        if ident.id_type == "aicte_permanent_id":
            return ident.id_value
    return ""


def _stamp() -> str:
    return (datetime.now(timezone.utc) + IST_OFFSET).strftime("%Y%m%d_%H%M")


def _download(data: bytes, filename: str, media_type: str) -> Response:
    return Response(
        content=data, media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"',
                 "Access-Control-Expose-Headers": "Content-Disposition"},
    )


def _csv_bytes(header: List[str], rows: List[list]) -> bytes:
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(header)
    w.writerows(rows)
    w.writerow([])
    w.writerow([DEMO_NOTE])
    # UTF-8 with BOM so Excel shows ₹, — and Hindi text correctly
    return out.getvalue().encode("utf-8-sig")


def _case_query(db: Session, current_user: User, status: Optional[str], bureau_id: Optional[int],
                institution_id: Optional[int], region: Optional[str], category: Optional[str],
                priority: Optional[str], overdue: Optional[bool], limit: Optional[int] = None):
    query = _base_query(db, current_user, status, bureau_id, institution_id, region, category, priority, overdue)
    query = query.options(selectinload(Case.institution).selectinload(Institution.identifiers),
                          selectinload(Case.bureau), selectinload(Case.assigned_officer)).order_by(Case.case_number)
    if limit:
        query = query.limit(limit)
    return query.all()


def _base_query(db: Session, current_user: User, status: Optional[str], bureau_id: Optional[int],
                institution_id: Optional[int], region: Optional[str], category: Optional[str],
                priority: Optional[str], overdue: Optional[bool]):
    """All filters applied in SQL (including 'beyond timeline'), no row loading."""
    query = (db.query(Case).filter(Case.is_active == True)  # noqa: E712
             )
    if status:
        statuses = [s for s in status.split(",") if s in STATUS_LABELS]
        if statuses:
            query = query.filter(Case.status.in_([CaseStatus(s) for s in statuses]))
    if bureau_id:
        query = query.filter(Case.bureau_id == bureau_id)
    if institution_id:
        query = query.filter(Case.institution_id == institution_id)
    if category:
        query = query.filter(Case.category == category)
    if priority:
        try:
            query = query.filter(Case.priority == CasePriority(priority))
        except ValueError:
            pass
    if region:
        query = query.join(Institution, Case.institution_id == Institution.id).filter(Institution.region == region)
    if current_user.role == UserRole.BUREAU_OFFICER and current_user.bureau_id:
        query = query.filter(Case.bureau_id == current_user.bureau_id)
    if overdue:
        now = datetime.now(timezone.utc)
        query = query.filter(Case.due_date < now,
                             Case.status.notin_([CaseStatus(x) for x in FINISHED]))
    return query


def _filters_text(**kw) -> str:
    parts = [f"{k.replace('_', ' ').title()}: {v}" for k, v in kw.items() if v]
    return " | ".join(parts) if parts else "All cases in your scope"


# ─── CSV exports ──────────────────────────────────────────────────────────────

CASE_CSV_HEADER = [
    "Case ID", "Source reference", "Date of receipt", "Nature / category", "Title", "Institution",
    "AICTE Permanent ID", "Region", "State", "Bureau / Cell", "Current status", "Priority",
    "Assigned officer", "Date of last action", "Next action required", "Expected disposal date",
    "Days beyond timeline", "Disposed on",
]


@router.get("/cases/csv")
async def export_cases_csv(
    status: Optional[str] = Query(None, description="One status or a comma-separated list"),
    bureau_id: Optional[int] = Query(None),
    institution_id: Optional[int] = Query(None),
    region: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    overdue: Optional[bool] = Query(None),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Case register as CSV (opens cleanly in Excel). Same scope as the case list; logged to audit."""
    cases = _case_query(db, current_user, status, bureau_id, institution_id, region, category, priority, overdue)
    now = datetime.now(timezone.utc)
    rows = []
    for c in cases:
        inst = c.institution
        rows.append([
            c.case_number, c.source_case_id or "", _d(c.received_date or c.created_at), c.category, c.title,
            inst.canonical_name if inst else "", _aicte_id(inst), inst.region if inst else "",
            inst.state if inst else "", f"{c.bureau.code} - {c.bureau.name}" if c.bureau else "",
            STATUS_LABELS.get(_status(c), _status(c)), c.priority.value.title() if c.priority else "",
            c.assigned_officer.full_name if c.assigned_officer else "Unassigned",
            _d(c.last_action_date), c.next_action or "", _d(c.due_date),
            _days_overdue(c, now) or "", _d(c.disposed_date),
        ])
    log_audit(db, current_user.id, "csv_export_cases", "report", None,
              f"Exported {len(cases)} cases to CSV ({_filters_text(status=status, bureau_id=bureau_id, region=region)})")
    return _download(_csv_bytes(CASE_CSV_HEADER, rows), f"NYAYA_SETU_Cases_{_stamp()}.csv", "text/csv; charset=utf-8")


@router.get("/coordination/csv")
async def export_coordination_csv(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """One-Voice coordination register. Bureau officers get the items their bureau takes part in."""
    query = db.query(CoordinationItem).options(
        joinedload(CoordinationItem.participants), joinedload(CoordinationItem.tasks),
        joinedload(CoordinationItem.institution), joinedload(CoordinationItem.lead_bureau))
    if current_user.role == UserRole.BUREAU_OFFICER and current_user.bureau_id:
        query = query.filter(CoordinationItem.participants.any(CoordinationParticipant.bureau_id == current_user.bureau_id))
    items = query.order_by(CoordinationItem.reference_number).all()
    codes = {b.id: b.code for b in db.query(Bureau).all()}
    rows = []
    for it in items:
        parts = [p for p in it.participants if p.bureau_id]
        acked = sum(1 for p in parts if p.acknowledged)
        done = sum(1 for t in it.tasks if t.is_completed)
        rows.append([
            it.reference_number, it.title, it.institution.canonical_name if it.institution else "",
            it.lead_bureau.code if it.lead_bureau else "",
            ", ".join(codes.get(p.bureau_id, "") for p in parts if p.bureau_id != it.lead_bureau_id),
            it.status.value.replace("_", " ").title() if it.status else "",
            it.decision.value.replace("_", " ").title() if it.decision else "",
            f"{acked}/{len(parts)}", f"{done}/{len(it.tasks)}",
            _d(it.created_at), _d(it.acknowledge_by), _d(it.action_due_date), _d(it.closed_at),
        ])
    log_audit(db, current_user.id, "csv_export_coordination", "report", None, f"Coordination CSV export ({len(items)} items)")
    header = ["Reference", "Title", "Institution", "Lead bureau", "Supporting bureaus", "Status", "Decision",
              "Bureaus acknowledged", "Tasks complete", "Opened on", "Acknowledge by", "Action due", "Closed on"]
    return _download(_csv_bytes(header, rows), f"NYAYA_SETU_Coordination_{_stamp()}.csv", "text/csv; charset=utf-8")


@router.get("/summary")
async def summary_report(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Summary report. Explicitly labelled DEMO DATA."""
    from sqlalchemy import func
    total_cases = db.query(func.count(Case.id)).filter(Case.is_active == True).scalar()
    disposed = db.query(func.count(Case.id)).filter(Case.status == CaseStatus.DISPOSED).scalar()
    now = datetime.now(timezone.utc)
    return {
        "report_title": "NYAYA SETU — Summary Report",
        "generated_at": now.isoformat(),
        "generated_by": current_user.full_name,
        "data_disclaimer": DEMO_NOTE,
        "total_cases": total_cases,
        "disposed_cases": disposed,
        "disposition_rate": round(disposed / total_cases * 100, 1) if total_cases else 0,
        "reporting_period": "All time (prototype)",
    }


# ── PDF exports ─────────────────────────────────────────────────────────────────
try:
    from reportlab.lib import colors as rl_colors
    from reportlab.lib.enums import TA_LEFT
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
    REPORTLAB_AVAILABLE = True
except ImportError:  # pragma: no cover
    REPORTLAB_AVAILABLE = False

INK = "#0E1433"
ROYAL = "#4F46E5"
GOLD = "#D99A0B"
_FONTS: Optional[tuple] = None


def _fonts() -> tuple:
    """Register a Unicode TTF (₹, —, Hindi-safe fallbacks) once; fall back to Helvetica."""
    global _FONTS
    if _FONTS:
        return _FONTS
    candidates = [
        (r"C:\Windows\Fonts\arial.ttf", r"C:\Windows\Fonts\arialbd.ttf"),
        (r"C:\Windows\Fonts\segoeui.ttf", r"C:\Windows\Fonts\segoeuib.ttf"),
        ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
        ("/Library/Fonts/Arial.ttf", "/Library/Fonts/Arial Bold.ttf"),
    ]
    for regular, bold in candidates:
        if os.path.exists(regular) and os.path.exists(bold):
            try:
                pdfmetrics.registerFont(TTFont("NSRegular", regular))
                pdfmetrics.registerFont(TTFont("NSBold", bold))
                _FONTS = ("NSRegular", "NSBold", True)
                return _FONTS
            except Exception:  # pragma: no cover - corrupt font file
                continue
    _FONTS = ("Helvetica", "Helvetica-Bold", False)
    return _FONTS


def _txt(value, unicode_ok: bool) -> str:
    s = "" if value is None else str(value)
    s = s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    if not unicode_ok:
        s = s.replace("₹", "Rs. ")
    return s


def _check_reportlab():
    if not REPORTLAB_AVAILABLE:
        raise HTTPException(status_code=501, detail="PDF export unavailable. Run: pip install reportlab")


def _pdf(title: str, subtitle: str, user: User, blocks_fn, landscape_mode: bool = True) -> bytes:
    regular, bold, uni = _fonts()
    buf = io.BytesIO()
    size = landscape(A4) if landscape_mode else A4
    doc = SimpleDocTemplate(buf, pagesize=size, leftMargin=12 * mm, rightMargin=12 * mm,
                            topMargin=26 * mm, bottomMargin=14 * mm, title=title, author="NYAYA SETU")
    generated = (datetime.now(timezone.utc) + IST_OFFSET).strftime("%d %b %Y, %H:%M IST")

    def frame(canvas, d):
        w, h = size
        canvas.saveState()
        canvas.setFillColor(rl_colors.HexColor(INK))
        canvas.rect(0, h - 18 * mm, w, 18 * mm, fill=1, stroke=0)
        canvas.setFillColor(rl_colors.HexColor(GOLD))
        canvas.rect(0, h - 18.8 * mm, w, 0.8 * mm, fill=1, stroke=0)
        canvas.setFont(bold, 13)
        canvas.drawString(12 * mm, h - 9 * mm, "NYAYA SETU")
        canvas.setFont(regular, 8)
        canvas.setFillColor(rl_colors.HexColor("#C7CBEA"))
        canvas.drawString(12 * mm, h - 14 * mm, "AICTE · Integrated Institution Complaint Monitoring · SIH PS 26264")
        canvas.setFillColor(rl_colors.white)
        canvas.setFont(bold, 11)
        canvas.drawRightString(w - 12 * mm, h - 9 * mm, title)
        canvas.setFont(regular, 8)
        canvas.setFillColor(rl_colors.HexColor("#C7CBEA"))
        canvas.drawRightString(w - 12 * mm, h - 14 * mm, f"Generated {generated} by {user.full_name}")
        canvas.setFillColor(rl_colors.HexColor("#6B7280"))
        canvas.setFont(regular, 7.5)
        canvas.drawString(12 * mm, 7 * mm, DEMO_NOTE)
        canvas.drawRightString(w - 12 * mm, 7 * mm, f"Page {d.page}")
        canvas.restoreState()

    styles = {
        "h": ParagraphStyle("h", fontName=bold, fontSize=15, leading=19, textColor=rl_colors.HexColor(INK)),
        "sub": ParagraphStyle("sub", fontName=regular, fontSize=8.5, leading=11, textColor=rl_colors.HexColor("#6B7280")),
        "cell": ParagraphStyle("cell", fontName=regular, fontSize=7.2, leading=9, alignment=TA_LEFT),
        "cellb": ParagraphStyle("cellb", fontName=bold, fontSize=7.2, leading=9),
        "th": ParagraphStyle("th", fontName=bold, fontSize=7.2, leading=9, textColor=rl_colors.white),
        "kv": ParagraphStyle("kv", fontName=bold, fontSize=14, leading=16, textColor=rl_colors.HexColor(INK)),
        "kl": ParagraphStyle("kl", fontName=regular, fontSize=7.5, leading=9, textColor=rl_colors.HexColor("#6B7280")),
        "h2": ParagraphStyle("h2", fontName=bold, fontSize=10.5, leading=14, textColor=rl_colors.HexColor(INK), spaceBefore=6),
    }
    story = [Paragraph(_txt(title, uni), styles["h"]), Paragraph(_txt(subtitle, uni), styles["sub"]), Spacer(1, 5 * mm)]
    story += blocks_fn(styles, uni, size[0] - 24 * mm)
    doc.build(story, onFirstPage=frame, onLaterPages=frame)
    return buf.getvalue()


def _kpi_row(pairs, styles, width):
    cells = [[Paragraph(str(v), styles["kv"]), Paragraph(k, styles["kl"])] for k, v in pairs]
    t = Table([[Table([[a], [b]], style=[("LEFTPADDING", (0, 0), (-1, -1), 0)]) for a, b in cells]],
              colWidths=[width / len(pairs)] * len(pairs))
    t.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.6, rl_colors.HexColor("#E5E7EB")),
        ("INNERGRID", (0, 0), (-1, -1), 0.6, rl_colors.HexColor("#E5E7EB")),
        ("BACKGROUND", (0, 0), (-1, -1), rl_colors.HexColor("#F8FAFC")),
        ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
    ]))
    return t


def _data_table(header, rows, widths, styles, uni, highlight_rows=()):
    data = [[Paragraph(_txt(h, uni), styles["th"]) for h in header]]
    for r in rows:
        data.append([Paragraph(_txt(v, uni), styles["cellb"] if i == 0 else styles["cell"]) for i, v in enumerate(r)])
    t = Table(data, colWidths=widths, repeatRows=1)
    style = [
        ("BACKGROUND", (0, 0), (-1, 0), rl_colors.HexColor(INK)),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [rl_colors.white, rl_colors.HexColor("#F7F8FC")]),
        ("LINEBELOW", (0, 0), (-1, -1), 0.4, rl_colors.HexColor("#E5E7EB")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 3.5), ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5),
        ("LEFTPADDING", (0, 0), (-1, -1), 4), ("RIGHTPADDING", (0, 0), (-1, -1), 4),
    ]
    for i in highlight_rows:
        style.append(("BACKGROUND", (0, i + 1), (-1, i + 1), rl_colors.HexColor("#FFF1F2")))
    t.setStyle(TableStyle(style))
    return t


@router.get("/cases/pdf")
async def export_cases_pdf(
    status: Optional[str] = Query(None),
    bureau_id: Optional[int] = Query(None),
    institution_id: Optional[int] = Query(None),
    region: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    overdue: Optional[bool] = Query(None),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Case register as a printable landscape PDF with a status summary. Logged to audit."""
    _check_reportlab()
    PDF_MAX = 1000  # a printable register; the CSV export always carries every row
    base = _base_query(db, current_user, status, bureau_id, institution_id, region, category, priority, overdue)
    counts = {(_s.value if hasattr(_s, "value") else _s): n
              for _s, n in base.with_entities(Case.status, sqlfunc.count(Case.id)).group_by(Case.status).all()}
    now = datetime.now(timezone.utc)
    n_beyond = base.filter(Case.due_date < now, Case.status.notin_([CaseStatus(x) for x in FINISHED])).count()
    cases = _case_query(db, current_user, status, bureau_id, institution_id, region, category, priority, overdue, limit=PDF_MAX)
    total = sum(counts.values())
    if current_user.role == UserRole.BUREAU_OFFICER and current_user.bureau_id:
        bureau_id = current_user.bureau_id
    bureau = db.query(Bureau).filter(Bureau.id == bureau_id).first() if bureau_id else None
    scope = f"{bureau.code} - {bureau.name}" if bureau else "All Bureaus / Cells"
    filters = _filters_text(status=status and ", ".join(STATUS_LABELS.get(s, s) for s in status.split(",")),
                            region=region, category=category, priority=priority, overdue="Beyond timeline" if overdue else None)

    grp = lambda keys: sum(counts.get(k, 0) for k in keys)  # noqa: E731
    kpis = [("Total cases", f"{total:,}"), ("Pending", f"{grp(PENDING_GROUP):,}"),
            ("Under process", f"{grp({'under_process', 'decision_review'}):,}"),
            ("Disposed / closed", f"{grp({'disposed', 'closed'}):,}"),
            ("Transferred", f"{grp({'transfer_requested', 'transferred'}):,}"),
            ("Escalated", f"{counts.get('escalated', 0):,}"), ("Beyond timeline", f"{n_beyond:,}")]
    shown = cases
    beyond = [i for i, c in enumerate(shown) if _days_overdue(c, now)]

    def blocks(styles, uni, width):
        rows = []
        for c in shown:
            od = _days_overdue(c, now)
            rows.append([
                c.case_number, _d(c.received_date or c.created_at),
                f"{c.institution.canonical_name}" if c.institution else "",
                c.bureau.code if c.bureau else "", f"{c.title} ({c.category})",
                STATUS_LABELS.get(_status(c), _status(c)), c.priority.value.title() if c.priority else "",
                c.assigned_officer.full_name if c.assigned_officer else "Unassigned",
                _d(c.last_action_date), _d(c.due_date) + (f" ({od}d late)" if od else ""),
            ])
        mmw = [35, 18, 42, 14, 58, 22, 16, 24, 18, 26]  # = 273 mm usable landscape width
        out = [_kpi_row(kpis, styles, width), Spacer(1, 5 * mm)]
        out.append(_data_table(["Case ID", "Received", "Institution", "Bureau", "Complaint (nature)", "Status",
                                "Priority", "Officer", "Last action", "Expected disposal"],
                               rows, [width * w / sum(mmw) for w in mmw], styles, uni, highlight_rows=beyond))
        if not rows:
            out.append(Paragraph("No cases match the selected filters.", styles["sub"]))
        return out

    more = f"  ·  first {PDF_MAX:,} rows shown, use CSV for all" if total > PDF_MAX else ""
    pdf = _pdf("Case Register", f"Scope: {scope}  ·  {filters}  ·  {total:,} cases{more}  ·  rows in red are beyond the prescribed timeline",
               current_user, blocks)
    log_audit(db, current_user.id, "pdf_export", "cases", None, f"PDF export: {total} cases ({filters})")
    return _download(pdf, f"NYAYA_SETU_Case_Register_{_stamp()}.pdf", "application/pdf")


@router.get("/institution/{institution_id}/pdf")
async def export_institution_pdf(
    institution_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Institution 360° dossier: profile, bureau-wise split and complete complaint history."""
    _check_reportlab()
    inst = db.query(Institution).options(joinedload(Institution.identifiers)).filter(Institution.id == institution_id).first()
    if not inst:
        raise HTTPException(status_code=404, detail="Institution not found")
    cases = (db.query(Case).options(joinedload(Case.bureau), joinedload(Case.assigned_officer))
             .filter(Case.institution_id == institution_id, Case.is_active == True)  # noqa: E712
             .order_by(Case.received_date.desc()).all())
    now = datetime.now(timezone.utc)
    open_cases = [c for c in cases if _status(c) not in FINISHED]
    bureaus_open = sorted({c.bureau.code for c in open_cases if c.bureau})

    def blocks(styles, uni, width):
        prof = [["AICTE Permanent ID", _aicte_id(inst) or "—", "Region", inst.region or "—"],
                ["Short name", inst.short_name or "—", "City / State", f"{inst.city or '—'}, {inst.state or '—'}"],
                ["Type", inst.institution_type or "—", "Open files with", ", ".join(bureaus_open) or "None"]]
        pt = Table([[Paragraph(_txt(v, uni), styles["cellb"] if j % 2 == 0 else styles["cell"]) for j, v in enumerate(r)] for r in prof],
                   colWidths=[width * f for f in (0.16, 0.34, 0.14, 0.36)])
        pt.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.4, rl_colors.HexColor("#E5E7EB")),
                                ("BACKGROUND", (0, 0), (0, -1), rl_colors.HexColor("#F3F4F6")),
                                ("BACKGROUND", (2, 0), (2, -1), rl_colors.HexColor("#F3F4F6")),
                                ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4)]))
        kpis = [("Total complaints", len(cases)), ("Open", len(open_cases)),
                ("Bureaus involved", len({c.bureau_id for c in cases})),
                ("Beyond timeline", sum(1 for c in cases if _days_overdue(c, now)))]
        rows = [[c.case_number, _d(c.received_date or c.created_at), c.bureau.code if c.bureau else "",
                 f"{c.title} ({c.category})", STATUS_LABELS.get(_status(c), _status(c)),
                 c.assigned_officer.full_name if c.assigned_officer else "Unassigned", _d(c.due_date)] for c in cases]
        hl = [i for i, c in enumerate(cases) if _days_overdue(c, now)]
        return [pt, Spacer(1, 4 * mm), _kpi_row(kpis, styles, width), Spacer(1, 2 * mm),
                Paragraph("Consolidated complaint history (all Bureaus / Cells)", styles["h2"]), Spacer(1, 2 * mm),
                _data_table(["Case ID", "Received", "Bureau", "Complaint (nature)", "Status", "Officer", "Expected disposal"],
                            rows, [width * w / 273 for w in (36, 20, 16, 95, 34, 40, 32)], styles, uni, hl)]

    pdf = _pdf(f"Institution 360° — {inst.short_name or inst.canonical_name}", inst.canonical_name, current_user, blocks)
    log_audit(db, current_user.id, "pdf_export", "institution", institution_id, f"Institution PDF: {inst.canonical_name}")
    return _download(pdf, f"NYAYA_SETU_Institution_{inst.short_name or institution_id}_{_stamp()}.pdf", "application/pdf")
