"""
NYAYA SETU — Demo Seed Script (SIH PS 26264)
=============================================

Creates bureaus (RB, PGRC, …), demo users, a FICTIONAL institution registry,
a scripted set of overlap / conflict scenarios that mirror the problem
statement, ~14 months of background complaint history for analytics, and
coordination items + alerts.

⚠ ALL DATA IS SYNTHETIC — NOT OFFICIAL AICTE RECORDS.

Usage:
    cd backend
    python seed.py            # create / top-up demo data (idempotent)
    python seed.py --reset    # drop all tables and rebuild the demo from scratch
"""
import os
import random
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv  # noqa: E402
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

from sqlalchemy.orm import Session  # noqa: E402

from app.core.security import get_password_hash  # noqa: E402
from app.data.registry import BUREAUS, INSTITUTIONS  # noqa: E402
from app.db.base import Base  # noqa: E402,F401  (imports every model)
from app.db.session import SessionLocal, engine  # noqa: E402
from app.models.bureau import Bureau  # noqa: E402
from app.models.case import Case, CaseAction, CaseAssignment, CasePriority, CaseStatus  # noqa: E402
from app.models.coordination import (  # noqa: E402
    CoordinationDecision, CoordinationItem, CoordinationParticipant, CoordinationStatus, CoordinationTask,
)
from app.models.deadline import DeadlineRule  # noqa: E402
from app.models.institution import Institution, InstitutionIdentifier  # noqa: E402
from app.models.relationship import CaseRelationship, RelationshipType, ReviewStatus  # noqa: E402
from app.models.transfer import TransferRequest, TransferStatus  # noqa: E402
from app.models.user import AccountStatus, User, UserRole  # noqa: E402

DEMO_NOTE = "[DEMO DATA] Synthetic record — Not official AICTE data"
NOW = datetime.now(timezone.utc)
RNG = random.Random(26264)


def days_ago(n: float) -> datetime:
    return NOW - timedelta(days=n)


# ─── Masters ──────────────────────────────────────────────────────────────────

def seed_bureaus(db: Session) -> dict:
    out = {}
    for b in BUREAUS:
        row = db.query(Bureau).filter(Bureau.code == b["code"]).first()
        if not row:
            row = Bureau(**b, is_active=True)
            db.add(row)
            db.flush()
        out[b["code"]] = row
    db.commit()
    print(f"✓ Bureaus: {', '.join(out)}")
    return out


USERS = [
    ("admin@aicte.demo", "System Administrator", UserRole.SYSTEM_ADMIN, None, "System Administrator", None, "Admin@123456"),
    ("management@aicte.demo", "Dr. Rajesh Kumar", UserRole.SENIOR_MANAGEMENT, None, "Director (Monitoring), AICTE", None, "Demo@123456"),
    ("officer1@aicte.demo", "Priya Sharma", UserRole.BUREAU_OFFICER, "RB", "Section Officer, Regulation Bureau", None, "Demo@123456"),
    ("officer2@aicte.demo", "Amit Verma", UserRole.BUREAU_OFFICER, "PGRC", "Grievance Officer, PGRC", None, "Demo@123456"),
    ("officer3@aicte.demo", "Vikram Nair", UserRole.BUREAU_OFFICER, "AB", "Technical Officer, Approval Bureau", None, "Demo@123456"),
    ("officer4@aicte.demo", "Neha Iyer", UserRole.BUREAU_OFFICER, "ACAD", "Assistant Director, Academic Bureau", None, "Demo@123456"),
    ("officer5@aicte.demo", "Arjun Mehta", UserRole.BUREAU_OFFICER, "FIN", "Section Officer, Finance & Scholarship", None, "Demo@123456"),
    ("officer6@aicte.demo", "Kavita Rao", UserRole.BUREAU_OFFICER, "PGRC", "Deputy Director, PGRC", None, "Demo@123456"),
    ("officer7@aicte.demo", "Sandeep Gill", UserRole.BUREAU_OFFICER, "RB", "Deputy Director, Regulation Bureau", None, "Demo@123456"),
    ("reviewer@aicte.demo", "Sunita Patel", UserRole.COORDINATION_REVIEWER, None, "Coordination Analyst", None, "Demo@123456"),
    ("datamgr@aicte.demo", "Rahul Singh", UserRole.DATA_ADMIN, None, "Data Manager", None, "Demo@123456"),
    ("regional@aicte.demo", "Meena Gupta", UserRole.REGIONAL_OFFICER, None, "Regional Officer", "North-West", "Demo@123456"),
]


