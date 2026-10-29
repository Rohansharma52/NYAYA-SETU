"""Unit tests for Overlap & Conflict Intelligence rules (pure python, no DB)."""
from datetime import datetime, timedelta, timezone

from app.services.overlap import CaseFacts, analyze_institution, classify_pair, risk_profile

NOW = datetime.now(timezone.utc)


def _case(i, code, bid, **kw):
    base = dict(id=i, case_number=f"C-{i}", bureau_id=bid, bureau_code=code, bureau_name=code,
                category="Fee Refund", title="Excess fee charged", summary="", status="under_process",
                received_date=NOW - timedelta(days=10))
    base.update(kw)
    return CaseFacts(**base)


def test_closure_vs_enforcement_is_critical_conflict():
    pgrc = _case(1, "PGRC", 2, status="disposed", actions=["Disposed: institution assured refund"])
    rb = _case(2, "RB", 1, category="Fee Regulation", status="escalated",
               actions=["Penal action proposed: withdrawal of approval"])
    res = classify_pair(pgrc, rb)
    assert res["classification"] == "action_conflict"
    assert res["severity"] == "critical"
    assert res["rules"][0]["code"] == "C1"


def test_parallel_directions_detected():
    a = _case(1, "PGRC", 2, actions=["Letter issued to institution seeking reply"])
    b = _case(2, "RB", 1, category="Fee Regulation", actions=["Show-cause notice issued"])
    res = classify_pair(a, b)
    assert any(r["code"] == "C2" for r in res["rules"])


def test_same_complainant_duplicate():
    a = _case(1, "PGRC", 2, complainant_name="Rohit Kumar", title="Refund of excess fee not given")
    b = _case(2, "FIN", 5, complainant_name="Rohit  kumar", title="Excess fee refund pending")
    assert classify_pair(a, b)["classification"] == "duplicate"


def test_independent_issues():
    a = _case(1, "PGRC", 2, category="Student Welfare", title="Hostel mess food quality")
    b = _case(2, "ACAD", 4, category="Examination", title="Result declaration delayed")
    res = classify_pair(a, b)
    assert res["classification"] == "independent"
    assert res["severity"] == "low"


def test_lead_bureau_prefers_regulatory_action():
    a = _case(1, "PGRC", 2, actions=["Letter issued to institution"])
    b = _case(2, "RB", 1, category="Fee Regulation", actions=["Show-cause notice issued"])
    out = analyze_institution([a, b])
    assert out["banner"] == "Potential Overlapping Cases – Coordination Required"
    assert out["lead_bureau"]["bureau_code"] == "RB"


def test_risk_profile_flags_systemic_issue():
    cases = [_case(i, "PGRC", 2, received_date=NOW - timedelta(days=20 * i)) for i in range(1, 5)]
    risk = risk_profile(cases)
    assert risk["systemic_issues"] and risk["systemic_issues"][0]["issue"] == "fees"
    assert risk["score"] > 30
