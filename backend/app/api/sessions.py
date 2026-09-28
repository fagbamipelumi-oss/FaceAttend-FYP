from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin
from app.api.schemas import SessionCreate, SessionOut
from app.core.database import get_db
from app.models.session import AttendanceSession

router = APIRouter(prefix="/sessions", tags=["sessions"], dependencies=[Depends(get_current_admin)])


@router.post("", response_model=SessionOut, status_code=201)
def create_session(payload: SessionCreate, db: Session = Depends(get_db)):
    session = AttendanceSession(
        name=payload.name, course=payload.course, session_date=payload.session_date
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


@router.get("", response_model=list[SessionOut])
def list_sessions(db: Session = Depends(get_db)):
    return db.execute(select(AttendanceSession)).scalars().all()
