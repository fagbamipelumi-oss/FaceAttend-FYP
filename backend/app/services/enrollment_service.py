"""Enrollment business logic: consent gate, per-photo face validation, embedding storage."""

import io
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from PIL import Image
from sqlalchemy.orm import Session

from app.models.embedding import FaceEmbedding
from app.models.person import Person
from app.services.face_service import (
    MultipleFacesFoundError,
    NoFaceFoundError,
    encode_single_face,
)

# FaceAttend-FYP/data/raw_enrollment -- gitignored, real biometric photos live
# here so evaluation/evaluate.py can run against the actual enrolled dataset
# instead of requiring a separately-collected copy.
RAW_ENROLLMENT_DIR = Path(__file__).resolve().parents[3] / "data" / "raw_enrollment"


class ConsentRequiredError(Exception):
    pass


def load_image_from_bytes(data: bytes) -> np.ndarray:
    image = Image.open(io.BytesIO(data)).convert("RGB")
    return np.array(image)


def _sanitize_folder_name(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9_-]+", "_", name.strip()) or "unnamed"


def save_raw_enrollment_photo(person: Person, filename: str, image_bytes: bytes) -> Path:
    person_dir = RAW_ENROLLMENT_DIR / f"{person.id}_{_sanitize_folder_name(person.full_name)}"
    person_dir.mkdir(parents=True, exist_ok=True)

    suffix = Path(filename).suffix or ".jpg"
    unique_name = f"{uuid.uuid4().hex[:8]}{suffix}"
    dest = person_dir / unique_name
    dest.write_bytes(image_bytes)
    return dest


def create_person(
    db: Session,
    full_name: str,
    consent_given: bool,
    matric_number: str | None = None,
    email: str | None = None,
) -> Person:
    if not consent_given:
        raise ConsentRequiredError("Enrollment requires documented consent before any photo is captured.")

    person = Person(
        full_name=full_name,
        matric_number=matric_number,
        email=email,
        consent_given=True,
        consent_given_at=datetime.now(timezone.utc),
    )
    db.add(person)
    db.commit()
    db.refresh(person)
    return person


def enroll_photo(db: Session, person: Person, filename: str, image_bytes: bytes) -> tuple[bool, str | None]:
    """Validate and store one enrollment photo.

    Returns (accepted, reason). A photo is rejected (not stored) if it has
    zero or more than one detected face, with the reason surfaced back to
    the enroller so they can retake it.
    """
    if not person.consent_given:
        raise ConsentRequiredError(f"Person {person.id} has not given consent.")

    image = load_image_from_bytes(image_bytes)
    try:
        encoding = encode_single_face(image)
    except NoFaceFoundError:
        return False, "No face detected in photo."
    except MultipleFacesFoundError as exc:
        return False, f"{exc.count} faces detected; enrollment photos must contain exactly one face."

    save_raw_enrollment_photo(person, filename, image_bytes)

    embedding = FaceEmbedding(person_id=person.id, source_filename=filename)
    embedding.vector = encoding.tolist()
    db.add(embedding)
    db.commit()
    return True, None
