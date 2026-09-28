import io

from PIL import Image

from app.tests.conftest import photo_bytes


def test_enrollment_requires_consent(client, auth_headers):
    r = client.post(
        "/people",
        json={"full_name": "No Consent Person", "consent_given": False},
        headers=auth_headers,
    )
    assert r.status_code == 400


def test_enrollment_rejects_photo_with_no_face(client, auth_headers):
    r = client.post(
        "/people",
        json={"full_name": "Blank Photo Person", "consent_given": True},
        headers=auth_headers,
    )
    person_id = r.json()["id"]

    blank = Image.new("RGB", (300, 300), color=(120, 120, 120))
    buf = io.BytesIO()
    blank.save(buf, format="JPEG")

    r = client.post(
        f"/people/{person_id}/photos",
        files=[("files", ("blank.jpg", buf.getvalue(), "image/jpeg"))],
        headers=auth_headers,
    )
    body = r.json()
    assert body["total_embeddings"] == 0
    assert body["results"][0]["accepted"] is False
    assert "No face detected" in body["results"][0]["reason"]


def test_accepted_photo_is_saved_to_raw_enrollment_dir(client, auth_headers):
    import app.services.enrollment_service as enrollment_service

    r = client.post(
        "/people",
        json={"full_name": "Raw Save Test", "consent_given": True},
        headers=auth_headers,
    )
    person_id = r.json()["id"]

    r = client.post(
        f"/people/{person_id}/photos",
        files=[("files", ("obama.jpg", photo_bytes("obama.jpg"), "image/jpeg"))],
        headers=auth_headers,
    )
    assert r.json()["results"][0]["accepted"] is True

    person_dirs = list(enrollment_service.RAW_ENROLLMENT_DIR.iterdir())
    assert len(person_dirs) == 1
    saved_files = list(person_dirs[0].iterdir())
    assert len(saved_files) == 1
    assert saved_files[0].read_bytes() == photo_bytes("obama.jpg")


def test_full_enroll_group_scan_duplicate_and_unknown_flow(client, auth_headers):
    # Enroll Obama
    r = client.post(
        "/people",
        json={"full_name": "Barack Obama", "consent_given": True},
        headers=auth_headers,
    )
    assert r.status_code == 201
    person = r.json()

    r = client.post(
        f"/people/{person['id']}/photos",
        files=[("files", ("obama.jpg", photo_bytes("obama.jpg"), "image/jpeg"))],
        headers=auth_headers,
    )
    assert r.status_code == 200
    body = r.json()
    assert body["total_embeddings"] == 1
    assert body["results"][0]["accepted"] is True

    # Create a session
    r = client.post(
        "/sessions",
        json={"name": "CSC401 Lecture", "session_date": "2026-09-25"},
        headers=auth_headers,
    )
    assert r.status_code == 201
    session_id = r.json()["id"]

    # Group-scan is admin-only: no auth header must be rejected
    r = client.post(
        "/recognize/group-scan",
        data={"session_id": session_id},
        files={"file": ("obama.jpg", photo_bytes("obama.jpg"), "image/jpeg")},
    )
    assert r.status_code == 401

    # Recognize the enrolled face -> should match and mark attendance
    r = client.post(
        "/recognize/group-scan",
        data={"session_id": session_id},
        files={"file": ("obama.jpg", photo_bytes("obama.jpg"), "image/jpeg")},
        headers=auth_headers,
    )
    assert r.status_code == 200
    faces = r.json()["faces"]
    assert len(faces) == 1
    assert faces[0]["matched"] is True
    assert faces[0]["person_name"] == "Barack Obama"
    assert faces[0]["attendance_status"] == "marked"

    # Recognize again in the same session -> should not create a duplicate record
    r = client.post(
        "/recognize/group-scan",
        data={"session_id": session_id},
        files={"file": ("obama.jpg", photo_bytes("obama.jpg"), "image/jpeg")},
        headers=auth_headers,
    )
    assert r.json()["faces"][0]["attendance_status"] == "already_marked"

    # An unenrolled person must be rejected, not misclassified as Obama
    r = client.post(
        "/recognize/group-scan",
        data={"session_id": session_id},
        files={"file": ("biden.jpg", photo_bytes("biden.jpg"), "image/jpeg")},
        headers=auth_headers,
    )
    face = r.json()["faces"][0]
    assert face["matched"] is False
    assert face["attendance_status"] == "unrecognized"

    # Attendance listing should show exactly one record, not two
    r = client.get("/attendance", params={"session_id": session_id}, headers=auth_headers)
    records = r.json()
    assert len(records) == 1
    assert records[0]["person_name"] == "Barack Obama"


