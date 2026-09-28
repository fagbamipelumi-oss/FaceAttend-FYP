import enum
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, Float, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class AttendanceSource(str, enum.Enum):
    kiosk = "kiosk"
    group_scan = "group_scan"


class AttendanceRecord(Base):
    __tablename__ = "attendance_records"
    __table_args__ = (
        # A person can only be marked present once per session — enforced
        # at the database level, not just in application logic.
        UniqueConstraint("person_id", "session_id", name="uq_attendance_person_session"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    person_id: Mapped[int] = mapped_column(ForeignKey("people.id"))
    session_id: Mapped[int] = mapped_column(ForeignKey("sessions.id"))

    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    match_distance: Mapped[float] = mapped_column(Float)
    source: Mapped[AttendanceSource] = mapped_column(Enum(AttendanceSource))

    person: Mapped["Person"] = relationship(back_populates="attendance_records")  # noqa: F821
    session: Mapped["AttendanceSession"] = relationship(back_populates="attendance_records")  # noqa: F821