def seed_users(db: Session, bureaus: dict) -> dict:
    out = {}
    for email, name, role, bcode, desig, region, pwd in USERS:
        u = db.query(User).filter(User.email == email).first()
        if not u:
            u = User(email=email, full_name=name, role=role, designation=desig, region=region,
                     bureau_id=bureaus[bcode].id if bcode else None,
                     hashed_password=get_password_hash(pwd), account_status=AccountStatus.ACTIVE, is_active=True)
            db.add(u)
            db.flush()
        out[email.split("@")[0]] = u
    db.commit()
    print(f"✓ Users: {len(out)}")
    return out


def seed_institutions(db: Session, admin: User) -> dict:
    out = {}
    for d in INSTITUTIONS:
        inst = db.query(Institution).filter(Institution.canonical_name == d["canonical_name"]).first()
        if not inst:
            inst = Institution(
                canonical_name=d["canonical_name"], short_name=d["short_name"],
                institution_type=d["institution_type"], state=d["state"], district=d["district"],
                city=d["city"], region=d["region"], address=d["address"], pincode=d["pincode"],
                phone=d["phone"], email=d["email"], website=d["website"],
                data_source="demo_registry", import_notes=DEMO_NOTE, source_last_synced=NOW,
                created_by_id=admin.id,
            )
            db.add(inst)
            db.flush()
            idents = [
                ("aicte_permanent_id", d["aicte_id"], "AICTE Approval Portal (demo)", True, True),
                ("aishe_code", d["aishe"], "AISHE (demo)", False, True),
                ("hindi_name", d["hindi_name"], "Registry alias", False, True),
            ] + [("alias", a, "Observed in complaints", False, False) for a in d.get("aliases", [])]
            for t, v, src, primary, verified in idents:
                db.add(InstitutionIdentifier(institution_id=inst.id, id_type=t, id_value=v, source_system=src,
                                             is_primary=primary, is_verified=verified))
        out[d["key"]] = inst
    db.commit()
    print(f"✓ Institutions: {len(out)} (fictional registry)")
    return out


# ─── Cases ────────────────────────────────────────────────────────────────────

_counter = {"n": 0}


def _case_number() -> str:
    _counter["n"] += 1
    return f"AICTE-NS-{NOW.year}-{_counter['n']:05d}"


