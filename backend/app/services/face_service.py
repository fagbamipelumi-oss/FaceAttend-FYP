"""Low-level face detection and embedding wrapper around face_recognition/dlib."""

import cv2
import face_recognition
import numpy as np


class NoFaceFoundError(Exception):
    pass


class MultipleFacesFoundError(Exception):
    def __init__(self, count: int):
        self.count = count
        super().__init__(f"expected exactly one face, found {count}")


def detect_face_locations(image: np.ndarray) -> list[tuple[int, int, int, int]]:
    """Return (top, right, bottom, left) boxes for every face found."""
    return face_recognition.face_locations(image)


def encode_single_face(image: np.ndarray) -> np.ndarray:
    """Encode an image expected to contain exactly one face.

    Raises NoFaceFoundError / MultipleFacesFoundError otherwise, so callers
    (enrollment) can reject bad photos with a clear reason instead of
    silently encoding the wrong face.
    """
    locations = detect_face_locations(image)
    if len(locations) == 0:
        raise NoFaceFoundError()
    if len(locations) > 1:
        raise MultipleFacesFoundError(len(locations))
    encodings = face_recognition.face_encodings(image, known_face_locations=locations)
    return encodings[0]


def encode_face_at_location(image: np.ndarray, location: tuple[int, int, int, int]) -> np.ndarray:
    return face_recognition.face_encodings(image, known_face_locations=[location])[0]


def encode_all_faces(image: np.ndarray) -> list[tuple[tuple[int, int, int, int], np.ndarray]]:
    """Encode every face found in an image. Used for group-scan recognition."""
    locations = detect_face_locations(image)
    encodings = face_recognition.face_encodings(image, known_face_locations=locations)
    return list(zip(locations, encodings))


def euclidean_distance(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.linalg.norm(np.asarray(a) - np.asarray(b)))


def downscale_for_detection(image: np.ndarray, max_dimension: int = 800) -> np.ndarray:
    """Shrink an image so its longer side is at most max_dimension.

    Face detection cost scales with image size, and repeated detection
    across a multi-frame liveness burst is the main per-request cost at
    scale. EAR (used for blink detection) is a ratio of distances within
    the same image, so it is scale-invariant; only detection speed
    changes, not the liveness math. No-op if already small enough.
    """
    height, width = image.shape[:2]
    longest_side = max(height, width)
    if longest_side <= max_dimension:
        return image
    scale = max_dimension / longest_side
    return cv2.resize(
        image, (round(width * scale), round(height * scale)), interpolation=cv2.INTER_AREA
    )


def largest_face(locations: list[tuple[int, int, int, int]]) -> tuple[int, int, int, int] | None:
    """Pick the largest detected face box (top, right, bottom, left).

    Used for kiosk capture, where we expect one primary subject in frame
    and want to ignore smaller faces that wander into the background.
    """
    if not locations:
        return None
    return max(locations, key=lambda loc: (loc[2] - loc[0]) * (loc[1] - loc[3]))
