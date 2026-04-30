import json
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.api import routes_compliance, routes_ingest, routes_query, routes_runtime
from app.db.models import AuditLog, Chunk, Document, Incident, IngestJob, RefreshToken, SystemSetting, User
from app import main as app_main
from app.services import answering, compliance, embeddings, extract, incidents, ingest, retrieval, url_safety
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
        "ollama_chat_generate",
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


def test_permission_metadata_requires_ref_for_non_public():
    with pytest.raises(HTTPException) as exc_info:
        routes_ingest._validate_permission_metadata_or_422("internal", None)

    assert exc_info.value.status_code == 422
    assert "permission_ref is required" in exc_info.value.detail


def test_permission_metadata_is_normalized_for_public():
    permission_type, permission_ref = routes_ingest._validate_permission_metadata_or_422(" Public ", " ")

    assert permission_type == "public"
    assert permission_ref is None


def test_source_permission_validation_rejects_invalid_source(source):
    source.permission_type = "restricted"
    source.permission_ref = None

    with pytest.raises(HTTPException) as exc_info:
        routes_ingest._validate_source_permission_or_422(source)

    assert exc_info.value.status_code == 422


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
    compliance.set_compliance_enforcement_override(False)
    user = SimpleNamespace(id=1, role="User")
    monkeypatch.setattr(routes_query, "answer_no_rag", lambda query, **kwargs: "direct answer")

    try:
        response = routes_query.ask(
            payload=routes_query.QueryRequest(query="What is this?", mode=routes_query.QueryMode.no_rag),
            user=user,
            db=db_session,
        )
    finally:
        compliance.set_compliance_enforcement_override(None)

    assert response["mode"] == "no-rag"
    assert response["answer"] == "direct answer"
    assert response["citations"] == []
    assert response["operation_id"].startswith("op-")
    assert response["compliance_bypassed"] is True
    assert response["compliance_confirmed"] is False
    assert response["model_usage"]["text"]["model"] == routes_query.query_model_usage(mode="no-rag")["text"]["model"]


