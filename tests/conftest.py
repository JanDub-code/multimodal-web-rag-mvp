from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.models import Source, User
from app.db.session import get_db
from app.db.session import Base
from app.api import routes_auth
from app.main import app
from app.services.security import hash_password


@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite://",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    Base.metadata.create_all(engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(engine)


@pytest.fixture()
def source(db_session):
    row = Source(name="Example", base_url="https://example.com", permission_type="public")
    db_session.add(row)
    db_session.commit()
    db_session.refresh(row)
    return row


@pytest.fixture()
def temp_evidence_dirs(tmp_path):
    evidence_dir = tmp_path / "evidence"
    screenshot_dir = evidence_dir / "screenshots"
    dom_dir = evidence_dir / "dom"
    for path in (evidence_dir, screenshot_dir, dom_dir):
        path.mkdir(parents=True, exist_ok=True)
    return {
        "evidence_dir": evidence_dir,
        "screenshot_dir": screenshot_dir,
        "dom_snapshot_dir": dom_dir,
    }


@pytest.fixture()
def fake_screenshot(temp_evidence_dirs):
    path = Path(temp_evidence_dirs["screenshot_dir"]) / "screen.png"
    Image.new("RGB", (32, 32), color="white").save(path)
    return path


@pytest.fixture()
def user_factory(db_session):
    def _create(username: str, password: str, role: str = "User") -> User:
        user = User(username=username, password_hash=hash_password(password), role=role)
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        return user

    return _create


@pytest.fixture()
def api_client(db_session):
    routes_auth._login_attempts.clear()

    def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    try:
        with TestClient(app) as client:
            yield client
    finally:
        app.dependency_overrides.clear()
        routes_auth._login_attempts.clear()