def make_case(db: Session, *, inst, bureau, title, category, summary, status, priority="medium",
              received=10, due_in=None, officer=None, actor=None, source=None, complainant=None,
              email=None, actions=(), next_action=None, disposed_after=None) -> Case:
    rec = days_ago(received)
    due = rec + timedelta(days=due_in) if due_in is not None else None
    case = Case(
        case_number=_case_number(), source_case_id=source,
        source_system={"PGRC": "CPGRAMS / AICTE Grievance Portal", "RB": "e-Office", "AB": "AICTE Approval Portal",
                       "ACAD": "e-Office", "FIN": "Scholarship Portal"}.get(bureau.code, "Manual entry"),
        institution_id=inst.id, bureau_id=bureau.id, assigned_officer_id=officer.id if officer else None,
        title=title, summary=summary, category=category, status=status, priority=CasePriority(priority),
        complainant_name=complainant, complainant_email=email, received_date=rec, due_date=due,
        next_action=next_action, created_by_id=(actor or officer).id if (actor or officer) else None,
    )
    if disposed_after is not None:
        case.disposed_date = min(rec + timedelta(days=disposed_after), NOW - timedelta(hours=2))
    db.add(case)
    db.flush()
    by = officer or actor
    db.add(CaseAction(case_id=case.id, action_type="created", new_status=CaseStatus.RECEIVED,
                      description=f"Complaint received via {case.source_system}" + (f" (ref {source})" if source else ""),
                      performed_by_id=by.id if by else None, created_at=rec))
    if officer:
        db.add(CaseAssignment(case_id=case.id, assigned_to_id=officer.id, assigned_by_id=officer.id,
                              bureau_id=bureau.id, notes="Initial assignment", assigned_at=rec + timedelta(hours=6)))
        db.add(CaseAction(case_id=case.id, action_type="assigned", description=f"Assigned to {officer.full_name}",
                          performed_by_id=officer.id, created_at=rec + timedelta(hours=6)))
    last = rec + timedelta(hours=6)
    for offset, atype, text, new_status in actions:
        when = min(rec + timedelta(days=offset), NOW - timedelta(hours=1))
        db.add(CaseAction(case_id=case.id, action_type=atype, description=text,
                          new_status=new_status, performed_by_id=by.id if by else None, created_at=when))
        last = max(last, when)
    case.last_action_date = last
    return case


