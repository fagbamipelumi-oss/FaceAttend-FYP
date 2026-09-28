from fastapi import APIRouter, Depends, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin
from app.api.schemas import KioskBurstResponse, LivenessStepResponse, RecognizeFaceResult, RecognizeResponse
from app.core.config import get_settings
from app.core.database import get_db
from app.models.attendance import AttendanceSource
from app.models.session import AttendanceSession
from app.services.attendance_service import mark_attendance
from app.services.enrollment_service import load_image_from_bytes
from app.services.face_service import detect_face_locations, encode_all_faces, encode_face_at_location, largest_face
from app.services.liveness_check import VALID_CHALLENGES, evaluate_challenge
from app.services.matching_service import find_best_match

router = APIRouter(prefix="/recognize", tags=["recognition"])


@router.post("/group-scan", response_model=RecognizeResponse, dependencies=[Depends(get_current_admin)])
def recognize_group_scan(
    session_id: int = Form(...),
    file: UploadFile = None,
    db: Session = Depends(get_db),
):
    """Admin tool: upload one photo of a group (e.g. a lecture hall), detect
    and match every face in it, and mark attendance for each recognized
    person. Unlike the kiosk, this has no liveness check -- it's meant for
    an admin reviewing a real photo they took, not a public walk-up device.

    Plain def, not async def: this does CPU-bound face detection/encoding
    plus blocking database calls, which would otherwise tie up the whole
    server's single event loop for the entire request. FastAPI runs a
    plain def route in a worker thread automatically, so other requests
    (another kiosk attempt, an admin page load) keep being served while
    this one is busy.
    """
    session = db.get(AttendanceSession, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found.")
    if file is None:
        raise HTTPException(status_code=422, detail="An image file is required.")

    settings = get_settings()
    data = file.file.read()
    image = load_image_from_bytes(data)

    faces = encode_all_faces(image)
    results: list[RecognizeFaceResult] = []

    for location, encoding in faces:
        match = find_best_match(db, encoding, settings.face_match_threshold)

        if match.person is None:
            results.append(
                RecognizeFaceResult(
                    face_location=location,
                    matched=False,
                    distance=match.distance,
                    attendance_status="unrecognized",
                )
            )
            continue

        mark = mark_attendance(db, match.person, session_id, match.distance, AttendanceSource.group_scan)
        results.append(
            RecognizeFaceResult(
                face_location=location,
                matched=True,
                person_id=match.person.id,
                person_name=match.person.full_name,
                distance=match.distance,
                attendance_status="already_marked" if mark.already_marked else "marked",
            )
        )

    return RecognizeResponse(session_id=session_id, faces=results)


@router.post("/liveness-step", response_model=LivenessStepResponse)
def check_liveness_step(
    challenge: str = Form(...),
    frames: list[UploadFile] = None,
):
    """One step of a multi-step challenge sequence (e.g. step 1 of 3:
    'turn left'). Only verifies the challenge was satisfied -- no face
    matching or attendance marking happens here. The caller (frontend)
    advances to the next step on success, or lets the person retry this
    same step on failure.

    Plain def, not async def: real CPU work per frame, must not block the
    server's single event loop.
    """
    if challenge not in VALID_CHALLENGES:
        raise HTTPException(
            status_code=422, detail=f"challenge must be one of {sorted(VALID_CHALLENGES)}"
        )
    if not frames:
        raise HTTPException(status_code=422, detail="A burst of image frames is required.")

    result = evaluate_challenge(frames, challenge, get_settings())
    return LivenessStepResponse(
        passed=result.passed,
        frames_with_face=result.frames_with_face,
        frames_submitted=result.frames_submitted,
        message=result.message,
        challenge_requested=challenge,
    )


@router.post("/kiosk-burst", response_model=KioskBurstResponse)
def recognize_kiosk_burst(
    session_id: int = Form(...),
    challenge: str = Form("blink"),
    frames: list[UploadFile] = None,
    db: Session = Depends(get_db),
):
    """Final step: verify the challenge like /liveness-step, then (if it
    passes) run face matching and mark attendance. This is meaningfully
    harder to spoof with a pre-recorded video than a passive-only check,
    since the video would need to already match whichever instruction is
    picked at capture time, but it is still not a security-grade liveness
    system.

    Plain def, not async def: same reasoning as recognize_group_scan above
    -- this does real CPU work per frame plus a blocking database call,
    and must not tie up the server's single event loop while doing it.
    """
    if challenge not in VALID_CHALLENGES:
        raise HTTPException(
            status_code=422, detail=f"challenge must be one of {sorted(VALID_CHALLENGES)}"
        )

    session = db.get(AttendanceSession, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found.")
    if not frames:
        raise HTTPException(status_code=422, detail="A burst of image frames is required.")

    settings = get_settings()
    liveness = evaluate_challenge(frames, challenge, settings)

    if not liveness.passed:
        return KioskBurstResponse(
            session_id=session_id,
            liveness_passed=False,
            frames_with_face=liveness.frames_with_face,
            frames_submitted=liveness.frames_submitted,
            message=liveness.message,
            threshold_used=settings.face_match_threshold,
            challenge_requested=challenge,
        )

    last_image = liveness.last_full_res_image
    # Re-detect on the full-resolution frame for the actual match embedding:
    # the per-frame loop only ever detected on the downscaled copy, and its
    # box coordinates don't map back to full resolution.
    final_location = largest_face(detect_face_locations(last_image))
    if final_location is None:
        return KioskBurstResponse(
            session_id=session_id,
            liveness_passed=True,
            frames_with_face=liveness.frames_with_face,
            frames_submitted=liveness.frames_submitted,
            message="Could not confirm face location for matching. Please try again.",
            threshold_used=settings.face_match_threshold,
            challenge_requested=challenge,
        )

    encoding = encode_face_at_location(last_image, final_location)
    match = find_best_match(db, encoding, settings.face_match_threshold)

    if match.person is None:
        face_result = RecognizeFaceResult(
            face_location=final_location,
            matched=False,
            distance=match.distance,
            attendance_status="unrecognized",
        )
    else:
        mark = mark_attendance(db, match.person, session_id, match.distance, AttendanceSource.kiosk)
        face_result = RecognizeFaceResult(
            face_location=final_location,
            matched=True,
            person_id=match.person.id,
            person_name=match.person.full_name,
            distance=match.distance,
            attendance_status="already_marked" if mark.already_marked else "marked",
        )

    return KioskBurstResponse(
        session_id=session_id,
        liveness_passed=True,
        frames_with_face=liveness.frames_with_face,
        frames_submitted=liveness.frames_submitted,
        face=face_result,
        threshold_used=settings.face_match_threshold,
        challenge_requested=challenge,
    )
