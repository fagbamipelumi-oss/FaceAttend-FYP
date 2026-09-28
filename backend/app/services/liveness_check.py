"""Shared orchestration for verifying one challenge (blink / left / right)
against a burst of uploaded frames. Used both by the liveness-only step
endpoint (intermediate steps of a multi-step sequence) and by the final
kiosk-burst endpoint (which also does face matching after this passes).
"""

from dataclasses import dataclass

import numpy as np
from fastapi import UploadFile

from app.core.config import Settings
from app.services.enrollment_service import load_image_from_bytes
from app.services.face_service import detect_face_locations, downscale_for_detection, largest_face
from app.services.liveness_service import detect_blink, ear_from_landmarks, get_landmark_points, head_turned_direction, yaw_from_landmarks

VALID_CHALLENGES = {"blink", "left", "right"}


@dataclass
class LivenessCheckResult:
    passed: bool
    frames_with_face: int
    frames_submitted: int
    message: str | None
    # Full-resolution image of the last frame that had a detected face,
    # for the caller to run face matching against -- only meaningful when
    # passed is True. None otherwise.
    last_full_res_image: np.ndarray | None


def evaluate_challenge(frames: list[UploadFile], challenge: str, settings: Settings) -> LivenessCheckResult:
    ear_sequence: list[float] = []
    yaw_sequence: list[float] = []
    last_image = None

    for f in frames:
        data = f.file.read()
        image = load_image_from_bytes(data)
        # Downscaled purely for detection speed across this repeated,
        # per-frame loop; EAR and yaw are both scale-invariant, so this
        # doesn't change the liveness result, only how fast it's computed.
        small_image = downscale_for_detection(image, settings.liveness_detection_max_dimension)
        location = largest_face(detect_face_locations(small_image))
        if location is None:
            continue
        # One predictor call per frame, shared by both signals.
        points = get_landmark_points(small_image, location)
        ear_sequence.append(ear_from_landmarks(points))
        yaw = yaw_from_landmarks(points, small_image.shape)
        if yaw is not None:
            yaw_sequence.append(yaw)
        last_image = image  # keep full resolution for the final match embedding

    if len(ear_sequence) < settings.liveness_min_valid_frames:
        return LivenessCheckResult(
            passed=False,
            frames_with_face=len(ear_sequence),
            frames_submitted=len(frames),
            message="Could not detect a face clearly enough across the capture burst.",
            last_full_res_image=None,
        )

    if challenge == "blink":
        satisfied = detect_blink(ear_sequence, settings.ear_blink_threshold)
        failure_message = "You were asked to blink, but no blink was detected. Please try again."
    else:
        actual_direction = head_turned_direction(yaw_sequence, settings.head_yaw_min_range_degrees)
        satisfied = actual_direction == challenge
        failure_message = f"You were asked to turn your head {challenge}. Please try again."

    if not satisfied:
        return LivenessCheckResult(
            passed=False,
            frames_with_face=len(ear_sequence),
            frames_submitted=len(frames),
            message=failure_message,
            last_full_res_image=None,
        )

    return LivenessCheckResult(
        passed=True,
        frames_with_face=len(ear_sequence),
        frames_submitted=len(frames),
        message=None,
        last_full_res_image=last_image,
    )
