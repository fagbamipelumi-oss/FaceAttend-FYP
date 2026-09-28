def test_login_with_wrong_password_fails(client, admin_token):
    r = client.post("/auth/login", data={"username": "admin", "password": "wrong-password"})
    assert r.status_code == 401


def test_login_with_correct_password_succeeds(admin_token):
    assert admin_token  # fixture already asserts 200 and returns the token


def test_protected_endpoint_rejects_missing_token(client):
    r = client.get("/people")
    assert r.status_code == 401


def test_protected_endpoint_rejects_bad_token(client):
    r = client.get("/people", headers={"Authorization": "Bearer not-a-real-token"})
    assert r.status_code == 401


def test_protected_endpoint_accepts_valid_token(client, auth_headers):
    r = client.get("/people", headers=auth_headers)
    assert r.status_code == 200
    assert r.json() == []


def test_kiosk_burst_endpoint_does_not_require_auth(client, auth_headers):
    # kiosk endpoint: create a session as admin, then confirm the kiosk
    # burst endpoint works without any Authorization header at all.
    r = client.post(
        "/sessions",
        json={"name": "Open Kiosk Session", "session_date": "2026-09-25"},
        headers=auth_headers,
    )
    session_id = r.json()["id"]

    from app.tests.conftest import photo_bytes

    frame = ("obama.jpg", photo_bytes("obama.jpg"), "image/jpeg")
    r = client.post(
        "/recognize/kiosk-burst",
        data={"session_id": session_id},
        files=[("frames", frame) for _ in range(6)],
    )
    assert r.status_code == 200


def test_group_scan_endpoint_requires_auth(client, auth_headers):
    r = client.post(
        "/sessions",
        json={"name": "Group Scan Auth Session", "session_date": "2026-09-25"},
        headers=auth_headers,
    )
    session_id = r.json()["id"]

    from app.tests.conftest import photo_bytes

    r = client.post(
        "/recognize/group-scan",
        data={"session_id": session_id},
        files={"file": ("obama.jpg", photo_bytes("obama.jpg"), "image/jpeg")},
    )
    assert r.status_code == 401
