from datetime import date, datetime, timezone

from sqlalchemy import Date, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class AttendanceSession(Base):
    """A single class/lecture instance attendance is taken for."""

    __tablename__ = "sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    course: Mapped[str | None] = mapped_column(String(100), nullable=True)
    session_date: Mapped[date] = mapped_column(Date)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    attendance_records: Mapped[list["AttendanceRecord"]] = relationship(  # noqa: F821
        back_populates="session"
    )
