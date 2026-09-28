from datetime import date, datetime

from pydantic import BaseModel, ConfigDict

from app.models.attendance import AttendanceSource


class PersonCreate(BaseModel):
    full_name: str
    matric_number: str | None = None
    email: str | None = None
    consent_given: bool


class PersonOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    full_name: str
    matric_number: str | None
    email: str | None
    consent_given: bool
    consent_given_at: datetime | None
    created_at: datetime
    enrolled_photo_count: int = 0


class PhotoEnrollResult(BaseModel):
    filename: str
    accepted: bool
    reason: str | None = None


class EnrollPhotosResponse(BaseModel):
    person_id: int
    results: list[PhotoEnrollResult]
    total_embeddings: int


class SessionCreate(BaseModel):
    name: str
    course: str | None = None
    session_date: date


class SessionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    course: str | None
    session_date: date
    created_at: datetime


class RecognizeFaceResult(BaseModel):
    face_location: tuple[int, int, int, int]
    matched: bool
    person_id: int | None = None
    person_name: str | None = None
    distance: float | None = None
    attendance_status: str  # "marked" | "already_marked" | "unrecognized"


class RecognizeResponse(BaseModel):
    session_id: int
    faces: list[RecognizeFaceResult]


class LivenessStepResponse(BaseModel):
    passed: bool
    frames_with_face: int
    frames_submitted: int
    message: str | None = None
    challenge_requested: str


class KioskBurstResponse(BaseModel):
    session_id: int
    liveness_passed: bool
    frames_with_face: int
    frames_submitted: int
    face: RecognizeFaceResult | None = None
    message: str | None = None
    threshold_used: float
    challenge_requested: str


class AttendanceRecordOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    person_id: int
    person_name: str
    matric_number: str | None
    email: str | None
    session_id: int
    timestamp: datetime
    match_distance: float
    source: AttendanceSource
