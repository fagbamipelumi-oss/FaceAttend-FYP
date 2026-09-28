"""Nearest-neighbor matching of a query face embedding against enrolled people."""

from dataclasses import dataclass

import numpy as np
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.embedding import FaceEmbedding
from app.models.person import Person
from app.services.face_service import euclidean_distance


@dataclass
class MatchResult:
    person: Person | None
    distance: float | None


def find_best_match(db: Session, query_embedding: np.ndarray, threshold: float) -> MatchResult:
    """Compare against every enrolled sample embedding (not a centroid) and
    return the closest one. Below `threshold` is a match; otherwise unknown.

    Eagerly loads the .person relationship in the same query (selectinload)
    instead of the SQLAlchemy default of lazy-loading it on first access.
    Without this, accessing row.person triggers one extra network round
    trip to the database per distinct enrolled person -- fine on a local
    database, but a real, measured ~200ms+ penalty per person against a
    remote host like Neon, and one that gets worse as more people enroll.
    """
    rows = db.execute(select(FaceEmbedding).options(selectinload(FaceEmbedding.person))).scalars().all()

    best_distance: float | None = None
    best_person: Person | None = None
    for row in rows:
        distance = euclidean_distance(query_embedding, np.array(row.vector))
        if best_distance is None or distance < best_distance:
            best_distance = distance
            best_person = row.person

    if best_distance is None or best_distance > threshold:
        return MatchResult(person=None, distance=best_distance)
    return MatchResult(person=best_person, distance=best_distance)
