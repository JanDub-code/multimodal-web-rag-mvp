import json
import sys

import pytest

from scripts import eval_retrieval


def test_run_eval_computes_metrics_and_result_payload(monkeypatch):
    hits_by_query = {
        "alpha": [
            {"chunk_id": 10, "doc_id": 1, "source_id": 1, "url": "https://example.com/a", "score": 0.91},
            {"chunk_id": 11, "doc_id": 2, "source_id": 1, "url": "https://example.com/b", "score": 0.75},
        ],
        "beta": [
            {"chunk_id": 20, "doc_id": 3, "source_id": 2, "url": "https://example.com/c", "score": 0.88},
        ],
    }
    monkeypatch.setattr(eval_retrieval, "search_top_k", lambda query, top_k: hits_by_query[query])

    report = eval_retrieval.run_eval(
        [
            {"query": "alpha", "expected_doc_id": 2},
            {"query": "beta", "expected_url_contains": "/missing"},
        ],
        top_k=5,
    )

    assert report["query_count"] == 2
    assert report["scored_query_count"] == 2
    assert report["metrics"]["recall_at_k"] == 0.5
    assert report["metrics"]["mrr_at_k"] == 0.25
    assert report["metrics"]["latency_p50_ms"] is not None
    assert report["metrics"]["latency_p95_ms"] is not None
    assert report["results"][0]["rank"] == 2
    assert report["results"][0]["matched"] is True
    assert report["results"][1]["rank"] is None
    assert report["results"][1]["matched"] is False
    assert report["results"][0]["top_hits"][0] == {
        "chunk_id": 10,
        "doc_id": 1,
        "source_id": 1,
        "url": "https://example.com/a",
        "score": 0.91,
    }


def test_load_queries_rejects_invalid_dataset(tmp_path):
    dataset_path = tmp_path / "invalid.json"
    dataset_path.write_text(json.dumps([{"expected_doc_id": 1}]), encoding="utf-8")

    with pytest.raises(ValueError, match="non-empty 'query'"):
        eval_retrieval._load_queries(str(dataset_path))


def test_main_writes_report_and_enforces_quality_gate(monkeypatch, tmp_path):
    dataset_path = tmp_path / "queries.json"
    dataset_path.write_text(
        json.dumps(
            [
                {"query": "alpha", "expected_chunk_id": 1},
                {"query": "beta", "expected_chunk_id": 2},
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        eval_retrieval,
        "search_top_k",
        lambda query, top_k: [{"chunk_id": 1, "doc_id": 10, "source_id": 1, "url": "https://example.com", "score": 0.9}],
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "eval_retrieval.py",
            "--queries",
            str(dataset_path),
            "--top-k",
            "5",
            "--report-dir",
            str(tmp_path),
            "--min-recall",
            "0.75",
            "--min-mrr",
            "0.5",
        ],
    )

    exit_code = eval_retrieval.main()

    reports = list(tmp_path.glob("retrieval_eval_*.json"))
    assert exit_code == 2
    assert len(reports) == 1
    payload = json.loads(reports[0].read_text(encoding="utf-8"))
    assert payload["top_k"] == 5
    assert payload["query_count"] == 2
    assert payload["scored_query_count"] == 2
    assert payload["metrics"]["recall_at_k"] == 0.5
    assert payload["metrics"]["mrr_at_k"] == 0.5
    assert payload["quality_gate"] == {"min_recall_at_k": 0.75, "min_mrr_at_k": 0.5}
