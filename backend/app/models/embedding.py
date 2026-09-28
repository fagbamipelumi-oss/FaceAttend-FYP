import json
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class FaceEmbedding(Base):
    __tablename__ = "face_embeddings"

    id: Mapped[int] = mapped_column(primary_key=True)
    person_id: Mapped[int] = mapped_column(ForeignKey("people.id"))

    # 128-d dlib ResNet embedding, stored as a JSON-encoded list of floats.
    # Small dataset size at FYP scale makes a dedicated vector column
    # unnecessary; brute-force distance comparison in Python is fast enough.
    vector_json: Mapped[str] = mapped_column(Text)

    source_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    person: Mapped["Person"] = relationship(back_populates="embeddings")  # noqa: F821

    @property
    def vector(self) -> list[float]:
        return json.loads(self.vector_json)

    @vector.setter
    def vector(self, value: list[float]) -> None:
        self.vector_json = json.dumps(list(value))
