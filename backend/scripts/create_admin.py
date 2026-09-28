"""One-off CLI to create the first admin user.

Usage:
    venv/Scripts/python.exe scripts/create_admin.py <username> <password>

There is no public registration endpoint by design; admin accounts are
created out-of-band by whoever controls the server.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select

import app.models  # noqa: F401
from app.core.database import Base, SessionLocal, engine
from app.core.security import hash_password
from app.models.admin import AdminUser


def main() -> None:
    if len(sys.argv) != 3:
        print("Usage: create_admin.py <username> <password>")
        raise SystemExit(1)

    username, password = sys.argv[1], sys.argv[2]
    Base.metadata.create_all(engine)

    db = SessionLocal()
    try:
        existing = db.execute(select(AdminUser).where(AdminUser.username == username)).scalar_one_or_none()
        if existing is not None:
            print(f"Admin '{username}' already exists.")
            raise SystemExit(1)

        admin = AdminUser(username=username, password_hash=hash_password(password))
        db.add(admin)
        db.commit()
        print(f"Admin '{username}' created.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
