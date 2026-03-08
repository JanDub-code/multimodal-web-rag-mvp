import json
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.api import routes_ingest, routes_query
from app.db.models import Chunk, Document, Incident, IngestJob, Source
from app.services import answering, extract, ingest, retrieval, url_safety


@pytest.fixture()
def source(db_session):
    row = Source(name="Example", base_url="https://example.com", permission_type="public")
    db_session.add(row)
    db_session.commit()
    db_session.refresh(row)
    return row


def _patch_ingest_runtime(monkeypatch, temp_evidence_dirs):
    monkeypatch.setattr(ingest, "validate_public_url", lambda url: None)
    monkeypatch.setattr(ingest, "upsert_chunk_vectors", lambda rows: None)
    monkeypatch.setattr(ingest, "delete_vectors_by_chunk_ids", lambda chunk_ids: None)
    monkeypatch.setattr(ingest, "detect_captcha_heuristic", lambda text, url: (False, None))
    monkeypatch.setattr(ingest.settings, "evidence_dir", str(temp_evidence_dirs["evidence_dir"]))
    monkeypatch.setattr(ingest.settings, "screenshot_dir", str(temp_evidence_dirs["screenshot_dir"]))
    monkeypatch.setattr(ingest.settings, "dom_snapshot_dir", str(temp_evidence_dirs["dom_snapshot_dir"]))
    monkeypatch.setattr(ingest.settings, "vision_extract_on_ingest", False)


def test_run_ingest_html_path_persists_real_quality_score(monkeypatch, db_session, source, temp_evidence_dirs):
    _patch_ingest_runtime(monkeypatch, temp_evidence_dirs)
    monkeypatch.setattr(ingest, "_html_fetch", lambda url: ("Title", "A" * 800 + "\n" + "B" * 800))

    result = ingest.run_ingest(db_session, source.id, "https://example.com/article")

    document = db_session.get(Document, result["document_id"])
    canonical = json.loads(open(document.content_structured_uri, encoding="utf-8").read())
    assert result["strategy"] == "HTML"
    assert 0.0 <= document.quality_score <= 1.0
    assert canonical["metadata"]["quality_metrics"]["text_length_chars"] >= 1600
    assert len(result["evidence_ids"]) == 1


def test_run_ingest_rendered_dom_uses_ocr_evidence(monkeypatch, db_session, source, temp_evidence_dirs, fake_screenshot):
    _patch_ingest_runtime(monkeypatch, temp_evidence_dirs)
    monkeypatch.setattr(ingest, "_html_fetch", lambda url: ("Title", "too short"))
    monkeypatch.setattr(
        ingest,
        "_render_and_screenshot",
        lambda url: ("Rendered title", "Rendered DOM text " * 40, str(fake_screenshot), "Visible OCR text"),
    )

    result = ingest.run_ingest(db_session, source.id, "https://example.com/rendered")

    document = db_session.get(Document, result["document_id"])
    canonical = json.loads(open(document.content_structured_uri, encoding="utf-8").read())
    assert result["strategy"] == "RENDERED_DOM"
    assert canonical["metadata"]["ocr_used"] is True
    assert canonical["metadata"]["ocr_chars"] > 0
    assert canonical["metadata"]["vision_used"] is False
    assert len(result["evidence_ids"]) == 4


def test_run_ingest_screenshot_fallback_uses_ocr_text(monkeypatch, db_session, source, temp_evidence_dirs, fake_screenshot):
    _patch_ingest_runtime(monkeypatch, temp_evidence_dirs)

    def fail_html(url):
        raise RuntimeError("boom")

    monkeypatch.setattr(ingest, "_html_fetch", fail_html)
    monkeypatch.setattr(
        ingest,
        "_render_and_screenshot",
        lambda url: ("Fallback title", "", str(fake_screenshot), "Text only visible in screenshot"),
    )

    result = ingest.run_ingest(db_session, source.id, "https://example.com/visual")

    document = db_session.get(Document, result["document_id"])
    canonical = json.loads(open(document.content_structured_uri, encoding="utf-8").read())
    assert result["strategy"] == "SCREENSHOT"
    assert canonical["sections"][0]["content"] == "Text only visible in screenshot"
    assert canonical["metadata"]["ocr_used"] is True
    assert len(result["evidence_ids"]) == 3


