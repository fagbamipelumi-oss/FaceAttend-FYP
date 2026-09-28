from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import get_current_admin
from app.api.schemas import AttendanceRecordOut
from app.core.database import get_db
from app.models.attendance import AttendanceRecord

router = APIRouter(prefix="/attendance", tags=["attendance"], dependencies=[Depends(get_current_admin)])


@router.get("", response_model=list[AttendanceRecordOut])
def list_attendance(session_id: int | None = None, db: Session = Depends(get_db)):
    # selectinload(.person): same fix as find_best_match's N+1 bug -- fetch
    # every record's person in one batched query instead of one extra
    # round trip to Neon per distinct person.
    query = select(AttendanceRecord).options(selectinload(AttendanceRecord.person))
    if session_id is not None:
        query = query.where(AttendanceRecord.session_id == session_id)
    records = db.execute(query).scalars().all()
    return [
        AttendanceRecordOut(
            id=r.id,
            person_id=r.person_id,
            person_name=r.person.full_name,
            matric_number=r.person.matric_number,
            email=r.person.email,
            session_id=r.session_id,
            timestamp=r.timestamp,
            match_distance=r.match_distance,
            source=r.source,
        )
        for r in records
    ]