def test_answer_no_rag_writes_model_call_audit(monkeypatch, db_session):
    monkeypatch.setattr(answering, "ollama_chat_generate", lambda **kwargs: "Model response")
    output = answering.answer_no_rag("What is new?", db=db_session, user_id=42)

    assert output == "Model response"
    entry = db_session.query(AuditLog).order_by(AuditLog.id.desc()).first()
    assert entry is not None
    assert entry.action == "model.call"
    metadata = json.loads(entry.metadata_json or "{}")
    assert metadata.get("context") == "query.no_rag"
    assert metadata.get("status") == "ok"
    assert metadata.get("model") == answering.settings.ollama_model


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

    monkeypatch.setattr(answering, "ollama_chat_generate", fake_generate)
    retrieved = [
        {
            "chunk_id": 101,
            "doc_id": 77,
            "source_id": 8,
            "chunk_type": "text",
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
    assert response["citations"][0]["source_id"] == 8
    assert response["citations"][0]["doc_id"] == 77
    assert response["citations"][0]["chunk_id"] == 101
    assert response["citations"][0]["chunk_type"] == "text"


def test_run_ingest_records_fetch_error_incident_when_html_fails(monkeypatch, db_session, source, temp_evidence_dirs, fake_screenshot):
    _patch_ingest_runtime(monkeypatch, temp_evidence_dirs)

    def fail_html(url):
        raise RuntimeError("upstream timeout")

    monkeypatch.setattr(ingest, "_html_fetch", fail_html)
    monkeypatch.setattr(
        ingest,
        "_render_and_screenshot",
        lambda url: ("Fallback title", "DOM text", str(fake_screenshot), "OCR text"),
    )

    result = ingest.run_ingest(db_session, source.id, "https://example.com/with-fallback")

    assert result["status"] == "completed"
    incident = db_session.query(Incident).filter(Incident.type == "fetch_error").order_by(Incident.id.desc()).first()
    assert incident is not None
    assert incident.status == "observed"
    evidence_payload = json.loads(incident.evidence_refs or "{}")
    assert "reason" in evidence_payload


def test_log_ingest_incident_includes_request_id(db_session, source):
    token = set_request_id("req-incident-42")
    try:
        incident = incidents.log_ingest_incident(
            db_session,
            incident_type="fetch_error",
            source_id=source.id,
            url="https://example.com/incident",
            evidence_refs=[],
            reason="network timeout",
            severity="low",
            status="observed",
        )
    finally:
        reset_request_id(token)

    payload = json.loads(incident.evidence_refs or "{}")
    assert payload["metadata"]["request_id"] == "req-incident-42"


def test_search_top_k_applies_threshold(monkeypatch):
    class Hit:
        def __init__(self, score, payload):
            self.id = payload.get("chunk_id", 1)
            self.score = score
            self.payload = payload

    class DummyQdrant:
        def search(self, **kwargs):
            return [
                Hit(0.91, {"text": "keep", "url": "https://example.com", "citations_ref": json.dumps({"evidence_ids": [1]})}),
                Hit(0.12, {"text": "drop", "url": "https://example.com/low", "citations_ref": json.dumps({"evidence_ids": [2]})}),
            ]

    monkeypatch.setattr(retrieval, "embed_texts", lambda texts: [[0.1, 0.2, 0.3]])
    monkeypatch.setattr(retrieval, "get_qdrant", lambda: DummyQdrant())

    results = retrieval.search_top_k("question", top_k=5, min_score=0.5)

    assert len(results) == 1
    assert results[0]["text"] == "keep"


def test_embed_texts_posts_batch_to_ollama(monkeypatch):
    captured = {}

    class Response:
        def raise_for_status(self):
            return None

        def json(self):
            return {"embeddings": [[0.1, 0.2], [0.3, 0.4]]}

    def fake_post(url, json, timeout):
        captured["url"] = url
        captured["json"] = json
        captured["timeout"] = timeout
        return Response()

    monkeypatch.setattr(embeddings.settings, "embedding_base_url", "http://ollama:11434")
    monkeypatch.setattr(embeddings.settings, "embedding_model", "qwen3-embedding:8b")
    monkeypatch.setattr(embeddings.settings, "embedding_dimensions", 4096)
    monkeypatch.setattr(embeddings.requests, "post", fake_post)

    vectors = embeddings.embed_texts(["a", "b"])

    assert vectors == [[0.1, 0.2], [0.3, 0.4]]
    assert captured["url"] == "http://ollama:11434/api/embed"
    assert captured["json"]["model"] == "qwen3-embedding:8b"
    assert captured["json"]["input"] == ["a", "b"]
    assert captured["json"]["dimensions"] == 4096


def test_embed_texts_rejects_mismatched_response_count(monkeypatch):
    class Response:
        def raise_for_status(self):
            return None

        def json(self):
            return {"embeddings": [[0.1, 0.2]]}

    monkeypatch.setattr(embeddings.requests, "post", lambda *args, **kwargs: Response())

    with pytest.raises(embeddings.EmbeddingBackendError) as exc_info:
        embeddings.embed_texts(["a", "b"])

    assert "returned 1 vectors for 2 inputs" in str(exc_info.value)


def test_embed_texts_wraps_http_errors(monkeypatch):
    class Response:
        status_code = 500
        text = "backend failed"

        def raise_for_status(self):
            raise embeddings.requests.HTTPError(response=self)

    monkeypatch.setattr(embeddings.requests, "post", lambda *args, **kwargs: Response())

    with pytest.raises(embeddings.EmbeddingBackendError) as exc_info:
        embeddings.embed_texts(["a"])

    assert "status 500" in str(exc_info.value)
    assert "backend failed" in str(exc_info.value)


def test_ensure_collection_rejects_existing_dimension_mismatch(monkeypatch):
    class ExistingCollection:
        name = "chunks_qwen3_embedding_8b_4096"

    class Collections:
        collections = [ExistingCollection()]

    class Vectors:
        size = 384

    class Params:
        vectors = Vectors()

    class Config:
        params = Params()

    class CollectionInfo:
        config = Config()

    class DummyQdrant:
        def get_collections(self):
            return Collections()

        def get_collection(self, collection_name):
            return CollectionInfo()

    monkeypatch.setattr(retrieval.settings, "qdrant_collection", "chunks_qwen3_embedding_8b_4096")
    monkeypatch.setattr(retrieval.settings, "embedding_model", "qwen3-embedding:8b")
    monkeypatch.setattr(retrieval, "get_qdrant", lambda: DummyQdrant())

    with pytest.raises(retrieval.QdrantVectorSizeMismatchError) as exc_info:
        retrieval.ensure_collection(vector_size=4096)

    assert "has vector size 384" in str(exc_info.value)
    assert "Use a new QDRANT_COLLECTION" in str(exc_info.value)


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
            "text": "Seznam - najdu tam, co neznam. Mapy, Zbozi, Firmy, Video.",
            "url": "https://www.seznam.cz/",
            "chunk_type": "text",
            "citations": {},
        },
        {
            "score": 0.503,
            "doc_id": 3,
            "source_id": 3,
            "text": "Repasovane notebooky, primo od vyrobce, se zarukou az tri roky",
            "url": "https://notebook.cz/",
            "chunk_type": "text",
            "citations": {},
        },
    ]

    results = retrieval._rerank_and_deduplicate_results(
        query="nejaky repasovany notebook sezenu kde ?",
        rows=rows,
        top_k=5,
    )

    assert len(results) == 1
    assert results[0]["url"] == "https://notebook.cz/"
    assert results[0]["lexical_hits"] >= 1


