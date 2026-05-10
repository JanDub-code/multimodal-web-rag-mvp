from types import SimpleNamespace

from app.api import routes_query, routes_runtime
from app.db.models import Chunk, Document
from app.services import answering, retrieval


def test_runtime_models_use_opencode_and_lexical_retrieval():
    response = routes_runtime.runtime_models(user=SimpleNamespace(id=1, role="Admin"))

    assert response["text"]["provider"] == "opencode"
    assert response["text"]["model"] == "opencode-go/deepseek-v4-flash"
    assert response["retrieval"]["provider"] == "fastembed-qdrant"


def test_vector_retrieval_returns_matching_chunks(db_session, source):
    document = Document(
        source_id=source.id,
        url="https://example.com/docs",
        doc_version=1,
        content_structured_uri="memory://canonical",
        quality_score=0.8,
    )
    db_session.add(document)
    db_session.flush()
    chunk = Chunk(
        doc_id=document.id,
        chunk_type="text",
        text="Compliance audit evidence is stored for every query.",
        citations_ref='{"url":"https://example.com/docs"}',
    )
    db_session.add(chunk)
    db_session.commit()
    db_session.refresh(chunk)

    retrieval.upsert_chunk_vectors(
        [
            {
                "chunk_id": chunk.id,
                "doc_id": document.id,
                "source_id": source.id,
                "url": document.url,
                "text": chunk.text,
                "chunk_type": chunk.chunk_type,
                "citations_ref": chunk.citations_ref,
            }
        ]
    )

    results = retrieval.search_top_k(db_session, "audit evidence", top_k=3)

    assert results
    assert results[0]["url"] == "https://example.com/docs"


def test_query_model_is_passed_to_generation(monkeypatch, db_session):
    user = SimpleNamespace(id=1, role="User")
    captured = {}

    def fake_answer(query, **kwargs):
        captured.update(kwargs)
        return "ok"

    monkeypatch.setattr(routes_query, "answer_no_rag", fake_answer)

    response = routes_query.ask(
        payload=routes_query.QueryRequest(
            query="hello",
            mode="no-rag",
            model="opencode-go/minimax-m2.7",
        ),
        user=user,
        db=db_session,
    )

    assert response["answer"] == "ok"
    assert response["selected_model"] == "opencode-go/minimax-m2.7"
    assert captured["model"] == "opencode-go/minimax-m2.7"


def test_answer_no_rag_uses_opencode_generation(monkeypatch):
    captured = {}

    def fake_generate(**kwargs):
        captured.update(kwargs)
        return "model output"

    monkeypatch.setattr(answering, "chat_generate", fake_generate)

    assert answering.answer_no_rag("hi", model="opencode-go/deepseek-v4-flash") == "model output"
    assert captured["model"] == "opencode-go/deepseek-v4-flash"