def test_run_ingest_vision_extract_adds_sections_and_table_chunks(monkeypatch, db_session, source, temp_evidence_dirs, fake_screenshot):
    _patch_ingest_runtime(monkeypatch, temp_evidence_dirs)
    monkeypatch.setattr(ingest.settings, "vision_extract_on_ingest", True)

    def fail_html(url):
        raise RuntimeError("boom")

    monkeypatch.setattr(ingest, "_html_fetch", fail_html)
    monkeypatch.setattr(
        ingest,
        "_render_and_screenshot",
        lambda url: ("Rendered title", "DOM fallback text", str(fake_screenshot), "OCR fallback text"),
    )
    monkeypatch.setattr(
        ingest,
        "extract_structured_document_from_image",
        lambda **kwargs: (
            {
                "title": "Vision title",
                "visual_summary": "Dashboard with KPI table",
                "model": "qwen-test",
                "sections": [
                    {"heading": "Overview", "content": "Revenue increased to 120."},
                    {"heading": "Notes", "content": "Visual trend is positive."},
                ],
                "tables": [
                    {"title": "KPIs", "columns": ["Metric", "Value"], "rows": [["Revenue", "120"], ["Margin", "20%"]]}
                ],
            },
            '{"title":"Vision title"}',
        ),
    )

    result = ingest.run_ingest(db_session, source.id, "https://example.com/vision")

    document = db_session.get(Document, result["document_id"])
    canonical = json.loads(open(document.content_structured_uri, encoding="utf-8").read())
    chunk_rows = db_session.query(Chunk).filter(Chunk.doc_id == document.id).all()

    assert canonical["title"] == "Vision title"
    assert canonical["metadata"]["vision_used"] is True
    assert canonical["metadata"]["vision_model"] == "qwen-test"
    assert canonical["tables"][0]["title"] == "KPIs"
    assert any(chunk.chunk_type == "table" for chunk in chunk_rows)
    assert any(chunk.chunk_type == "text" for chunk in chunk_rows)
    assert len(result["evidence_ids"]) == 4


def test_run_ingest_vision_failure_falls_back_to_ocr_text(monkeypatch, db_session, source, temp_evidence_dirs, fake_screenshot):
    _patch_ingest_runtime(monkeypatch, temp_evidence_dirs)
    monkeypatch.setattr(ingest.settings, "vision_extract_on_ingest", True)

    def fail_html(url):
        raise RuntimeError("boom")

    monkeypatch.setattr(ingest, "_html_fetch", fail_html)
    monkeypatch.setattr(
        ingest,
        "_render_and_screenshot",
        lambda url: ("Rendered title", "", str(fake_screenshot), "OCR fallback text"),
    )
    monkeypatch.setattr(ingest, "extract_structured_document_from_image", lambda **kwargs: (None, "not-json"))

    result = ingest.run_ingest(db_session, source.id, "https://example.com/vision-fallback")

    document = db_session.get(Document, result["document_id"])
    canonical = json.loads(open(document.content_structured_uri, encoding="utf-8").read())
    assert canonical["sections"][0]["content"] == "OCR fallback text"
    assert canonical["metadata"]["vision_used"] is False
    assert len(result["evidence_ids"]) == 4