def test_rag_mode_returns_no_results_message(monkeypatch, db_session):
    compliance.set_compliance_enforcement_override(False)
    user = SimpleNamespace(id=1, role="User")
    monkeypatch.setattr(routes_query, "search_top_k", lambda query, top_k=5: [])

    try:
        response = routes_query.ask(
            payload=routes_query.QueryRequest(query="Unrelated", mode=routes_query.QueryMode.rag),
            user=user,
            db=db_session,
        )
    finally:
        compliance.set_compliance_enforcement_override(None)

    assert response["mode"] == "rag"
    assert response["citations"] == []
    assert response["answer"] == "No relevant documents found for this query."
    assert response["model_usage"]["embedding"]["model"] == routes_query.query_model_usage(mode="rag")["embedding"]["model"]
    assert response["operation_id"].startswith("op-")
    assert response["compliance_bypassed"] is True


def test_query_requires_compliance_confirmation_when_enforced(monkeypatch, db_session):
    compliance.set_compliance_enforcement_override(True)
    user = SimpleNamespace(id=1, role="User")
    monkeypatch.setattr(routes_query, "answer_no_rag", lambda query, **kwargs: "direct answer")

    try:
        with pytest.raises(HTTPException) as exc_info:
            routes_query.ask(
                payload=routes_query.QueryRequest(query="What is this?", mode=routes_query.QueryMode.no_rag),
                user=user,
                db=db_session,
            )
    finally:
        compliance.set_compliance_enforcement_override(None)
    assert exc_info.value.status_code == 422
    assert "Compliance confirmation is required" in exc_info.value.detail


def test_query_accepts_confirmation_when_enforced(monkeypatch, db_session):
    compliance.set_compliance_enforcement_override(True)
    user = SimpleNamespace(id=1, role="User")
    monkeypatch.setattr(routes_query, "answer_no_rag", lambda query, **kwargs: "direct answer")

    try:
        response = routes_query.ask(
            payload=routes_query.QueryRequest(
                query="What is this?",
                mode=routes_query.QueryMode.no_rag,
                operation_id="op-enforced-1",
                compliance_confirmed=True,
                compliance_reason="scheduled test",
            ),
            user=user,
            db=db_session,
        )
    finally:
        compliance.set_compliance_enforcement_override(None)

    assert response["operation_id"] == "op-enforced-1"
    assert response["compliance_confirmed"] is True
    assert response["compliance_bypassed"] is False


def test_ingest_requires_compliance_confirmation_when_enforced(monkeypatch, db_session, source):
    compliance.set_compliance_enforcement_override(True)
    user = SimpleNamespace(id=1, role="Curator")
    monkeypatch.setattr(routes_ingest, "run_ingest", lambda **kwargs: {"status": "completed", "document_id": 1})

    try:
        with pytest.raises(HTTPException) as exc_info:
            routes_ingest.ingest_url(
                payload=routes_ingest.IngestRequest(source_id=source.id, url=f"{source.base_url}/article"),
                user=user,
                db=db_session,
            )
    finally:
        compliance.set_compliance_enforcement_override(None)
    assert exc_info.value.status_code == 422
    assert "Compliance confirmation is required" in exc_info.value.detail


