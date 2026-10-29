"""Focused analytics and SLA contract tests."""


def test_sla_status_requires_auth(client):
    response = client.get("/api/v1/analytics/sla-status")
    assert response.status_code in (401, 403)


def test_sla_status_has_unknown_deadline_bucket(client, admin_headers, institution):
    response = client.get("/api/v1/analytics/sla-status", headers=admin_headers)
    assert response.status_code == 200
    body = response.json()
    assert {
        "overdue_count",
        "approaching_deadline_count",
        "on_track",
        "at_risk",
        "no_deadline_set",
        "total_active",
        "compliance_percentage",
    }.issubset(body)


def test_dashboard_bureau_breakdown_is_reconcilable(client, admin_headers, institution):
    response = client.get("/api/v1/analytics/dashboard", headers=admin_headers)
    assert response.status_code == 200
    body = response.json()
    assert isinstance(body["cases_by_bureau"], list)
    assert all({"bureau_name", "count"}.issubset(item) for item in body["cases_by_bureau"])
