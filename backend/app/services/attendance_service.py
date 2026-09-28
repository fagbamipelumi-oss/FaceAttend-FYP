"""Attendance logging: mark present exactly once per person per session."""

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.attendance import AttendanceRecord, AttendanceSource
from app.models.person import Person


@dataclass
class MarkResult:
    record: AttendanceRecord
    already_marked: bool


def mark_attendance(
    db: Session,
    person: Person,
    session_id: int,
    distance: float,
    source: AttendanceSource,
) -> MarkResult:
    existing = db.execute(
        select(AttendanceRecord).where(
            AttendanceRecord.person_id == person.id,
            AttendanceRecord.session_id == session_id,
        )
    ).scalar_one_or_none()

    if existing is not None:
        return MarkResult(record=existing, already_marked=True)

    record = AttendanceRecord(
        person_id=person.id,
        session_id=session_id,
        match_distance=distance,
        source=source,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return MarkResult(record=record, already_marked=False)