def test_ingest_generates_operation_id_and_bypasses_in_dev_mode(monkeypatch, db_session, source):
    compliance.set_compliance_enforcement_override(False)
    user = SimpleNamespace(id=1, role="Curator")
    monkeypatch.setattr(routes_ingest, "run_ingest", lambda **kwargs: {"status": "completed", "document_id": 1})

    try:
        response = routes_ingest.ingest_url(
            payload=routes_ingest.IngestRequest(source_id=source.id, url=f"{source.base_url}/article"),
            user=user,
            db=db_session,
        )
    finally:
        compliance.set_compliance_enforcement_override(None)

    assert response["operation_id"].startswith("op-")
    assert response["compliance_confirmed"] is False
    assert response["compliance_bypassed"] is True
    assert response["model_usage"]["embedding"]["model"] == routes_ingest.ingest_model_usage()["embedding"]["model"]


def test_runtime_models_endpoint_reports_configured_models():
    user = SimpleNamespace(id=1, role="Admin")

    response = routes_runtime.runtime_models(user=user)

    assert response["text"]["model"] == routes_runtime.configured_model_usage()["text"]["model"]
    assert response["embedding"]["provider"] == "ollama"
    assert response["embedding"]["model"] == "qwen3-embedding:8b"


def test_compliance_history_returns_entries_from_audit(db_session, user_factory):
    compliance.set_compliance_enforcement_override(False)
    user = user_factory("history_user", "secret", role="User")
    try:
        decision = compliance.resolve_sensitive_action_compliance(
            db=db_session,
            user=user,
            action_type="query.execute",
            operation_id="op-history-1",
            compliance_confirmed=False,
            compliance_reason="",
            compliance_bypassed=True,
        )
        db_session.commit()
    finally:
        compliance.set_compliance_enforcement_override(None)

    history_rows = routes_compliance.history(limit=20, user=user, db=db_session)

    assert len(history_rows) >= 1
    assert history_rows[0]["operation_id"] == decision.operation_id
    assert history_rows[0]["action"] == "query.execute"
    assert history_rows[0]["compliance_bypassed"] is True


def test_compliance_mode_set_and_get_uses_runtime_override():
    compliance.set_compliance_enforcement_override(None)
    viewer = SimpleNamespace(id=1, role="User")
    admin = SimpleNamespace(id=2, role="Admin")

    initial = routes_compliance.get_mode(user=viewer)
    updated = routes_compliance.set_mode(
        payload=routes_compliance.ComplianceModeUpdateRequest(enforcement=not initial["enforcement"]),
        user=admin,
    )
    after = routes_compliance.get_mode(user=viewer)

    compliance.set_compliance_enforcement_override(None)

    assert updated["source"] == "runtime_override"
    assert after["enforcement"] == updated["enforcement"]


def test_health_returns_200_when_required_components_up(monkeypatch, api_client):
    monkeypatch.setattr(app_main, "_check_postgres", lambda: {"status": "up"})
    monkeypatch.setattr(app_main, "_check_qdrant", lambda: {"status": "up"})
    monkeypatch.setattr(app_main, "_check_ollama_backend", lambda: {"status": "down", "error": "offline"})

    response = api_client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["components"]["ollama"]["required"] is False
    assert body["components"]["ollama"]["status"] == "down"


def test_health_ready_returns_200_when_required_components_up(monkeypatch, api_client):
    monkeypatch.setattr(app_main, "_check_postgres", lambda: {"status": "up"})
    monkeypatch.setattr(app_main, "_check_qdrant", lambda: {"status": "up"})
    monkeypatch.setattr(app_main, "_check_ollama_backend", lambda: {"status": "up"})

    response = api_client.get("/health/ready")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_health_returns_503_when_required_component_down(monkeypatch, api_client):
    monkeypatch.setattr(app_main, "_check_postgres", lambda: {"status": "down", "error": "db down"})
    monkeypatch.setattr(app_main, "_check_qdrant", lambda: {"status": "up"})
    monkeypatch.setattr(app_main, "_check_ollama_backend", lambda: {"status": "up"})

    response = api_client.get("/health")

    assert response.status_code == 503
    assert response.json()["status"] == "degraded"


def test_health_ready_returns_503_when_required_component_down(monkeypatch, api_client):
    monkeypatch.setattr(app_main, "_check_postgres", lambda: {"status": "up"})
    monkeypatch.setattr(app_main, "_check_qdrant", lambda: {"status": "down", "error": "qdrant down"})
    monkeypatch.setattr(app_main, "_check_ollama_backend", lambda: {"status": "up"})

    response = api_client.get("/health/ready")

    assert response.status_code == 503
    assert response.json()["status"] == "degraded"


