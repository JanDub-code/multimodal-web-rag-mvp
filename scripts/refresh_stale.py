#!/usr/bin/env python3
from __future__ import annotations

import json
from uuid import uuid4

from app.db.session import SessionLocal
from app.services.refresh import refresh_stale_urls
from app.services.request_context import reset_request_id, set_request_id


def main() -> None:
    token = set_request_id(f"refresh-cron-{uuid4()}")
    try:
        with SessionLocal() as db:
            summary = refresh_stale_urls(db, trigger="cron")
            print(json.dumps(summary, ensure_ascii=False, indent=2))
    finally:
        reset_request_id(token)


if __name__ == "__main__":
    main()
