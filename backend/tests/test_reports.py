"""Exports: case register CSV/PDF, coordination CSV and Institution 360° PDF."""
from datetime import datetime, timedelta, timezone

from app.models.case import Case, CasePriority, CaseStatus


def _case(db, institution, bureau, n, **kw):
    c = Case(case_number=f"AICTE-NS-2026-{n:05d}", institution_id=institution.id, bureau_id=bureau.id,
             title=kw.get("title", "Excess fee of ₹45,000 — B.Tech"), category="Fee Refund",
             status=kw.get("status", CaseStatus.UNDER_PROCESS), priority=CasePriority.HIGH,
             received_date=datetime.now(timezone.utc) - timedelta(days=40),
             due_date=kw.get("due", datetime.now(timezone.utc) - timedelta(days=5)))
    db.add(c)
    db.flush()
    return c


def test_case_csv_is_excel_friendly(client, admin_headers, db, institution, bureau):
    _case(db, institution, bureau, 1)
    r = client.get("/api/v1/reports/cases/csv", headers=admin_headers)
    assert r.status_code == 200
    assert r.content.startswith(b"\xef\xbb\xbf")  # BOM for Excel
    text = r.content.decode("utf-8-sig")
    assert text.splitlines()[0].startswith("Case ID,Source reference,Date of receipt")
    assert "₹45,000" in text and "Under process" in text
    assert 'filename="NYAYA_SETU_Cases_' in r.headers["content-disposition"]


def test_case_csv_overdue_filter(client, admin_headers, db, institution, bureau):
    _case(db, institution, bureau, 1)
    _case(db, institution, bureau, 2, due=datetime.now(timezone.utc) + timedelta(days=10), title="Future")
    text = client.get("/api/v1/reports/cases/csv?overdue=true", headers=admin_headers).content.decode("utf-8-sig")
    assert "AICTE-NS-2026-00001" in text and "AICTE-NS-2026-00002" not in text


def test_case_pdf(client, admin_headers, officer_headers, db, institution, bureau):
    _case(db, institution, bureau, 1)
    for h in (admin_headers, officer_headers):
        r = client.get("/api/v1/reports/cases/pdf?status=under_process,escalated", headers=h)
        assert r.status_code == 200 and r.content[:4] == b"%PDF"


def test_institution_pdf_and_coordination_csv(client, admin_headers, officer_headers, db, institution, bureau):
    _case(db, institution, bureau, 1)
    r = client.get(f"/api/v1/reports/institution/{institution.id}/pdf", headers=admin_headers)
    assert r.status_code == 200 and r.content[:4] == b"%PDF"
    assert client.get("/api/v1/reports/institution/999999/pdf", headers=admin_headers).status_code == 404
    for h in (admin_headers, officer_headers):
        r = client.get("/api/v1/reports/coordination/csv", headers=h)
        assert r.status_code == 200 and r.content.decode("utf-8-sig").startswith("Reference,Title")