def test_run_ingest_captcha_blocks_indexing_and_cleans_previous_document(monkeypatch, db_session, source, temp_evidence_dirs):
    monkeypatch.setattr(ingest, "validate_public_url", lambda url: None)
    deleted_chunk_ids = []
    monkeypatch.setattr(ingest, "upsert_chunk_vectors", lambda rows: (_ for _ in ()).throw(AssertionError("should not index captcha")))
    monkeypatch.setattr(ingest, "delete_vectors_by_chunk_ids", lambda chunk_ids: deleted_chunk_ids.extend(chunk_ids))
    monkeypatch.setattr(ingest.settings, "evidence_dir", str(temp_evidence_dirs["evidence_dir"]))
    monkeypatch.setattr(ingest.settings, "screenshot_dir", str(temp_evidence_dirs["screenshot_dir"]))
    monkeypatch.setattr(ingest.settings, "dom_snapshot_dir", str(temp_evidence_dirs["dom_snapshot_dir"]))
    monkeypatch.setattr(ingest, "_html_fetch", lambda url: ("Blocked", "verify you are human " * 30))

    existing_doc = Document(
        source_id=source.id,
        url="https://example.com/blocked",
        doc_version=1,
        content_structured_uri=str(temp_evidence_dirs["evidence_dir"] / "old.json"),
        quality_score=0.5,
    )
    db_session.add(existing_doc)
    db_session.flush()
    existing_chunk = Chunk(doc_id=existing_doc.id, chunk_type="text", text="old", citations_ref="{}")
    db_session.add(existing_chunk)
    old_canonical_path = temp_evidence_dirs["evidence_dir"] / "old.json"
    old_canonical_path.write_text("{}", encoding="utf-8")
    db_session.commit()
    existing_chunk_id = existing_chunk.id

    result = ingest.run_ingest(db_session, source.id, "https://example.com/blocked")

    assert result["status"] == "blocked_captcha"
    assert result["document_id"] is None
    assert result["incident_id"] is not None
    assert db_session.query(Document).count() == 0
    assert db_session.query(Chunk).count() == 0
    assert db_session.query(Incident).count() == 1
    job = db_session.get(IngestJob, result["job_id"])
    assert job is not None
    assert job.status == "blocked_captcha"
    assert deleted_chunk_ids == [existing_chunk_id]
    assert not old_canonical_path.exists()


def test_extract_screenshot_text_uses_vision_when_tesseract_is_missing(monkeypatch, fake_screenshot):
    monkeypatch.setattr(
        ingest.pytesseract,
        "image_to_string",
        lambda *args, **kwargs: (_ for _ in ()).throw(ingest.pytesseract.TesseractNotFoundError()),
    )
    monkeypatch.setattr(ingest.settings, "ollama_model", "qwen3.5:9b")
    monkeypatch.setattr(ingest.settings, "ollama_vision_model", "qwen3.5:9b")
    monkeypatch.setattr(
        ingest,
        "ollama_generate",
        lambda **kwargs: "Visible screenshot text extracted by vision",
    )

    text = ingest._extract_screenshot_text(str(fake_screenshot))

    assert text == "Visible screenshot text extracted by vision"


def test_safe_session_prefers_explicit_ca_bundle(monkeypatch):
    monkeypatch.setattr(url_safety.settings, "fetch_verify_ssl", True)
    bundle_path = "/tmp/custom-ca.pem"
    monkeypatch.setenv("REQUESTS_CA_BUNDLE", bundle_path)
    monkeypatch.setattr(url_safety.Path, "is_file", lambda path: str(path) == bundle_path)

    session = url_safety.SafeSession()

    assert session.verify == bundle_path


def test_safe_session_can_disable_ssl_verification(monkeypatch):
    monkeypatch.setattr(url_safety.settings, "fetch_verify_ssl", False)

    session = url_safety.SafeSession()

    assert session.verify is False


def test_ingest_url_must_stay_within_selected_source_scope(source):
    with pytest.raises(HTTPException) as exc_info:
        routes_ingest._validate_ingest_url_matches_source_or_422(source, "https://www.ikea.com/cz/cs/")

    assert exc_info.value.status_code == 422
    assert "outside the selected source scope" in exc_info.value.detail


def test_persist_canonical_document_for_key_avoids_cross_source_collisions(tmp_path):
    payload = extract.to_canonical_document(
        url="https://example.com",
        title="Example Domain",
        text="This domain is for use in documentation examples.",
        strategy="HTML",
        evidence_ids=[1],
    )

    path_a, _ = extract.persist_canonical_document_for_key(str(tmp_path), payload, "source:1:https://example.com")
    path_b, _ = extract.persist_canonical_document_for_key(str(tmp_path), payload, "source:2:https://example.com")

    assert path_a != path_b


def test_query_request_rejects_invalid_mode():
    with pytest.raises(ValidationError):
        routes_query.QueryRequest(query="Hello", mode="something-else")


