"""
Overlap & Conflict Intelligence — NYAYA SETU
============================================

PS 26264 asks the system to detect "overlapping actions, duplication of
efforts" between RB, PGRC and other Bureaus/Cells. Saying "these two cases are
about the same institution" is only the first step. This module goes further:

  1. Classify every cross-bureau pair:
       DUPLICATE        same complaint filed in two places
       ACTION_CONFLICT  bureaus are acting in contradictory / parallel ways
       RELATED_PATTERN  same issue raised through different channels
       INDEPENDENT      same institution, unrelated issues (still visible)
  2. Fire explicit, auditable conflict rules (no black box).
  3. Propose a Lead Bureau ("One Institution, One Voice") with reasons.
  4. Score institution risk from complaint patterns (Risk Radar).

Pure Python — no database imports — so the rules are unit-testable.
Every output is a SUGGESTION for an authorised officer; nothing is merged,
closed or transferred automatically.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, Iterable, List, Optional, Sequence, Set, Tuple

from app.services.identity import token_set_ratio

RULESET_VERSION = "OCI-1.0"

ISSUE_GROUPS: Dict[str, Sequence[str]] = {
    "fees": ("fee", "fees", "refund", "capitation", "donation", "caution money", "tuition", "charged"),
    "infrastructure": ("infrastructure", "laboratory", "labs", "lab ", "building", "library", "classroom", "equipment"),
    "faculty": ("faculty", "salary", "teacher", "professor", "staff", "qualification", "cadre"),
    "academics": ("exam", "examination", "result", "curriculum", "degree", "marks", "academic", "syllabus"),
    "admission": ("admission", "intake", "seat", "unapproved", "approval", "programme", "course without"),
    "certificates": ("certificate", "migration", "transcript", "original documents", "documents withheld", "marksheet"),
    "student_welfare": ("ragging", "harassment", "hostel", "food", "safety", "discrimination", "mess"),
    "scholarship": ("scholarship", "fellowship", "stipend", "pmss", "freeship"),
    "placement": ("placement", "misleading", "advertisement", "false claim", "fake placement"),
}
ISSUE_LABELS = {
    "fees": "Fees & refunds", "infrastructure": "Infrastructure", "faculty": "Faculty & staff",
    "academics": "Academics & exams", "admission": "Admission & approval", "certificates": "Certificates & documents",
    "student_welfare": "Student welfare", "scholarship": "Scholarship", "placement": "Placement claims",
}
# Issues that are regulatory in nature (norms / approval conditions) → RB leads.
REGULATORY_ISSUES = {"infrastructure", "faculty", "admission", "placement", "fees"}
# Issues that are about redress for an individual → PGRC leads.
INDIVIDUAL_ISSUES = {"certificates", "scholarship", "student_welfare"}

ENFORCEMENT_KEYWORDS = (
    "show cause", "show-cause", "penal action", "withdrawal of approval", "inspection", "expert committee",
    "no admission", "reduction of intake", "penalty", "debar", "enforcement", "suspension of approval",
)
DIRECTIVE_KEYWORDS = (
    "directed", "direction issued", "letter issued", "notice issued", "instructed", "sought compliance",
    "advised the institution", "asked the institution", "letter sent", "communication sent",
)
RESOLVED_KEYWORDS = ("resolved", "satisfied", "settled", "assured", "no merit", "closed as")

CLOSURE_STATUSES = {"disposed", "closed"}
INACTIVE_STATUSES = CLOSURE_STATUSES | {"transferred"}
ENFORCEMENT_STATUSES = {"escalated", "decision_review"}

SEVERITY_ORDER = {"critical": 4, "high": 3, "medium": 2, "low": 1, "none": 0}

_STOP = {
    "the", "a", "an", "of", "and", "to", "in", "for", "on", "at", "by", "with", "from", "is", "are", "was",
    "were", "be", "been", "has", "have", "had", "not", "no", "this", "that", "it", "its", "as", "or",
    "students", "student", "complaint", "regarding", "against", "institute", "college", "institution",
    "engineering", "technology", "university", "demo", "data", "synthetic", "record", "official", "aicte",
    "allege", "alleged", "alleges", "same", "multiple", "received",
}


@dataclass
class CaseFacts:
    id: int
    case_number: str
    bureau_id: Optional[int]
    bureau_code: str
    bureau_name: str
    category: str
    title: str
    summary: str = ""
    status: str = "received"
    received_date: Optional[datetime] = None
    due_date: Optional[datetime] = None
    complainant_name: Optional[str] = None
    complainant_email: Optional[str] = None
    actions: List[str] = field(default_factory=list)  # free-text action descriptions
    officer_name: Optional[str] = None
    institution_name: str = ""  # its tokens are ignored when comparing complaint text

    @property
    def text(self) -> str:
        return f"{self.category} {self.title} {self.summary}"

    @property
    def action_text(self) -> str:
        return " ".join(self.actions).lower()

    @property
    def is_active(self) -> bool:
        return self.status not in INACTIVE_STATUSES


@dataclass
class RuleHit:
    code: str
    title: str
    explanation: str
    severity: str

    def as_dict(self) -> dict:
        return {"code": self.code, "title": self.title, "explanation": self.explanation, "severity": self.severity}


# ─── Helpers ──────────────────────────────────────────────────────────────────

def issue_groups(text: str) -> Set[str]:
    low = f" {text.lower()} "
    return {g for g, kws in ISSUE_GROUPS.items() if any(k in low for k in kws)}


def _content_tokens(text: str, ignore: Optional[Set[str]] = None) -> List[str]:
    toks = re.sub(r"[^a-z0-9\s]", " ", text.lower()).split()
    ignore = ignore or set()
    return [t for t in toks if t not in _STOP and t not in ignore and len(t) > 2 and not t.isdigit()]


def _sort_ratio(a: List[str], b: List[str]) -> float:
    if not a or not b:
        return 0.0
    from difflib import SequenceMatcher
    return SequenceMatcher(None, " ".join(sorted(a)), " ".join(sorted(b))).ratio()


def text_similarity(a: str, b: str, ignore: Optional[Set[str]] = None, title_a: str = "", title_b: str = "") -> float:
    """Strict complaint-text similarity: title word-order-insensitive ratio + content Jaccard.

    Institution-name tokens are ignored, otherwise every complaint about the same
    college would look alike.
    """
    ta, tb = _content_tokens(a, ignore), _content_tokens(b, ignore)
    sa, sb = set(ta), set(tb)
    jacc = len(sa & sb) / len(sa | sb) if sa and sb else 0.0
    if title_a and title_b:
        title = _sort_ratio(_content_tokens(title_a, ignore), _content_tokens(title_b, ignore))
        return 0.6 * title + 0.4 * jacc
    return token_set_ratio(ta, tb) * 0.5 + jacc * 0.5


def _norm(v: Optional[str]) -> str:
    return re.sub(r"[^a-z]", "", (v or "").lower())


def _has(text: str, keywords: Iterable[str]) -> Optional[str]:
    for k in keywords:
        if k in text:
            return k
    return None


def _aware(dt: Optional[datetime]) -> Optional[datetime]:
    if dt is None:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


# ─── Pair classification ──────────────────────────────────────────────────────

def classify_pair(a: CaseFacts, b: CaseFacts) -> dict:
    issues_a, issues_b = issue_groups(a.text), issue_groups(b.text)
    shared = sorted(issues_a & issues_b)
    ignore = set(_content_tokens(f"{a.institution_name} {b.institution_name}"))
    sim = text_similarity(a.text, b.text, ignore, a.title, b.title)
    same_person = bool(
        (_norm(a.complainant_name) and _norm(a.complainant_name) == _norm(b.complainant_name))
        or (a.complainant_email and a.complainant_email.lower() == (b.complainant_email or "").lower())
    )
    reasons: List[str] = []
    if shared:
        reasons.append("Same issue: " + ", ".join(ISSUE_LABELS[s] for s in shared))
    if sim >= 0.45:
        reasons.append(f"Complaint text similarity {sim:.2f}")
    if same_person:
        reasons.append("Same complainant identified in both records")
    cross_bureau = a.bureau_id != b.bureau_id

    rules: List[RuleHit] = []
    same_issue = bool(shared) or sim >= 0.5
    if same_issue:
        for x, y in ((a, b), (b, a)):
            enforcement = _has(y.action_text, ENFORCEMENT_KEYWORDS) or (
                y.status in ENFORCEMENT_STATUSES and y.bureau_code == "RB")
            recent = x.received_date is None or y.received_date is None or abs(
                (_aware(y.received_date) - _aware(x.received_date)).days) <= 180
            if x.status in CLOSURE_STATUSES and y.is_active and enforcement and recent:
                kw = enforcement if isinstance(enforcement, str) else y.status.replace("_", " ")
                rules.append(RuleHit(
                    "C1", "Closure vs. enforcement",
                    f"{x.bureau_code} closed {x.case_number} as disposed while {y.bureau_code} is pursuing "
                    f"'{kw}' on the same issue in {y.case_number}. The institution receives contradictory signals.",
                    "critical"))
                break
        dir_a = _has(a.action_text, DIRECTIVE_KEYWORDS + ENFORCEMENT_KEYWORDS)
        dir_b = _has(b.action_text, DIRECTIVE_KEYWORDS + ENFORCEMENT_KEYWORDS)
        if cross_bureau and a.is_active and b.is_active and dir_a and dir_b:
            rules.append(RuleHit(
                "C2", "Parallel directions to the institution",
                f"Both {a.bureau_code} ('{dir_a}') and {b.bureau_code} ('{dir_b}') have communicated with the "
                f"institution on the same issue. Two letters, two deadlines — risk of conflicting compliance.",
                "high"))
        for x, y in ((a, b), (b, a)):
            if x.status == "transfer_requested" and y.is_active and cross_bureau:
                rules.append(RuleHit(
                    "C3", "Transfer into an existing file",
                    f"{x.case_number} is being transferred while {y.bureau_code} already handles the same issue "
                    f"in {y.case_number}. Link instead of creating parallel handling.",
                    "medium"))
                break
        res_a = _has(a.action_text, RESOLVED_KEYWORDS)
        res_b = _has(b.action_text, RESOLVED_KEYWORDS)
        if cross_bureau and a.status in CLOSURE_STATUSES and b.status in CLOSURE_STATUSES and bool(res_a) != bool(res_b):
            rules.append(RuleHit(
                "C4", "Divergent outcomes",
                "The two bureaus closed the same issue with different outcomes. Reconcile before replying to the complainant.",
                "high"))

    is_duplicate = (same_person and (bool(shared) or sim >= 0.55)) or sim >= 0.82
    has_critical = any(r.severity == "critical" for r in rules)
    if rules and (has_critical or not is_duplicate):
        klass = "action_conflict"
        severity = max((r.severity for r in rules), key=lambda s: SEVERITY_ORDER[s])
        headline = rules[0].title
        if is_duplicate:
            reasons.append("Records also look like the same complaint")
    elif is_duplicate:
        klass = "duplicate"
        headline = "Possible duplicate — same complaint received by two channels"
        severity = "high" if cross_bureau and a.is_active and b.is_active else "medium"
        if rules:
            severity = max([severity] + [r.severity for r in rules], key=lambda s: SEVERITY_ORDER[s])
    elif same_issue:
        klass = "related_pattern"
        headline = "Same issue raised through different channels"
        severity = "medium" if (a.is_active and b.is_active) else "low"
    else:
        klass = "independent"
        headline = "Different issues at the same institution"
        severity = "low"

    if not reasons:
        reasons.append("Same institution, handled by different bureaus" if cross_bureau else "Same institution")

    return {
        "case_a_id": a.id, "case_b_id": b.id,
        "case_a_number": a.case_number, "case_b_number": b.case_number,
        "bureau_a": a.bureau_code, "bureau_b": b.bureau_code,
        "cross_bureau": cross_bureau,
        "classification": klass,
        "headline": headline,
        "severity": severity,
        "text_similarity": round(sim, 3),
        "shared_issues": shared,
        "same_complainant": same_person,
        "reasons": reasons,
        "rules": [r.as_dict() for r in rules],
    }


# ─── Lead bureau ("One Institution, One Voice") ───────────────────────────────

def propose_lead(cases: Sequence[CaseFacts]) -> Optional[dict]:
    active = [c for c in cases if c.is_active and c.bureau_id]
    if not active:
        return None
    scores: Dict[str, float] = {}
    why: Dict[str, List[str]] = {}
    meta: Dict[str, Tuple[Optional[int], str]] = {}
    earliest = min((c for c in active if c.received_date), key=lambda c: _aware(c.received_date), default=None)
    for c in active:
        code = c.bureau_code
        meta[code] = (c.bureau_id, c.bureau_name)
        scores.setdefault(code, 0.0)
        why.setdefault(code, [])
        issues = issue_groups(c.text)
        if _has(c.action_text, ENFORCEMENT_KEYWORDS) or c.status in ENFORCEMENT_STATUSES:
            scores[code] += 3
            why[code].append(f"holds regulatory/enforcement action in {c.case_number}")
        if code == "RB" and issues & REGULATORY_ISSUES:
            scores[code] += 2
            why[code].append("issue concerns norms/approval conditions (regulatory mandate)")
        if code == "PGRC" and issues & INDIVIDUAL_ISSUES and not issues & (REGULATORY_ISSUES - {"fees"}):
            scores[code] += 2
            why[code].append("issue is individual redress (grievance mandate)")
        if earliest is not None and c.id == earliest.id:
            scores[code] += 1
            why[code].append(f"earliest receipt ({c.case_number})")
        scores[code] += 0.1  # presence
    lead = max(scores, key=lambda k: (scores[k], k == "RB"))
    others = [k for k in scores if k != lead]
    reasons = sorted(set(why[lead])) or ["only bureau with an active case"]
    return {
        "bureau_code": lead,
        "bureau_id": meta[lead][0],
        "bureau_name": meta[lead][1],
        "score": round(scores[lead], 2),
        "reasons": reasons,
        "supporting_bureaus": others,
        "protocol": [
            f"{lead} acts as single point of contact with the institution",
            "Other bureaus send inputs to the lead instead of writing to the institution directly",
            "One consolidated communication; one compliance deadline",
            "Each bureau keeps its own source file and closes it with a cross-reference",
        ],
    }


# ─── Institution-level analysis ───────────────────────────────────────────────

def analyze_institution(cases: Sequence[CaseFacts]) -> dict:
    """Analyse all cases of one institution and summarise overlap & conflicts."""
    pairs = []
    for i, a in enumerate(cases):
        for b in cases[i + 1:]:
            if not a.is_active and not b.is_active:
                continue  # historical files only — nothing left to coordinate
            if a.bureau_id == b.bureau_id:
                # Same-bureau pairs only matter if they look like duplicates
                result = classify_pair(a, b)
                if result["classification"] == "duplicate":
                    pairs.append(result)
                continue
            pairs.append(classify_pair(a, b))
    active_bureaus = sorted({c.bureau_code for c in cases if c.is_active and c.bureau_code})
    all_bureaus = sorted({c.bureau_code for c in cases if c.bureau_code})
    severity = max((p["severity"] for p in pairs), key=lambda s: SEVERITY_ORDER[s], default="none")
    if len(active_bureaus) < 2 and severity in ("low", "medium"):
        # Overlap involving closed files only is informational
        severity = "low" if pairs else "none"
    counts: Dict[str, int] = {}
    for p in pairs:
        counts[p["classification"]] = counts.get(p["classification"], 0) + 1
    coordination_required = len(active_bureaus) >= 2 or counts.get("action_conflict", 0) > 0 or (
        counts.get("duplicate", 0) > 0)
    lead = propose_lead(cases) if coordination_required else None
    actions: List[str] = []
    if counts.get("action_conflict"):
        actions.append("Freeze outgoing communication on this issue until the lead bureau consolidates a position")
    if counts.get("duplicate"):
        actions.append("Link duplicate records; reply to the complainant once, quoting both reference numbers")
    if lead:
        actions.append(f"Designate {lead['bureau_code']} as lead bureau and open a coordination item")
    if counts.get("related_pattern"):
        actions.append("Share case notes across bureaus — the same issue is reaching AICTE through multiple channels")
    if not actions and pairs:
        actions.append("Keep all bureaus informed; no coordinated action needed yet")
    return {
        "ruleset": RULESET_VERSION,
        "banner": "Potential Overlapping Cases – Coordination Required" if coordination_required else None,
        "coordination_required": coordination_required,
        "severity": severity,
        "active_bureaus": active_bureaus,
        "bureaus_involved": all_bureaus,
        "classification_counts": counts,
        "pairs": sorted(pairs, key=lambda p: -SEVERITY_ORDER[p["severity"]]),
        "lead_bureau": lead,
        "recommended_actions": actions,
    }


# ─── Risk Radar ───────────────────────────────────────────────────────────────

def risk_profile(cases: Sequence[CaseFacts], now: Optional[datetime] = None, overlap: Optional[dict] = None) -> dict:
    """Explainable 0-100 institution risk score from complaint patterns."""
    now = now or datetime.now(timezone.utc)
    factors: List[dict] = []

    def add(code: str, label: str, points: float, detail: str):
        if points > 0:
            factors.append({"code": code, "label": label, "points": round(points, 1), "detail": detail})

    recent90 = [c for c in cases if c.received_date and (now - _aware(c.received_date)).days <= 90]
    add("velocity", "Complaint velocity", min(len(recent90) * 6, 24),
        f"{len(recent90)} complaints in the last 90 days")

    overdue = [c for c in cases if c.is_active and c.due_date and _aware(c.due_date) < now]
    add("overdue", "Overdue cases", min(len(overdue) * 7, 21), f"{len(overdue)} open cases past timeline")

    bureaus = {c.bureau_code for c in cases if c.is_active}
    add("multi_bureau", "Multi-bureau exposure", 8 if len(bureaus) >= 2 else 0,
        f"Active files in {len(bureaus)} bureaus: {', '.join(sorted(bureaus))}")

    systemic = []
    window = [c for c in cases if c.received_date and (now - _aware(c.received_date)).days <= 180]
    counts: Dict[str, int] = {}
    for c in window:
        for g in issue_groups(c.text):
            counts[g] = counts.get(g, 0) + 1
    for g, n in sorted(counts.items(), key=lambda kv: -kv[1]):
        if n >= 3:
            systemic.append({"issue": g, "label": ISSUE_LABELS[g], "count": n})
    add("systemic", "Systemic issue pattern", min(len(systemic) * 14, 28),
        "; ".join(f"{s['label']}: {s['count']} complaints in 6 months" for s in systemic))

    escalated = [c for c in cases if c.status == "escalated"]
    add("escalation", "Escalations", min(len(escalated) * 6, 12), f"{len(escalated)} escalated cases")

    if overlap and overlap.get("classification_counts", {}).get("action_conflict"):
        add("conflict", "Inter-bureau action conflict", 12, "Contradictory actions detected between bureaus")

    score = min(100.0, sum(f["points"] for f in factors))
    level = "critical" if score >= 70 else "high" if score >= 45 else "elevated" if score >= 20 else "low"
    recs: List[str] = []
    reg = [s for s in systemic if s["issue"] in REGULATORY_ISSUES]
    if reg:
        recs.append(f"Recommend RB inspection / expert committee visit — recurring {reg[0]['label'].lower()} complaints")
    if overdue:
        recs.append("Escalate overdue files to bureau heads")
    if len(bureaus) >= 2:
        recs.append("Maintain a single coordination file for this institution")
    if not recs:
        recs.append("Routine monitoring")
    return {
        "score": round(score, 1),
        "level": level,
        "factors": sorted(factors, key=lambda f: -f["points"]),
        "systemic_issues": systemic,
        "recommendations": recs,
        "complaints_90d": len(recent90),
        "open_cases": sum(1 for c in cases if c.is_active),
        "overdue_cases": len(overdue),
    }