def seed_scenarios(db: Session, b: dict, u: dict, i: dict) -> list:
    S = CaseStatus
    cases = []

    # S1 — PS 26264 example: same institution, PGRC + RB + FIN acting in parallel on fees
    cases.append(make_case(
        db, inst=i["aiet"], bureau=b["PGRC"], officer=u["officer2"], received=18, due_in=30,
        source="DHEDU/E/2026/0048213", complainant="Rohit Kumar", email="rohit.k@example.com",
        title="Excess fee charged and refund of ₹45,000 denied — B.Tech 2nd year",
        category="Fee Refund", status=S.UNDER_PROCESS, priority="high",
        summary="Complaint received on CPGRAMS naming 'A.I.E.T. Faridabad'. Students allege collection of ₹45,000 "
                "above the approved fee and refusal to refund.",
        actions=[(0.2, "identity_resolved", "Institution resolved from 'A.I.E.T. Faridabad' → AIET (IRE confidence 0.75: acronym + location)", None),
                 (2, "status_change", "Taken up for examination", S.UNDER_PROCESS),
                 (4, "letter_issued", "Letter issued to institution seeking para-wise reply within 15 days", None)],
        next_action="Examine institution's reply; decide on refund direction"))
    cases.append(make_case(
        db, inst=i["aiet"], bureau=b["RB"], officer=u["officer1"], received=9, due_in=45,
        source="F.No. RB/NWRO/2026/117", complainant="Parents' Association, Faridabad",
        title="Fee collected beyond Fee Regulatory Committee approval",
        category="Fee Regulation", status=S.UNDER_PROCESS, priority="urgent",
        summary="Representation alleging systematic collection of fee beyond the approved fee structure for "
                "B.Tech programmes at Aravali Institute of Engineering & Technology.",
        actions=[(1, "status_change", "Prima facie violation of approval conditions", S.UNDER_PROCESS),
                 (3, "show_cause", "Show-cause notice issued to institution under approval conditions", None)],
        next_action="Await reply to show-cause; consider expert committee inspection"))
    cases.append(make_case(
        db, inst=i["aiet"], bureau=b["FIN"], officer=u["officer5"], received=12, due_in=30,
        source="AICTE-GRV-2026-11872", complainant="Rohit Kumar", email="rohit.k@example.com",
        title="Refund of excess fee ₹45,000 not given — B.Tech",
        category="Fee Refund", status=S.ASSIGNED, priority="medium",
        summary="Same student writes to the Finance cell about refund of ₹45,000 excess fee charged by AIET Faridabad.",
        actions=[], next_action="Verify fee receipts"))

    # S2 — Critical conflict: PGRC closed as resolved while RB is pursuing penal action
    cases.append(make_case(
        db, inst=i["git"], bureau=b["PGRC"], officer=u["officer6"], received=64, due_in=30, disposed_after=27,
        source="DHEDU/E/2026/0031177", complainant="Ananya Bisht",
        title="Caution money and excess tuition fee not refunded",
        category="Fee Refund", status=S.DISPOSED, priority="medium",
        summary="Complainant sought refund of caution money and excess tuition fee from Gangotri Institute of Technology.",
        actions=[(3, "letter_issued", "Letter issued to institution for comments", None),
                 (27, "status_change", "Disposed: institution assured refund; complainant satisfied", S.DISPOSED)]))
    cases.append(make_case(
        db, inst=i["git"], bureau=b["RB"], officer=u["officer7"], received=40, due_in=37,
        source="F.No. RB/NRO/2026/089", complainant="Student Council, GIT",
        title="Excess fee collection from multiple batches — norms violation",
        category="Fee Regulation", status=S.ESCALATED, priority="urgent",
        summary="Multiple batches report excess fee collection; inspection found fee receipts above approved structure.",
        actions=[(5, "inspection", "Expert committee inspection conducted", S.UNDER_PROCESS),
                 (22, "status_change", "Penal action proposed: withdrawal of approval under consideration", S.ESCALATED)],
        next_action="Placement before competent authority for penal action"))

    # S3 — Independent issues, two bureaus (informational)
    cases.append(make_case(
        db, inst=i["nvec"], bureau=b["PGRC"], officer=u["officer2"], received=6, due_in=30,
        source="DHEDU/E/2026/0051002", complainant="Hostel residents",
        title="Poor hostel mess food quality", category="Student Welfare", status=S.RECEIVED, priority="low",
        summary="Residents complain about mess food quality and hygiene in the boys' hostel.",
        next_action="Forward to institution for action taken report"))
    cases.append(make_case(
        db, inst=i["nvec"], bureau=b["ACAD"], officer=u["officer4"], received=21, due_in=45,
        source="F.No. ACAD/2026/412", title="Delay in declaration of semester examination results",
        category="Examination", status=S.UNDER_PROCESS, priority="medium",
        summary="Results of the odd semester examination not declared even after 90 days.",
        actions=[(2, "status_change", "Sought status from affiliating university", S.UNDER_PROCESS)],
        next_action="Follow up with university"))

    # S4 — Related pattern: same issue via two channels
    cases.append(make_case(
        db, inst=i["simt"], bureau=b["PGRC"], officer=u["officer6"], received=15, due_in=30,
        source="DHEDU/E/2026/0046650", complainant="Kiran Patil",
        title="Fake placement claims in admission brochure", category="Placement",
        status=S.TRIAGED, priority="medium",
        summary="Brochure claims 100% placement with average package of 12 LPA; students allege the claims are false."))
    cases.append(make_case(
        db, inst=i["simt"], bureau=b["AB"], officer=u["officer3"], received=11, due_in=60,
        source="F.No. AB/WRO/2026/233", title="Misleading placement advertisement during admissions",
        category="Placement", status=S.UNDER_PROCESS, priority="medium",
        summary="Advertisement in newspapers with unverifiable placement statistics during admission season.",
        actions=[(2, "status_change", "Examination of advertisement against approval handbook", S.UNDER_PROCESS)]))

    # S5 — Transfer into an existing file
    pg = make_case(
        db, inst=i["miet"], bureau=b["PGRC"], officer=u["officer2"], received=25, due_in=30,
        source="DHEDU/E/2026/0039004", complainant="Faculty Association, MIET",
        title="Faculty salaries not paid for four months", category="Faculty",
        status=S.TRANSFER_REQUESTED, priority="high",
        summary="Faculty members of Malabar Institute of Engineering & Technology have not received salary for four months.",
        actions=[(6, "transfer_requested", "Transfer requested to Regulation Bureau: matter concerns faculty norms", S.TRANSFER_REQUESTED)])
    cases.append(pg)
    rb_miet = make_case(
        db, inst=i["miet"], bureau=b["RB"], officer=u["officer1"], received=33, due_in=60,
        source="F.No. RB/SRO/2026/054", title="Faculty shortage and unpaid salaries — norms violation",
        category="Faculty", status=S.UNDER_PROCESS, priority="high",
        summary="Faculty-student ratio below norms; reports of unpaid salaries.",
        actions=[(4, "status_change", "Compliance report sought from institution", S.UNDER_PROCESS)])
    cases.append(rb_miet)
    db.flush()
    db.add(TransferRequest(case_id=pg.id, from_bureau_id=b["PGRC"].id, to_bureau_id=b["RB"].id,
                           from_officer_id=u["officer2"].id, reason="Matter concerns faculty norms under RB's mandate",
                           status=TransferStatus.REQUESTED, requested_by_id=u["officer2"].id,
                           requested_at=days_ago(19)))

    # S6 — Systemic issue, coordination already running (risk radar)
    for k, (bc, off, rec, title, st) in enumerate([
        ("PGRC", "officer2", 150, "Development fee charged without approval", S.DISPOSED),
        ("FIN", "officer5", 110, "Scholarship students asked to pay full tuition fee", S.UNDER_PROCESS),
        ("PGRC", "officer6", 70, "Refund of fee after withdrawal of admission denied", S.UNDER_PROCESS),
        ("RB", "officer7", 45, "Capitation fee demanded at the time of admission", S.UNDER_PROCESS),
    ]):
        cases.append(make_case(
            db, inst=i["cits"], bureau=b[bc], officer=u[off], received=rec, due_in=45,
            disposed_after=40 if st == S.DISPOSED else None,
            source=f"CITS-REF-{k + 1:03d}", title=title, category="Fee Regulation" if bc == "RB" else "Fee Refund",
            status=st, priority="high",
            summary=f"{title} at Chambal Institute of Technology & Science, Gwalior.",
            actions=[(3, "letter_issued", "Letter issued to institution seeking compliance", None)] +
                    ([(40, "status_change", "Disposed after institution reversed the levy", S.DISPOSED)] if st == S.DISPOSED else [])))
    db.commit()
    print(f"✓ Scenario cases: {len(cases)} (PS overlap, conflict, duplicate, transfer, systemic)")
    return cases


