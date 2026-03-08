import sys
from pathlib import Path

from sqlalchemy import select

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.db.models import User
from app.db.session import Base, SessionLocal, engine
from app.services.security import hash_password


def ensure_user(db, username: str, password: str, role: str) -> None:
    existing = db.execute(select(User).where(User.username == username)).scalar_one_or_none()
    if existing:
        return
    db.add(User(username=username, password_hash=hash_password(password), role=role))


def main() -> None:
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        ensure_user(db, "admin", "admin123", "Admin")
        ensure_user(db, "curator", "curator123", "Curator")
        ensure_user(db, "analyst", "analyst123", "Analyst")
        ensure_user(db, "user", "user123", "User")
        db.commit()
    print("Database initialized and default users ensured.")


if __name__ == "__main__":
    main()
