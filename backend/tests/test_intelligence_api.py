"""API tests for overlap intelligence, identity resolution, analytics, transfers and attachments."""
import pytest

from app.models.bureau import Bureau


@pytest.fixture
def pgrc(db):
    b = Bureau(code="PGRC", name="Public Grievance Redressal Cell", is_active=True)
    db.add(b)
    db.commit()
    db.refresh(b)
    return b


def _case(client, headers, inst_id, bureau_id, title, category="Fee Refund"):
    r = client.post("/api/v1/cases/", json={"title": title, "category": category,
                                             "institution_id": inst_id, "bureau_id": bureau_id}, headers=headers)
    assert r.status_code == 201, r.text
    return r.json()


def test_cross_bureau_overlap_and_one_voice(client, admin_headers, institution, bureau, pgrc):
    a = _case(client, admin_headers, institution.id, pgrc.id, "Excess fee charged, refund denied")
    b = _case(client, admin_headers, institution.id, bureau.id, "Fee collected beyond approved structure", "Fee Regulation")
    client.post(f"/api/v1/cases/{b['id']}/actions", json={"description": "Show-cause notice issued", "action_type": "show_cause"},
                headers=admin_headers)
    r = client.get("/api/v1/intelligence/overlaps", headers=admin_headers)
    assert r.status_code == 200
    item = next(i for i in r.json()["items"] if i["institution"]["id"] == institution.id)
    assert item["analysis"]["banner"] == "Potential Overlapping Cases – Coordination Required"
    assert item["analysis"]["lead_bureau"]["bureau_code"] == "RB"
    # list response flags the overlap on each case
    lst = client.get("/api/v1/cases/", headers=admin_headers).json()["items"]
    flagged = {c["id"]: c["overlap_bureaus"] for c in lst}
    assert flagged[a["id"]] == ["RB"]
    # open coordination
    r = client.post(f"/api/v1/intelligence/overlaps/{institution.id}/coordinate", json={}, headers=admin_headers)
    assert r.status_code == 201, r.text
    assert r.json()["lead_bureau"] == "RB"
    r2 = client.post(f"/api/v1/intelligence/overlaps/{institution.id}/coordinate", json={}, headers=admin_headers)
    assert r2.status_code == 409


def test_resolve_and_benchmark(client, admin_headers, institution):
    r = client.post("/api/v1/intelligence/resolve", json={"text": "complaint against Test Engg College TEC"},
                    headers=admin_headers)
    assert r.status_code == 200
    assert r.json()["candidates"][0]["institution_id"] == institution.id
    assert client.post("/api/v1/intelligence/resolve", json={"text": ""}, headers=admin_headers).status_code == 422
    bench = client.get("/api/v1/intelligence/benchmark", headers=admin_headers).json()
    assert bench["methods"]["ire"]["f1"] > bench["methods"]["exact"]["f1"]


def test_overview_and_performance(client, admin_headers, institution, bureau):
    _case(client, admin_headers, institution.id, bureau.id, "Labs not functional", "Infrastructure")
    ov = client.get("/api/v1/analytics/overview", headers=admin_headers)
    assert ov.status_code == 200
    body = ov.json()
    assert body["totals"]["received"] >= 1
    assert {"pending", "under_process", "disposed", "transferred", "escalated"} <= set(body["totals"])
    for period in ("monthly", "quarterly"):
        perf = client.get("/api/v1/analytics/performance", params={"period": period}, headers=admin_headers)
        assert perf.status_code == 200
        assert perf.json()["rows"]
    assert client.get("/api/v1/analytics/regions", headers=admin_headers).status_code == 200
    assert client.get("/api/v1/intelligence/risk", headers=admin_headers).status_code == 200
    assert client.get("/api/v1/intelligence/pulse", headers=admin_headers).status_code == 200


def test_transfer_accept_flow(client, admin_headers, institution, bureau, pgrc):
    c = _case(client, admin_headers, institution.id, pgrc.id, "Faculty salary not paid", "Faculty")
    r = client.post(f"/api/v1/cases/{c['id']}/transfer", json={"to_bureau_id": bureau.id, "reason": "RB mandate"},
                    headers=admin_headers)
    assert r.status_code == 201
    pending = client.get("/api/v1/transfers/", headers=admin_headers).json()["items"]
    tid = next(t["id"] for t in pending if t["case_id"] == c["id"])
    r = client.post(f"/api/v1/transfers/{tid}/respond", json={"accept": True, "notes": "Taken over"}, headers=admin_headers)
    assert r.status_code == 200
    assert r.json()["case_status"] == "transferred"
    assert r.json()["bureau_id"] == bureau.id
    hist = client.get(f"/api/v1/cases/{c['id']}/transfers", headers=admin_headers).json()
    assert hist[0]["status"] == "accepted"


def test_reject_transfer_requires_reason(client, admin_headers, institution, bureau, pgrc):
    c = _case(client, admin_headers, institution.id, pgrc.id, "Certificate withheld", "Certificates")
    client.post(f"/api/v1/cases/{c['id']}/transfer", json={"to_bureau_id": bureau.id, "reason": "x"}, headers=admin_headers)
    tid = client.get("/api/v1/transfers/", headers=admin_headers).json()["items"][0]["id"]
    assert client.post(f"/api/v1/transfers/{tid}/respond", json={"accept": False}, headers=admin_headers).status_code == 422


def test_attachment_upload_and_download(client, admin_headers, institution, bureau, tmp_path, monkeypatch):
    import app.api.v1.endpoints.cases as cases_mod
    monkeypatch.setattr(cases_mod, "UPLOAD_DIR", str(tmp_path))
    c = _case(client, admin_headers, institution.id, bureau.id, "Inspection report", "Infrastructure")
    r = client.post(f"/api/v1/cases/{c['id']}/attachments", files={"file": ("report.pdf", b"%PDF-1.4 demo", "application/pdf")},
                    data={"remarks": "Inspection report"}, headers=admin_headers)
    assert r.status_code == 201, r.text
    att = r.json()
    assert len(att["sha256"]) == 64
    lst = client.get(f"/api/v1/cases/{c['id']}/attachments", headers=admin_headers).json()
    assert lst[0]["filename"] == "report.pdf"
    dl = client.get(f"/api/v1/cases/{c['id']}/attachments/{att['id']}/download", headers=admin_headers)
    assert dl.status_code == 200 and dl.content.startswith(b"%PDF")
    bad = client.post(f"/api/v1/cases/{c['id']}/attachments", files={"file": ("x.exe", b"MZ", "application/octet-stream")},
                      headers=admin_headers)
    assert bad.status_code == 415


def test_coordination_detail_and_acknowledge(client, admin_headers, institution, bureau, pgrc):
    _case(client, admin_headers, institution.id, pgrc.id, "Excess fee charged, refund denied")
    _case(client, admin_headers, institution.id, bureau.id, "Fee collected beyond approved structure", "Fee Regulation")
    cid = client.post(f"/api/v1/intelligence/overlaps/{institution.id}/coordinate", json={}, headers=admin_headers).json()["id"]
    r = client.get(f"/api/v1/coordination/{cid}", headers=admin_headers)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["id"] == cid and body["lead_bureau_id"] == bureau.id
    assert len(body["participants"]) == 2 and len(body["tasks"]) == 4
    task_id = body["tasks"][0]["id"]
    assert client.put(f"/api/v1/coordination/{cid}/tasks/{task_id}", json={}, headers=admin_headers).status_code == 200