CATEGORY_BUREAU = {
    "Fee Refund": ["PGRC", "FIN"], "Fee Regulation": ["RB"], "Infrastructure": ["RB", "AB"],
    "Faculty": ["RB", "ACAD"], "Examination": ["ACAD"], "Certificates": ["PGRC"],
    "Student Welfare": ["PGRC"], "Scholarship": ["FIN"], "Admission": ["AB", "RB"], "Placement": ["AB", "PGRC"],
}
TITLES = {
    "Fee Refund": ["Refund of fee after cancellation not processed", "Excess hostel fee collected", "Caution money not refunded"],
    "Fee Regulation": ["Fee charged above approved structure", "Collection of capitation fee alleged"],
    "Infrastructure": ["Laboratories not functional as per norms", "Library lacks prescribed titles", "Classrooms below prescribed area"],
    "Faculty": ["Shortage of qualified faculty", "Faculty salary delayed", "Ad-hoc faculty shown as regular"],
    "Examination": ["Revaluation results pending", "Examination conducted without notice", "Marks not uploaded to university portal"],
    "Certificates": ["Original certificates withheld", "Migration certificate not issued", "Transcript not issued after payment"],
    "Student Welfare": ["Ragging complaint", "Unsafe hostel conditions", "Harassment by staff alleged"],
    "Scholarship": ["Scholarship amount not credited", "PMSS scholarship verification pending", "Freeship denied despite eligibility"],
    "Admission": ["Admission beyond approved intake", "Programme run without approval", "Lateral entry admissions irregular"],
    "Placement": ["Misleading placement statistics", "Placement fee charged"],
}
HOME = {  # each institution's main bureau for background OPEN cases (keeps overlap view meaningful)
    "acem": "AB", "gyiet": "ACAD", "siet": "FIN", "kce": "ACAD", "kit": "PGRC", "cpc": "AB", "svcet": "PGRC",
    "dipr": "AB", "bie": "ACAD", "hitm": "PGRC", "mec": "RB", "sce": "FIN",
    "aiet": "PGRC", "git": "RB", "nvec": "ACAD", "simt": "AB", "miet": "RB", "cits": "RB",
}
OFFICERS = {"RB": ["officer1", "officer7"], "PGRC": ["officer2", "officer6"], "AB": ["officer3"],
            "ACAD": ["officer4"], "FIN": ["officer5"]}


