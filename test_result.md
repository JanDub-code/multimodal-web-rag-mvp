# Test results (2026-04-30)

## Summary
- ✅ `pytest tests/test_eval_metrics.py` – passed (run inside API container).
- ❌ `scripts/eval_retrieval.py` – failed (embedding backend unreachable from container).
- ✅ `scripts/refresh_stale.py` – passed (no stale URLs).

## Details

### 1) Eval metrics unit test
**Command:** `docker compose exec -T api pytest tests/test_eval_metrics.py`

**Result:** ✅ PASS

### 2) Retrieval eval runner
**Command:**
`docker compose exec -T api env PYTHONPATH=/app python scripts/eval_retrieval.py --queries reports/retrieval_eval_dataset.json --top-k 5 --report-dir reports --min-recall 0.6 --min-mrr 0.3`

**Result:** ❌ FAIL

**Output (excerpt):**
```
EmbeddingBackendError: Ollama embedding backend is not reachable at http://host.docker.internal:11434/api/embed.
```

### 3) Refresh stale runner
**Command:**
`docker compose exec -T api env PYTHONPATH=/app python scripts/refresh_stale.py`

**Result:** ✅ PASS

**Output (excerpt):**
```
{
  "total": 0,
  "status_counts": {},
  "incident_types": {}
}
```

## Notes
- Unit tests and refresh script were executed inside the API container after rebuilding and applying migrations.
- Retrieval eval failed because the embedding backend at `http://host.docker.internal:11434` is not reachable from the container (Ollama not running or not exposed).

## Files used
- `tests/test_eval_metrics.py` – unit test suite pro metriky (Recall/MRR/percentil).
- `app/services/eval_metrics.py` – implementace eval metrik, testovano pytestem.
- `scripts/eval_retrieval.py` – eval runner pro retrieval pipeline (Recall@k, MRR@k, latence).
- `reports/retrieval_eval_dataset.json` – vstupní eval dataset s CZ/EN dotazy a očekáváním.
- `scripts/refresh_stale.py` – cron-like spouštěč refresh workflow.
- `app/services/refresh.py` – logika refresh batch jobu a auditních záznamů.
- `app/services/retrieval.py` – retrieval pipeline použitý eval runnerem.
