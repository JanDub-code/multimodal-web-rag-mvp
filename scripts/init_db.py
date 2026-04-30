import sys
from pathlib import Path

from sqlalchemy import select, text
from sqlalchemy.exc import SQLAlchemyError

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.db.models import User
from app.db.session import SessionLocal
from app.services.security import hash_password, verify_password


def ensure_user(db, username: str, password: str, role: str) -> str:
    existing = db.execute(select(User).where(User.username == username)).scalar_one_or_none()
    if existing:
        password_matches = False
        try:
            password_matches = verify_password(password, existing.password_hash)
        except Exception:
            password_matches = False

        if password_matches and existing.role == role:
            return "unchanged"

        existing.password_hash = hash_password(password)
        existing.role = role
        return "updated"

    db.add(User(username=username, password_hash=hash_password(password), role=role))
    return "created"


def ensure_schema_ready(db) -> None:
    try:
        db.execute(text("SELECT 1 FROM users LIMIT 1"))
    except SQLAlchemyError as exc:
        raise RuntimeError(
            "Database schema is missing. Run migrations first: `alembic upgrade head`."
        ) from exc


def main() -> None:
    with SessionLocal() as db:
        ensure_schema_ready(db)
        results = {
            "admin": ensure_user(db, "admin", "admin123", "Admin"),
            "curator": ensure_user(db, "curator", "curator123", "Curator"),
            "analyst": ensure_user(db, "analyst", "analyst123", "Analyst"),
            "user": ensure_user(db, "user", "user123", "User"),
        }
        db.commit()
    summary = ", ".join(f"{username}:{status}" for username, status in results.items())
    print(f"Default users ensured ({summary}).")


if __name__ == "__main__":
    main()