def test_group_scan_handles_multiple_faces_in_one_photo(client, auth_headers):
    """Build a genuine two-face image (both real detected faces, not a
    mock) by pasting the two smoke-test photos side by side, and confirm
    the group-scan endpoint detects and matches both independently.
    """
    from io import BytesIO

    from PIL import Image

    def scale_to_height(img: Image.Image, target_height: int) -> Image.Image:
        # Preserve aspect ratio -- a distorted stretch can make a real face
        # undetectable, which would falsely look like a detection bug.
        ratio = target_height / img.height
        return img.resize((round(img.width * ratio), target_height))

    target_height = 600
    obama_img = scale_to_height(Image.open(BytesIO(photo_bytes("obama.jpg"))).convert("RGB"), target_height)
    biden_img = scale_to_height(Image.open(BytesIO(photo_bytes("biden.jpg"))).convert("RGB"), target_height)
    combined = Image.new("RGB", (obama_img.width + biden_img.width, target_height))
    combined.paste(obama_img, (0, 0))
    combined.paste(biden_img, (obama_img.width, 0))
    buf = BytesIO()
    combined.save(buf, format="JPEG")
    combined_bytes = buf.getvalue()

    r = client.post(
        "/people", json={"full_name": "Barack Obama", "consent_given": True}, headers=auth_headers
    )
    obama_id = r.json()["id"]
    client.post(
        f"/people/{obama_id}/photos",
        files=[("files", ("obama.jpg", photo_bytes("obama.jpg"), "image/jpeg"))],
        headers=auth_headers,
    )

    r = client.post(
        "/sessions",
        json={"name": "Group Scan Test", "session_date": "2026-09-25"},
        headers=auth_headers,
    )
    session_id = r.json()["id"]

    r = client.post(
        "/recognize/group-scan",
        data={"session_id": session_id},
        files={"file": ("group.jpg", combined_bytes, "image/jpeg")},
        headers=auth_headers,
    )
    assert r.status_code == 200
    faces = r.json()["faces"]
    assert len(faces) == 2

    matched = [f for f in faces if f["matched"]]
    unmatched = [f for f in faces if not f["matched"]]
    assert len(matched) == 1
    assert matched[0]["person_name"] == "Barack Obama"
    assert len(unmatched) == 1


def test_liveness_step_does_not_require_auth_or_session(client):
    frame = ("obama.jpg", photo_bytes("obama.jpg"), "image/jpeg")
    r = client.post(
        "/recognize/liveness-step",
        data={"challenge": "blink"},
        files=[("frames", frame) for _ in range(8)],
    )
    assert r.status_code == 200
    body = r.json()
    assert body["passed"] is False  # static repeat, no real blink
    assert body["challenge_requested"] == "blink"


def test_liveness_step_rejects_invalid_challenge(client):
    frame = ("obama.jpg", photo_bytes("obama.jpg"), "image/jpeg")
    r = client.post(
        "/recognize/liveness-step",
        data={"challenge": "not-a-real-challenge"},
        files=[("frames", frame) for _ in range(8)],
    )
    assert r.status_code == 422


def test_kiosk_burst_rejects_static_photo_replay(client, auth_headers):
    """A static photo submitted repeatedly (simulating a photo-of-a-photo
    spoof, or a still image with no eye movement at all) has a flat EAR
    sequence and must fail the liveness check, not be treated as a live
    capture.
    """
    r = client.post(
        "/sessions",
        json={"name": "Liveness Test Session", "session_date": "2026-09-25"},
        headers=auth_headers,
    )
    session_id = r.json()["id"]

    frame = ("obama.jpg", photo_bytes("obama.jpg"), "image/jpeg")
    files = [("frames", frame) for _ in range(8)]

    r = client.post(
        "/recognize/kiosk-burst",
        data={"session_id": session_id},
        files=files,
    )
    assert r.status_code == 200
    body = r.json()
    assert body["liveness_passed"] is False
    assert body["frames_with_face"] == 8
