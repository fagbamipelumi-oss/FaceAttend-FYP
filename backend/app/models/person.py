from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Person(Base):
    __tablename__ = "people"

    id: Mapped[int] = mapped_column(primary_key=True)
    full_name: Mapped[str] = mapped_column(String(200))
    matric_number: Mapped[str | None] = mapped_column(String(50), unique=True, nullable=True)
    email: Mapped[str | None] = mapped_column(String(200), nullable=True)

    # Enrollment cannot proceed without documented consent for biometric capture.
    consent_given: Mapped[bool] = mapped_column(Boolean, default=False)
    consent_given_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    embeddings: Mapped[list["FaceEmbedding"]] = relationship(
        back_populates="person", cascade="all, delete-orphan"
    )
    attendance_records: Mapped[list["AttendanceRecord"]] = relationship(back_populates="person")
