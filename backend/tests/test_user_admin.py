"""Account lifecycle: sign-up → bureau assignment → approval → suspend → reactivate."""


def _signup(client, email="new.officer@aicte.demo"):
    r = client.post("/api/v1/auth/signup", json={
        "full_name": "New Officer", "email": email, "password": "Strong@12345", "designation": "Section Officer"})
    assert r.status_code in (200, 201), r.text
    return r.json()["user_id"]


def test_approval_requires_bureau_then_lifecycle(client, admin_headers, bureau):
    uid = _signup(client)
    r = client.post(f"/api/v1/users/{uid}/approve", headers=admin_headers)
    assert r.status_code == 422  # bureau officer without a Bureau/Cell
    assert client.put(f"/api/v1/users/{uid}", json={"bureau_id": bureau.id}, headers=admin_headers).status_code == 200
    r = client.post(f"/api/v1/users/{uid}/approve", headers=admin_headers)
    assert r.status_code == 200 and r.json()["account_status"] == "active"
    assert client.post(f"/api/v1/users/{uid}/suspend", headers=admin_headers).json()["account_status"] == "suspended"
    r = client.post(f"/api/v1/users/{uid}/reactivate", headers=admin_headers)
    assert r.status_code == 200 and r.json()["account_status"] == "active"
    assert client.post(f"/api/v1/users/{uid}/reactivate", headers=admin_headers).status_code == 400


def test_reactivate_is_admin_only(client, officer_headers, admin_headers, bureau):
    uid = _signup(client, "other.officer@aicte.demo")
    assert client.post(f"/api/v1/users/{uid}/reactivate", headers=officer_headers).status_code == 403
