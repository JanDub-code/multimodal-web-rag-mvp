#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from app.config import get_settings
from app.services.eval_metrics import mrr_at_k, percentile, recall_at_k
from app.services.retrieval import search_top_k

settings = get_settings()


def _load_queries(path: str) -> list[dict]:
    with Path(path).open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, list):
        raise ValueError("Eval dataset must be a JSON array")
    for item in payload:
        if not isinstance(item, dict) or not item.get("query"):
            raise ValueError("Each eval item must contain a non-empty 'query'")
    return payload


def _has_expectation(item: dict) -> bool:
    return any(
        item.get(key)
        for key in ("expected_chunk_id", "expected_doc_id", "expected_source_id", "expected_url_contains")
    )


def _matches_expectation(item: dict, hit: dict) -> bool:
    if item.get("expected_chunk_id") is not None and str(hit.get("chunk_id")) == str(item.get("expected_chunk_id")):
        return True
    if item.get("expected_doc_id") is not None and str(hit.get("doc_id")) == str(item.get("expected_doc_id")):
        return True
    if item.get("expected_source_id") is not None and str(hit.get("source_id")) == str(item.get("expected_source_id")):
        return True
    expected_url = str(item.get("expected_url_contains") or "").strip()
    return bool(expected_url and expected_url in str(hit.get("url") or ""))


def run_eval(queries: list[dict], top_k: int) -> dict:
    latencies_ms: list[float] = []
    hit_flags: list[bool] = []
    ranks: list[int | None] = []
    scored_queries = 0
    results_payload: list[dict] = []

    for item in queries:
        start = time.perf_counter()
        results = search_top_k(item["query"], top_k=top_k)
        latency_ms = (time.perf_counter() - start) * 1000
        latencies_ms.append(latency_ms)

        rank = None
        matched = False
        if _has_expectation(item):
            scored_queries += 1
            for idx, hit in enumerate(results, start=1):
                if _matches_expectation(item, hit):
                    rank = idx
                    matched = True
                    break
            hit_flags.append(matched)
            ranks.append(rank)

        results_payload.append(
            {
                "query": item["query"],
                "expected": {
                    "expected_chunk_id": item.get("expected_chunk_id"),
                    "expected_doc_id": item.get("expected_doc_id"),
                    "expected_source_id": item.get("expected_source_id"),
                    "expected_url_contains": item.get("expected_url_contains"),
                },
                "rank": rank,
                "matched": matched if _has_expectation(item) else None,
                "latency_ms": latency_ms,
                "top_hits": [
                    {
                        "chunk_id": hit.get("chunk_id"),
                        "doc_id": hit.get("doc_id"),
                        "source_id": hit.get("source_id"),
                        "url": hit.get("url"),
                        "score": hit.get("score"),
                    }
                    for hit in results
                ],
            }
        )

    return {
        "query_count": len(queries),
        "scored_query_count": scored_queries,
        "metrics": {
            "recall_at_k": recall_at_k(hit_flags),
            "mrr_at_k": mrr_at_k(ranks),
            "latency_p50_ms": percentile(latencies_ms, 0.5),
            "latency_p95_ms": percentile(latencies_ms, 0.95),
        },
        "results": results_payload,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate retrieval Recall@k, MRR@k, and latency.")
    parser.add_argument("--queries", required=True, help="Path to JSON eval dataset")
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--report-dir", default="reports")
    parser.add_argument("--min-recall", type=float, default=0.6)
    parser.add_argument("--min-mrr", type=float, default=0.3)
    args = parser.parse_args()

    queries = _load_queries(args.queries)
    payload = run_eval(queries, top_k=args.top_k)

    now = datetime.now(timezone.utc)
    report_dir = Path(args.report_dir)
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / f"retrieval_eval_{now.strftime('%Y%m%d_%H%M%S')}.json"

    report = {
        "generated_at": now.isoformat(),
        "top_k": args.top_k,
        "min_score": settings.retrieval_min_score,
        "metrics": payload["metrics"],
        "query_count": payload["query_count"],
        "scored_query_count": payload["scored_query_count"],
        "results": payload["results"],
        "quality_gate": {
            "min_recall_at_k": args.min_recall,
            "min_mrr_at_k": args.min_mrr,
        },
    }

    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    recall = report["metrics"]["recall_at_k"]
    mrr = report["metrics"]["mrr_at_k"]
    if recall is not None and recall < args.min_recall:
        return 2
    if mrr is not None and mrr < args.min_mrr:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
