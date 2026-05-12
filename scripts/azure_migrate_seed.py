"""Run Azure startup database work: wait for Postgres, migrate, seed users."""

from __future__ import annotations

import os
import time

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text

from app.config import get_settings


def _truthy(value: str | None, *, default: bool = True) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def wait_for_database() -> None:
    settings = get_settings()
    timeout = int(os.getenv("DB_STARTUP_TIMEOUT_SECONDS", "600"))
    interval = int(os.getenv("DB_STARTUP_RETRY_SECONDS", "5"))
    deadline = time.monotonic() + timeout

    engine = create_engine(settings.database_url, future=True, pool_pre_ping=True)
    last_error: Exception | None = None

    while time.monotonic() < deadline:
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            print("Database is reachable.")
            return
        except Exception as exc:  # noqa: BLE001 - retry any startup connection failure
            last_error = exc
            print(f"Waiting for database: {exc}")
            time.sleep(interval)

    raise RuntimeError(f"Database was not reachable within {timeout}s.") from last_error


def run_migrations() -> None:
    print("Running Alembic migrations...")
    alembic_cfg = Config("alembic.ini")
    command.upgrade(alembic_cfg, "head")
    print("Alembic migrations finished.")


def seed_demo_users() -> None:
    if not _truthy(os.getenv("SEED_DEMO_USERS"), default=True):
        print("Skipping demo user seed because SEED_DEMO_USERS is false.")
        return

    print("Ensuring demo users...")
    from scripts.init_db import main as seed_main

    seed_main()


def main() -> None:
    wait_for_database()
    run_migrations()
    seed_demo_users()


if __name__ == "__main__":
    main()
