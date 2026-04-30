from __future__ import annotations

import statistics
from typing import Iterable


def percentile(values: list[float], percentile_value: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, int((len(ordered) - 1) * percentile_value)))
    return ordered[index]


def recall_at_k(hit_flags: Iterable[bool]) -> float | None:
    flags = list(hit_flags)
    if not flags:
        return None
    return sum(1 for flag in flags if flag) / len(flags)


def mrr_at_k(ranks: Iterable[int | None]) -> float | None:
    values = []
    for rank in ranks:
        if rank is None or rank <= 0:
            values.append(0.0)
        else:
            values.append(1 / rank)
    return statistics.mean(values) if values else None