def test_health_echoes_request_id_header(api_client):
    response = api_client.get("/health", headers={"X-Request-ID": "req-health-123"})

    assert response.status_code in (200, 503)
    assert response.headers["X-Request-ID"] == "req-health-123"


def test_login_returns_refresh_token_and_audit_request_id(api_client, db_session, user_factory):
    user_factory("alice", "secret", role="User")

    response = api_client.post(
        "/api/auth/login",
        data={"username": "alice", "password": "secret"},
        headers={"X-Request-ID": "req-login-1"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["access_token"]
    assert body["refresh_token"]
    assert body["token_type"] == "bearer"
    assert response.headers["X-Request-ID"] == "req-login-1"

    token_count = db_session.query(RefreshToken).count()
    assert token_count == 1

    latest_audit = db_session.query(AuditLog).order_by(AuditLog.id.desc()).first()
    assert latest_audit is not None
    metadata = json.loads(latest_audit.metadata_json or "{}")
    assert metadata.get("request_id") == "req-login-1"


def test_login_with_invalid_stored_hash_returns_401(api_client, db_session):
    db_session.add(User(username="broken", password_hash="not-a-passlib-hash", role="User"))
    db_session.commit()

    response = api_client.post("/api/auth/login", data={"username": "broken", "password": "secret"})

    assert response.status_code == 401


def test_settings_retention_roundtrip_persists_and_audits(api_client, db_session, user_factory):
    user_factory("admin", "secret", role="Admin")
    login = api_client.post("/api/auth/login", data={"username": "admin", "password": "secret"})
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}", "X-Request-ID": "req-settings-1"}

    defaults = api_client.get("/api/settings", headers=headers)
    assert defaults.status_code == 200
    assert defaults.json()["retention"] == {
        "raw_evidence": "60 dní",
        "audit_logs": "60 dní",
        "vector_snapshot": "60 dní",
    }

    payload = {
        "retention": {
            "raw_evidence": "90 dní",
            "audit_logs": "1 rok",
            "vector_snapshot": "30 dní",
        }
    }
    updated = api_client.put("/api/settings", json=payload, headers=headers)

    assert updated.status_code == 200
    assert updated.json() == payload
    assert db_session.query(SystemSetting).count() == 3

    latest_audit = db_session.query(AuditLog).order_by(AuditLog.id.desc()).first()
    assert latest_audit.action == "settings.updated"
    metadata = json.loads(latest_audit.metadata_json or "{}")
    assert metadata["retention"] == payload["retention"]
    assert metadata["request_id"] == "req-settings-1"


def test_refresh_rotates_token_and_rejects_reuse(api_client, db_session, user_factory):
    user_factory("bob", "secret", role="User")

    login = api_client.post("/api/auth/login", data={"username": "bob", "password": "secret"})
    assert login.status_code == 200
    old_refresh = login.json()["refresh_token"]

    refreshed = api_client.post("/api/auth/refresh", json={"refresh_token": old_refresh})
    assert refreshed.status_code == 200
    new_refresh = refreshed.json()["refresh_token"]
    assert new_refresh != old_refresh

    reused = api_client.post("/api/auth/refresh", json={"refresh_token": old_refresh})
    assert reused.status_code == 401

    # New token remains valid and can rotate again.
    refreshed_again = api_client.post("/api/auth/refresh", json={"refresh_token": new_refresh})
    assert refreshed_again.status_code == 200

    active_tokens = db_session.query(RefreshToken).filter(RefreshToken.revoked_ts.is_(None)).count()
    assert active_tokens == 1


def test_logout_revokes_refresh_token(api_client, db_session, user_factory):
    user_factory("carol", "secret", role="User")

    login = api_client.post("/api/auth/login", data={"username": "carol", "password": "secret"})
    assert login.status_code == 200
    refresh_token = login.json()["refresh_token"]

    logout = api_client.post("/api/auth/logout", json={"refresh_token": refresh_token})
    assert logout.status_code == 200
    assert logout.json() == {"status": "ok"}

    refresh_after_logout = api_client.post("/api/auth/refresh", json={"refresh_token": refresh_token})
    assert refresh_after_logout.status_code == 401
