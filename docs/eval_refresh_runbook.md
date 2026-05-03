# Eval and Refresh Runbook

This runbook covers the operational checks for retrieval evaluation and refresh.

## Prerequisites

- Docker stack is running and migrations have been applied.
- API container can import the application with `PYTHONPATH=/app`.
- For a meaningful retrieval eval, Qdrant must contain indexed chunks. If the collection is missing or empty, the runner still writes a report, but the quality gate will fail.

## Run Retrieval Eval

Run inside the API container:

```bash
docker compose exec -T api env PYTHONPATH=/app python scripts/eval_retrieval.py \
  --queries reports/retrieval_eval_dataset.json \
  --top-k 5 \
  --report-dir reports \
  --min-recall 0.6 \
  --min-mrr 0.3
```

Expected output behavior:

- A timestamped report is written to `reports/retrieval_eval_YYYYMMDD_HHMMSS.json`.
- Exit code `0` means the configured quality gate passed.
- Exit code `2` means `Recall@k` or `MRR@k` is below the gate.

Read these fields first:

- `metrics.recall_at_k`: share of scored queries with at least one expected hit in top-k.
- `metrics.mrr_at_k`: mean reciprocal rank of the first expected hit.
- `metrics.latency_p50_ms` and `metrics.latency_p95_ms`: retrieval latency trend.
- `results[].rank` and `results[].top_hits`: per-query debugging detail.

If every query misses and logs mention a missing Qdrant collection, ingest representative URLs first, then rerun the eval.

## Run Manual Refresh

Manual refresh is exposed through the API:

```bash
curl -X POST http://localhost:8000/api/ingest/refresh \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "source_id": 1,
    "url": "https://example.com/article",
    "operation_id": "op-refresh-manual-001",
    "compliance_confirmed": true,
    "compliance_reason": "scheduled refresh verification"
  }'
```

The URL must already have been ingested once. Refresh reuses the ingest pipeline and replaces the existing document/chunks for the same `source_id` and URL, so repeated runs should not create duplicate documents or chunks.

## Run Stale Refresh Job

Run the cron-like job once inside the API container:

```bash
docker compose exec -T api env PYTHONPATH=/app python scripts/refresh_stale.py
```

Expected output is JSON:

```json
{
  "total": 0,
  "status_counts": {},
  "incident_types": {}
}
```

Meaning:

- `total`: stale URLs selected for this run.
- `status_counts`: count by refresh outcome, for example `completed`, `failed`, `blocked_captcha`, or `skipped_running`.
- `incident_types`: operational incident counts, currently `failed` and `blocked_captcha`.

## Audit and Troubleshooting

Refresh batch runs write `audit_logs.action = "refresh.batch"` with:

- `trigger`
- `batch_size`
- `operation_id`
- `status_counts`
- `incident_types`
- per-URL summaries

Manual refresh through the API also writes `refresh.completed`, `refresh.skipped`, or `refresh.failed`.

Common cases:

- Missing Qdrant collection during eval: no data has been indexed for the configured `QDRANT_COLLECTION`.
- `blocked_captcha`: evidence and incident were recorded, but the page was not indexed.
- `failed`: inspect the matching incident/audit metadata and the API logs for parser, fetch, render, or policy errors.