def seed_background(db: Session, b: dict, u: dict, i: dict, n: int = 96) -> int:
    S = CaseStatus
    keys = list(i.keys())
    created = 0
    used = set()
    for k in range(n):
        key = RNG.choice(keys)
        inst = i[key]
        received = RNG.uniform(20, 420)
        open_case = received < 120 and RNG.random() < 0.55
        if open_case:
            bcode = HOME[key]
            cats = [c for c, bs in CATEGORY_BUREAU.items() if bcode in bs]
        else:
            cat_any = RNG.choice(list(CATEGORY_BUREAU))
            bcode = RNG.choice(CATEGORY_BUREAU[cat_any])
            cats = [cat_any]
        cat = RNG.choice(cats)
        options = [t for t in TITLES[cat] if (key, t) not in used] or TITLES[cat]
        title = RNG.choice(options)
        used.add((key, title))
        off = u[RNG.choice(OFFICERS[bcode])]
        due_in = RNG.choice([30, 30, 45, 60])
        if open_case:
            st = RNG.choice([S.RECEIVED, S.TRIAGED, S.ASSIGNED, S.UNDER_PROCESS, S.UNDER_PROCESS,
                             S.AWAITING_INFORMATION, S.DECISION_REVIEW, S.ESCALATED])
            disposed_after = None
            acts = [(RNG.uniform(1, 5), "status_change", "Taken up for examination", S.UNDER_PROCESS)] \
                if st not in (S.RECEIVED, S.TRIAGED, S.ASSIGNED) else []
            if st == S.ESCALATED:
                acts.append((RNG.uniform(10, 30), "status_change", "Escalated: institution non-responsive", S.ESCALATED))
        else:
            st = RNG.choice([S.DISPOSED, S.DISPOSED, S.DISPOSED, S.CLOSED, S.TRANSFERRED])
            disposed_after = RNG.uniform(8, due_in * 1.6) if st in (S.DISPOSED, S.CLOSED) else None
            acts = [(RNG.uniform(1, 4), "letter_issued", "Letter issued to institution for action taken report", None)]
            if disposed_after:
                acts.append((disposed_after, "status_change",
                             RNG.choice(["Disposed: grievance redressed by institution",
                                         "Disposed: action taken report accepted",
                                         "Disposed: no merit after examination"]), S.DISPOSED))
            elif st == S.TRANSFERRED:
                acts.append((RNG.uniform(3, 10), "transfer_accepted", "Transfer accepted by receiving bureau", S.TRANSFERRED))
        make_case(
            db, inst=inst, bureau=b[bcode], officer=off, received=received, due_in=due_in,
            disposed_after=disposed_after, source=f"{bcode}/{NOW.year if received < 300 else NOW.year - 1}/{1000 + k}",
            title=f"{title}", category=cat, status=st,
            priority=RNG.choice(["low", "medium", "medium", "high", "urgent"]),
            summary=f"{title} — {inst.canonical_name}, {inst.city}. {DEMO_NOTE}",
            actions=acts, next_action=None if not open_case else "Await institution's response",
        )
        created += 1
    db.commit()
    print(f"✓ Background cases: {created} (14-month history for analytics)")
    return created


