"""Import order matters: every model must be imported here so SQLAlchemy can
resolve the string-based relationship() targets across modules."""

from app.models.person import Person  # noqa: F401
from app.models.embedding import FaceEmbedding  # noqa: F401
from app.models.session import AttendanceSession  # noqa: F401
from app.models.attendance import AttendanceRecord, AttendanceSource  # noqa: F401
from app.models.admin import AdminUser  # noqa: F401