def test_ask_no_rag_mode_returns_direct_answer(monkeypatch, db_session):
    user = SimpleNamespace(id=1, role="User")
    monkeypatch.setattr(routes_query, "answer_no_rag", lambda query: "direct answer")

    response = routes_query.ask(
        payload=routes_query.QueryRequest(query="What is this?", mode=routes_query.QueryMode.no_rag),
        user=user,
        db=db_session,
    )

    assert response == {"mode": "no-rag", "answer": "direct answer", "citations": []}


def test_answer_rag_uses_screenshot_as_multimodal_input(monkeypatch, fake_screenshot):
    captured = {}
    monkeypatch.setattr(answering.settings, "vision_answer_enabled", True)
    monkeypatch.setattr(answering.settings, "ollama_model", "text-model")
    monkeypatch.setattr(answering.settings, "ollama_vision_model", "vision-model")

    def fake_generate(prompt, model, image_paths=None, timeout=None):
        captured["prompt"] = prompt
        captured["model"] = model
        captured["image_paths"] = image_paths
        return "Grounded answer [1]"

    monkeypatch.setattr(answering, "ollama_generate", fake_generate)
    retrieved = [
        {
            "text": "Revenue increased to 120.",
            "url": "https://example.com/report",
            "score": 0.9,
            "citations": {
                "evidence_items": [
                    {"id": 1, "type": "screenshot", "storage_uri": str(fake_screenshot), "hash": "abc"}
                ]
            },
        }
    ]

    response = answering.answer_rag("What happened?", retrieved)

    assert response["answer"] == "Grounded answer [1]"
    assert captured["model"] == "vision-model"
    assert captured["image_paths"] == [str(fake_screenshot)]


def test_search_top_k_applies_threshold(monkeypatch):
    class DummyEmbedder:
        def encode(self, texts, normalize_embeddings=True):
            return [[0.1, 0.2, 0.3]]

    class Hit:
        def __init__(self, score, payload):
            self.score = score
            self.payload = payload

    class DummyQdrant:
        def search(self, **kwargs):
            return [
                Hit(0.91, {"text": "keep", "url": "https://example.com", "citations_ref": json.dumps({"evidence_ids": [1]})}),
                Hit(0.12, {"text": "drop", "url": "https://example.com/low", "citations_ref": json.dumps({"evidence_ids": [2]})}),
            ]

    monkeypatch.setattr(retrieval, "get_embedder", lambda: DummyEmbedder())
    monkeypatch.setattr(retrieval, "get_qdrant", lambda: DummyQdrant())

    results = retrieval.search_top_k("question", top_k=5, min_score=0.5)

    assert len(results) == 1
    assert results[0]["text"] == "keep"


def test_rerank_prefers_lexical_match_and_deduplicates_by_document():
    rows = [
        {
            "score": 0.57,
            "doc_id": 3,
            "source_id": 3,
            "text": "NOTEBOOK.cz - Notebooky, Testy, Recenze",
            "url": "https://notebook.cz/",
            "chunk_type": "text",
            "citations": {},
        },
        {
            "score": 0.545,
            "doc_id": 2,
            "source_id": 2,
            "text": "Seznam – najdu tam, co neznám. Mapy, Zboží, Firmy, Video.",
            "url": "https://www.seznam.cz/",
            "chunk_type": "text",
            "citations": {},
        },
        {
            "score": 0.503,
            "doc_id": 3,
            "source_id": 3,
            "text": "Repasované notebooky, přímo od výrobce, se zárukou až tři roky",
            "url": "https://notebook.cz/",
            "chunk_type": "text",
            "citations": {},
        },
    ]

    results = retrieval._rerank_and_deduplicate_results(
        query="nějaký repasovaný notebook seženu kde ?",
        rows=rows,
        top_k=5,
    )

    assert len(results) == 1
    assert results[0]["url"] == "https://notebook.cz/"
    assert results[0]["lexical_hits"] >= 1


def test_rag_mode_returns_no_results_message(monkeypatch, db_session):
    user = SimpleNamespace(id=1, role="User")
    monkeypatch.setattr(routes_query, "search_top_k", lambda query, top_k=5: [])

    response = routes_query.ask(
        payload=routes_query.QueryRequest(query="Unrelated", mode=routes_query.QueryMode.rag),
        user=user,
        db=db_session,
    )

    assert response["mode"] == "rag"
    assert response["citations"] == []
    assert response["answer"] == "No relevant documents found for this query."