# ─── Relationships, coordination, rules ───────────────────────────────────────

def seed_relationships(db: Session, scenario_cases: list) -> None:
    """Persist pairwise overlap candidates for the human review inbox."""
    from sqlalchemy.orm import joinedload
    from app.services.intelligence import case_to_facts
    from app.services.overlap import classify_pair
    mapping = {"duplicate": RelationshipType.POSSIBLE_DUPLICATE, "action_conflict": RelationshipType.ACTION_CONFLICT,
               "related_pattern": RelationshipType.RELATED_COMPLAINT,
               "independent": RelationshipType.SAME_INSTITUTION_UNRELATED}
    ids = [c.id for c in scenario_cases]
    rows = db.query(Case).options(joinedload(Case.bureau), joinedload(Case.actions)).filter(Case.id.in_(ids)).all()
    by_inst = {}
    for c in rows:
        by_inst.setdefault(c.institution_id, []).append(c)
    created = 0
    for items in by_inst.values():
        for x in range(len(items)):
            for y in range(x + 1, len(items)):
                a, bb = items[x], items[y]
                if a.bureau_id == bb.bureau_id:
                    continue
                res = classify_pair(case_to_facts(a), case_to_facts(bb))
                score = {"duplicate": 0.91, "action_conflict": 0.86, "related_pattern": 0.68, "independent": 0.32}[res["classification"]]
                db.add(CaseRelationship(
                    case_a_id=a.id, case_b_id=bb.id, relationship_type=mapping[res["classification"]],
                    score=score, reasons=res["reasons"] + [r["title"] for r in res["rules"]],
                    matching_evidence={"classification": res["classification"], "severity": res["severity"],
                                       "rules": res["rules"], "shared_issues": res["shared_issues"],
                                       "text_similarity": res["text_similarity"], "cross_bureau": True},
                    algorithm_version="OCI-1.0", review_status=ReviewStatus.PENDING,
                    created_at=max(a.received_date, bb.received_date) + timedelta(hours=1)))
                created += 1
    db.commit()
    print(f"✓ Relationship candidates: {created}")


def seed_coordination(db: Session, b: dict, u: dict, i: dict) -> None:
    existing = db.query(CoordinationItem).count()
    if existing:
        print("• Coordination items already present — skipped")
        return
    reviewer, admin = u["reviewer"], u["admin"]
    # Running One-Voice coordination for the systemic-fee institution
    item = CoordinationItem(
        reference_number=f"CCP-{NOW.year}-0001",
        title="One-Voice Coordination — CITS",
        description="Potential Overlapping Cases – Coordination Required\n\nFour fee-related complaints across PGRC, FIN and RB within six months.",
        owner_id=reviewer.id, status=CoordinationStatus.FOLLOW_UP, decision=CoordinationDecision.COORDINATE,
        decision_rationale="RB holds regulatory action; issue concerns fee norms (regulatory mandate)",
        decision_by_id=reviewer.id, decision_at=days_ago(30), acknowledge_by=days_ago(27),
        action_due_date=NOW + timedelta(days=6), created_by_id=reviewer.id,
        institution_id=i["cits"].id, lead_bureau_id=b["RB"].id, created_at=days_ago(30),
    )
    db.add(item)
    db.flush()
    for code, role, ack in (("RB", "lead", True), ("PGRC", "supporting", True), ("FIN", "supporting", False)):
        db.add(CoordinationParticipant(coordination_item_id=item.id, bureau_id=b[code].id, role_in_coordination=role,
                                       acknowledged=ack, acknowledged_at=days_ago(28) if ack else None))
    for title, due, done in (("RB: consolidate position of all bureaus", -20, True),
                             ("Supporting bureaus: share file notes with the lead bureau", -25, True),
                             ("RB: issue one consolidated communication to the institution", 4, False),
                             ("All bureaus: close source files with cross-reference", 12, False)):
        db.add(CoordinationTask(coordination_item_id=item.id, title=title, due_date=NOW + timedelta(days=due),
                                is_completed=done, completed_at=NOW + timedelta(days=due - 1) if done else None,
                                completed_by_id=u["officer7"].id if done else None, created_by_id=reviewer.id))
    # A closed historical coordination
    closed = CoordinationItem(
        reference_number=f"CCP-{NOW.year}-0002", title="Admission beyond intake — joint review (closed)",
        description="AB and RB jointly reviewed admissions beyond approved intake.", owner_id=admin.id,
        status=CoordinationStatus.CLOSED, decision=CoordinationDecision.COORDINATE,
        acknowledge_by=days_ago(150), action_due_date=days_ago(120), closed_by_id=reviewer.id,
        closed_at=days_ago(118), closure_notes="RB issued consolidated direction; AB recorded compliance. Files closed with cross-reference.",
        created_by_id=admin.id, institution_id=i["mec"].id, lead_bureau_id=b["RB"].id, created_at=days_ago(160),
    )
    db.add(closed)
    db.commit()
    print("✓ Coordination items: 2")


