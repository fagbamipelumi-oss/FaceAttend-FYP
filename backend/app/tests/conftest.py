from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.models  # noqa: F401
from app.core.database import Base, get_db
from app.main import app as fastapi_app

TEST_DB_PATH = Path(__file__).parent / "test.db"
SMOKE_DIR = Path(__file__).parents[3] / "data" / "test_sets" / "smoke_test"


def photo_bytes(name: str) -> bytes:
    return (SMOKE_DIR / name).read_bytes()


@pytest.fixture()
def db_session_factory():
    if TEST_DB_PATH.exists():
        TEST_DB_PATH.unlink()
    engine = create_engine(f"sqlite:///{TEST_DB_PATH}", connect_args={"check_same_thread": False})
    TestingSessionLocal = sessionmaker(bind=engine)
    Base.metadata.create_all(engine)

    yield TestingSessionLocal

    engine.dispose()
    if TEST_DB_PATH.exists():
        TEST_DB_PATH.unlink()


@pytest.fixture()
def client(db_session_factory, tmp_path, monkeypatch):
    # Redirect raw enrollment photo storage to a throwaway temp dir so tests
    # never write into the real data/raw_enrollment dataset.
    import app.services.enrollment_service as enrollment_service

    monkeypatch.setattr(enrollment_service, "RAW_ENROLLMENT_DIR", tmp_path / "raw_enrollment")

    def override_get_db():
        db = db_session_factory()
        try:
            yield db
        finally:
            db.close()

    fastapi_app.dependency_overrides[get_db] = override_get_db
    with TestClient(fastapi_app) as c:
        yield c
    fastapi_app.dependency_overrides.clear()


@pytest.fixture()
def admin_token(client, db_session_factory):
    from app.core.security import hash_password
    from app.models.admin import AdminUser

    db = db_session_factory()
    db.add(AdminUser(username="admin", password_hash=hash_password("test-password-123")))
    db.commit()
    db.close()

    r = client.post("/auth/login", data={"username": "admin", "password": "test-password-123"})
    assert r.status_code == 200
    return r.json()["access_token"]


@pytest.fixture()
def auth_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}
