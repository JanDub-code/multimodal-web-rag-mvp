from pathlib import Path

import pytest
from PIL import Image
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.session import Base


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