def seed_deadline_rules(db: Session) -> None:
    rules = [
        {"name": "Grievance disposal (PGRC)", "applies_to": "bureau", "applies_to_value": "PGRC", "days_to_resolve": 30, "escalation_after_days": 21},
        {"name": "Regulatory matter (RB)", "applies_to": "bureau", "applies_to_value": "RB", "days_to_resolve": 60, "escalation_after_days": 45},
        {"name": "Urgent priority", "applies_to": "priority", "applies_to_value": "urgent", "days_to_resolve": 15, "escalation_after_days": 10},
        {"name": "Coordination acknowledgement", "applies_to": "coordination", "days_to_resolve": 3, "escalation_after_days": 2},
    ]
    for r in rules:
        if not db.query(DeadlineRule).filter(DeadlineRule.name == r["name"]).first():
            db.add(DeadlineRule(**r))
    db.commit()
    print("✓ Timeline rules (configurable demo values — not official AICTE policy)")


def main() -> None:
    reset = "--reset" in sys.argv
    print("\n" + "=" * 64)
    print("NYAYA SETU — Demo Seed (SIH PS 26264)")
    print("⚠  ALL DATA IS SYNTHETIC — NOT OFFICIAL AICTE RECORDS")
    print("=" * 64 + "\n")
    if reset:
        print("Dropping all tables…")
        Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        bureaus = seed_bureaus(db)
        users = seed_users(db, bureaus)
        insts = seed_institutions(db, users["admin"])
        if db.query(Case).count() == 0:
            scenario = seed_scenarios(db, bureaus, users, insts)
            seed_background(db, bureaus, users, insts)
            seed_relationships(db, scenario)
        else:
            print("• Cases already present — skipped (use --reset to rebuild)")
        seed_coordination(db, bureaus, users, insts)
        seed_deadline_rules(db)
        from app.services.intelligence import run_alert_scan
        res = run_alert_scan(db)
        print(f"✓ Alerts generated: {res['total']} {res['created']}")
        print("\n✅ Seed complete.  Open http://localhost:5173\n")
        print("Demo accounts:")
        for email, name, role, bcode, desig, _, pwd in USERS:
            print(f"  {email:<24} {pwd:<13} {desig}")
        print("\n⚠  DEMO CREDENTIALS — change before any real deployment\n")
    except Exception as exc:
        import traceback
        traceback.print_exc()
        db.rollback()
        print(f"\n❌ Seed failed: {exc}")
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
