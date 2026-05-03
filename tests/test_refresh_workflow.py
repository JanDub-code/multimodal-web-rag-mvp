import json
from datetime import datetime, timedelta, timezone

from app.db.models import AuditLog, Chunk, Document, Incident, IngestJob, SourceUrl
from app.services import ingest, refresh
from app.services.request_context import reset_request_id, set_request_id


def _patch_ingest_runtime(monkeypatch, temp_evidence_dirs):
    monkeypatch.setattr(ingest, "validate_public_url", lambda url: None)
    monkeypatch.setattr(ingest, "upsert_chunk_vectors", lambda rows: None)
    monkeypatch.setattr(ingest, "delete_vectors_by_chunk_ids", lambda chunk_ids: None)
    monkeypatch.setattr(ingest, "detect_captcha_heuristic", lambda text, url: (False, None))
    monkeypatch.setattr(ingest.settings, "evidence_dir", str(temp_evidence_dirs["evidence_dir"]))
    monkeypatch.setattr(ingest.settings, "screenshot_dir", str(temp_evidence_dirs["screenshot_dir"]))
    monkeypatch.setattr(ingest.settings, "dom_snapshot_dir", str(temp_evidence_dirs["dom_snapshot_dir"]))
    monkeypatch.setattr(ingest.settings, "vision_extract_on_ingest", False)


def test_refresh_url_reingests_same_url_without_duplicate_documents_or_chunks(
    monkeypatch,
    db_session,
    source,
    temp_evidence_dirs,
):
    _patch_ingest_runtime(monkeypatch, temp_evidence_dirs)
    versions = iter(
        [
            ("Title v1", "first version " * 120),
            ("Title v2", "second version " * 120),
        ]
    )
    monkeypatch.setattr(ingest, "_html_fetch", lambda url: next(versions))

    first = ingest.run_ingest(db_session, source.id, "https://example.com/article", refresh_interval_minutes=60)
    refreshed = refresh.refresh_url(
        db_session,
        source_id=source.id,
        url="https://example.com/article",
        refresh_interval_minutes=60,
        trigger="manual",
    )

    documents = db_session.query(Document).filter(Document.source_id == source.id).all()
    chunks = db_session.query(Chunk).all()
    source_url = db_session.query(SourceUrl).filter(SourceUrl.source_id == source.id).one()

    assert first["status"] == "completed"
    assert refreshed.status == "completed"
    assert refreshed.job_id is not None
    assert len(documents) == 1
    assert len(chunks) == 3
    assert all("second version" in chunk.text for chunk in chunks)
    assert source_url.last_successful_ingest_ts is not None
    assert db_session.query(IngestJob).filter(IngestJob.status == "completed").count() == 2


def test_refresh_url_uses_ingest_fallback_and_records_fetch_incident(
    monkeypatch,
    db_session,
    source,
    temp_evidence_dirs,
    fake_screenshot,
):
    _patch_ingest_runtime(monkeypatch, temp_evidence_dirs)
    html_calls = {"count": 0}

    def flaky_html_fetch(url):
        html_calls["count"] += 1
        if html_calls["count"] == 1:
            return "Initial", "initial text " * 120
        raise RuntimeError("upstream timeout")

    monkeypatch.setattr(ingest, "_html_fetch", flaky_html_fetch)
    monkeypatch.setattr(
        ingest,
        "_render_and_screenshot",
        lambda url: ("Rendered", "rendered fallback text " * 80, str(fake_screenshot), "ocr fallback text"),
    )

    ingest.run_ingest(db_session, source.id, "https://example.com/fallback")
    outcome = refresh.refresh_url(db_session, source_id=source.id, url="https://example.com/fallback", trigger="manual")

    incident = db_session.query(Incident).filter(Incident.type == "fetch_error").one_or_none()
    document = db_session.query(Document).filter(Document.url == "https://example.com/fallback").one()
    chunks = db_session.query(Chunk).filter(Chunk.doc_id == document.id).all()

    assert outcome.status == "completed"
    assert incident is not None
    assert incident.status == "observed"
    assert any("rendered fallback text" in chunk.text for chunk in chunks)


def test_refresh_url_returns_failed_on_ingest_exception_and_updates_attempt(monkeypatch, db_session, source):
    def fail_ingest(**kwargs):
        raise RuntimeError("parser failed")

    monkeypatch.setattr(refresh, "run_ingest", fail_ingest)

    outcome = refresh.refresh_url(db_session, source_id=source.id, url="https://example.com/error", trigger="manual")
    source_url = db_session.query(SourceUrl).filter(SourceUrl.url == "https://example.com/error").one()

    assert outcome.status == "failed"
    assert outcome.job_id is None
    assert outcome.error == "parser failed"
    assert source_url.last_attempt_ts is not None


def test_refresh_stale_urls_audits_summary_and_incident_counts(monkeypatch, db_session, source):
    stale = SourceUrl(
        source_id=source.id,
        url="https://example.com/stale",
        refresh_interval_minutes=1,
        last_successful_ingest_ts=datetime.now(timezone.utc) - timedelta(days=1),
        last_attempt_ts=None,
    )
    fresh = SourceUrl(
        source_id=source.id,
        url="https://example.com/fresh",
        refresh_interval_minutes=1440,
        last_successful_ingest_ts=datetime.now(timezone.utc),
        last_attempt_ts=None,
    )
    db_session.add_all([stale, fresh])
    db_session.commit()
    monkeypatch.setattr(
        refresh,
        "refresh_url",
        lambda *args, **kwargs: refresh.RefreshOutcome(status="blocked_captcha", job_id=123, error=None),
    )
    token = set_request_id("req-refresh-test")

    try:
        summary = refresh.refresh_stale_urls(db_session, batch_size=10, trigger="unit")
    finally:
        reset_request_id(token)

    audit = db_session.query(AuditLog).filter(AuditLog.action == "refresh.batch").one()
    metadata = json.loads(audit.metadata_json or "{}")
    assert summary == {
        "total": 1,
        "status_counts": {"blocked_captcha": 1},
        "incident_types": {"blocked_captcha": 1},
    }
    assert metadata["trigger"] == "unit"
    assert metadata["operation_id"] == "req-refresh-test"
    assert metadata["request_id"] == "req-refresh-test"
    assert metadata["urls"] == [
        {
            "source_id": source.id,
            "url": "https://example.com/stale",
            "status": "blocked_captcha",
            "job_id": 123,
        }
    ]
