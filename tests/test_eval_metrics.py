from app.services.eval_metrics import mrr_at_k, percentile, recall_at_k


def test_recall_at_k():
    assert recall_at_k([True, False, True]) == 2 / 3
    assert recall_at_k([]) is None


def test_mrr_at_k():
    assert mrr_at_k([1, None, 2]) == (1 + 0 + 0.5) / 3
    assert mrr_at_k([]) is None


def test_percentile():
    assert percentile([10, 20, 30, 40], 0.5) == 20
    assert percentile([], 0.5) is None
