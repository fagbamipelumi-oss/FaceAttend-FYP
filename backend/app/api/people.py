from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin
from app.api.schemas import EnrollPhotosResponse, PersonCreate, PersonOut, PhotoEnrollResult
from app.core.database import get_db
from app.models.person import Person
from app.services.enrollment_service import ConsentRequiredError, create_person, enroll_photo

router = APIRouter(prefix="/people", tags=["people"], dependencies=[Depends(get_current_admin)])


def _to_person_out(person: Person) -> PersonOut:
    return PersonOut(
        id=person.id,
        full_name=person.full_name,
        matric_number=person.matric_number,
        email=person.email,
        consent_given=person.consent_given,
        consent_given_at=person.consent_given_at,
        created_at=person.created_at,
        enrolled_photo_count=len(person.embeddings),
    )


@router.post("", response_model=PersonOut, status_code=201)
def register_person(payload: PersonCreate, db: Session = Depends(get_db)):
    try:
        person = create_person(
            db,
            full_name=payload.full_name,
            consent_given=payload.consent_given,
            matric_number=payload.matric_number,
            email=payload.email,
        )
    except ConsentRequiredError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return _to_person_out(person)


@router.post("/{person_id}/photos", response_model=EnrollPhotosResponse)
def upload_enrollment_photos(person_id: int, files: list[UploadFile], db: Session = Depends(get_db)):
    """Plain def, not async def: enroll_photo() below does CPU-bound face
    detection/encoding, which would otherwise block the whole server's
    single event loop for its duration. FastAPI runs a plain def route in
    a worker thread automatically, so other requests keep being served
    concurrently while this one is busy.
    """
    person = db.get(Person, person_id)
    if person is None:
        raise HTTPException(status_code=404, detail="Person not found.")

    results: list[PhotoEnrollResult] = []
    for f in files:
        data = f.file.read()
        try:
            accepted, reason = enroll_photo(db, person, f.filename or "unnamed", data)
        except ConsentRequiredError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        results.append(PhotoEnrollResult(filename=f.filename or "unnamed", accepted=accepted, reason=reason))

    db.refresh(person)
    return EnrollPhotosResponse(
        person_id=person.id, results=results, total_embeddings=len(person.embeddings)
    )


@router.get("", response_model=list[PersonOut])
def list_people(db: Session = Depends(get_db)):
    people = db.execute(select(Person)).scalars().all()
    return [_to_person_out(p) for p in people]


@router.get("/{person_id}", response_model=PersonOut)
def get_person(person_id: int, db: Session = Depends(get_db)):
    person = db.get(Person, person_id)
    if person is None:
        raise HTTPException(status_code=404, detail="Person not found.")
    return _to_person_out(person)
