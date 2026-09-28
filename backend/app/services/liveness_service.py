"""Passive liveness checks using dlib's 68-point facial landmark predictor.

Two independent, passive signals are combined: a detected blink (Eye Aspect
Ratio dip-and-recover) and natural head movement (yaw range across the
burst, via solvePnP head-pose estimation). Either one passing is enough --
most people will do at least one without being told to. A photo or a
screen replay held perfectly still fails both.

Neither signal defeats a sophisticated attack (e.g. a recorded video of a
real person blinking and moving, replayed on a screen) -- that needs an
active, randomized challenge-response check, which this project does not
implement. This is a basic, honest anti-spoofing measure, not a
security-grade liveness system.
"""

from pathlib import Path

import cv2
import dlib
import numpy as np

MODEL_PATH = Path(__file__).resolve().parents[2] / "models" / "shape_predictor_68_face_landmarks.dat"

LEFT_EYE_IDX = list(range(42, 48))
RIGHT_EYE_IDX = list(range(36, 42))

# Standard 6-point 3D face model (arbitrary but self-consistent units) used
# for approximate head-pose estimation via solvePnP. This is the widely
# used generic model from OpenCV's head-pose estimation tutorials, not a
# per-person calibrated model -- fine for detecting *relative* movement
# across a burst, not for a precise absolute angle.
_MODEL_POINTS_3D = np.array(
    [
        (0.0, 0.0, 0.0),  # Nose tip (landmark 30)
        (0.0, -330.0, -65.0),  # Chin (landmark 8)
        (-225.0, 170.0, -135.0),  # Left eye left corner (landmark 36)
        (225.0, 170.0, -135.0),  # Right eye right corner (landmark 45)
        (-150.0, -150.0, -125.0),  # Left mouth corner (landmark 48)
        (150.0, -150.0, -125.0),  # Right mouth corner (landmark 54)
    ]
)
_POSE_LANDMARK_IDX = [30, 8, 36, 45, 48, 54]

_predictor: dlib.shape_predictor | None = None


class LandmarkModelMissingError(Exception):
    pass


def _get_predictor() -> dlib.shape_predictor:
    global _predictor
    if _predictor is None:
        if not MODEL_PATH.exists():
            raise LandmarkModelMissingError(
                f"Facial landmark model not found at {MODEL_PATH}. "
                "Download it from https://dlib.net/files/shape_predictor_68_face_landmarks.dat.bz2"
            )
        _predictor = dlib.shape_predictor(str(MODEL_PATH))
    return _predictor


def get_landmark_points(
    image: np.ndarray, face_location: tuple[int, int, int, int]
) -> list[tuple[int, int]]:
    """face_location is (top, right, bottom, left), as returned by face_recognition."""
    top, right, bottom, left = face_location
    rect = dlib.rectangle(left, top, right, bottom)
    shape = _get_predictor()(image, rect)
    return [(shape.part(i).x, shape.part(i).y) for i in range(68)]


def _eye_aspect_ratio(eye_points: list[tuple[int, int]]) -> float:
    p = np.array(eye_points, dtype=float)
    vertical_1 = np.linalg.norm(p[1] - p[5])
    vertical_2 = np.linalg.norm(p[2] - p[4])
    horizontal = np.linalg.norm(p[0] - p[3])
    return (vertical_1 + vertical_2) / (2.0 * horizontal)


def ear_from_landmarks(points: list[tuple[int, int]]) -> float:
    left_eye = [points[i] for i in LEFT_EYE_IDX]
    right_eye = [points[i] for i in RIGHT_EYE_IDX]
    return (_eye_aspect_ratio(left_eye) + _eye_aspect_ratio(right_eye)) / 2.0


def compute_ear(image: np.ndarray, face_location: tuple[int, int, int, int]) -> float:
    return ear_from_landmarks(get_landmark_points(image, face_location))


def detect_blink(ear_sequence: list[float], threshold: float) -> bool:
    """A blink is an EAR dip below `threshold` that recovers above it before
    the sequence ends. A flat sequence that stays open (no dip) or stays
    "closed" through to the last frame (occlusion, not a blink) is rejected.
    """
    below = [ear < threshold for ear in ear_sequence]
    i = 1
    while i < len(below) - 1:
        if below[i] and not below[i - 1]:
            j = i
            while j < len(below) and below[j]:
                j += 1
            if j < len(below):
                return True
            i = j
        else:
            i += 1
    return False


def yaw_from_landmarks(points: list[tuple[int, int]], image_shape: tuple[int, int]) -> float | None:
    """Approximate head yaw (left-right turn) in degrees via solvePnP.

    Uses an assumed generic camera matrix (no per-device calibration), so
    the absolute angle is not precise. Only the relative change across
    frames from the same camera in the same burst is meant to be
    meaningful, not the absolute value.
    """
    height, width = image_shape[:2]
    image_points = np.array([points[i] for i in _POSE_LANDMARK_IDX], dtype=float)

    focal_length = width
    center = (width / 2, height / 2)
    camera_matrix = np.array(
        [[focal_length, 0, center[0]], [0, focal_length, center[1]], [0, 0, 1]], dtype=float
    )
    dist_coeffs = np.zeros((4, 1))

    ok, rotation_vector, _ = cv2.solvePnP(
        _MODEL_POINTS_3D, image_points, camera_matrix, dist_coeffs, flags=cv2.SOLVEPNP_ITERATIVE
    )
    if not ok:
        return None

    rotation_matrix, _ = cv2.Rodrigues(rotation_vector)
    sy = (rotation_matrix[0, 0] ** 2 + rotation_matrix[1, 0] ** 2) ** 0.5
    yaw = np.degrees(np.arctan2(-rotation_matrix[2, 0], sy))
    return float(yaw)


def detect_head_movement(yaw_sequence: list[float], min_range_degrees: float) -> bool:
    """True if the head's yaw angle varied by at least min_range_degrees
    across the burst -- a proxy for natural movement that a photo or a
    dead-still screen replay would not exhibit.
    """
    valid = [y for y in yaw_sequence if y is not None]
    if len(valid) < 2:
        return False
    return (max(valid) - min(valid)) >= min_range_degrees


# Sign convention for head_turned_direction() below is a best-effort
# mapping derived from the raw (non-mirrored) camera frame's geometry, NOT
# yet confirmed against a real live capture. If a user turning to their
# own left is reported as "right" (or vice versa) during real testing,
# fix it by flipping this one constant -- no other code needs to change.
_YAW_INCREASING_MEANS = "right"


def head_turned_direction(yaw_sequence: list[float], min_range_degrees: float) -> str | None:
    """Return 'left', 'right', or None if movement was too small to call.

    Compares the first and last valid yaw reading in the burst (expected
    to start roughly neutral and end turned, for a challenge-response
    capture) rather than just the overall range, so this also captures
    *which way* the head moved, not just that it moved.
    """
    valid = [y for y in yaw_sequence if y is not None]
    if len(valid) < 2 or (max(valid) - min(valid)) < min_range_degrees:
        return None
    increasing = valid[-1] > valid[0]
    if _YAW_INCREASING_MEANS == "right":
        return "right" if increasing else "left"
    return "left" if increasing else "right"
