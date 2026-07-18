from __future__ import annotations

import numpy as np
import pandas as pd


DEFAULT_WEIGHTS = {
    "pickup_count": 0.22,
    "dropoff_count": 0.18,
    "late_pickup_ratio": 0.16,
    "weekend_boost": 0.14,
    "activity_persistence": 0.16,
    "short_trip_ratio": 0.08,
    "max_hourly_activity": 0.06,
}


def robust_minmax(series: pd.Series) -> pd.Series:
    values = pd.to_numeric(series, errors="coerce").fillna(0)
    lower = values.quantile(0.05)
    upper = values.quantile(0.95)
    clipped = values.clip(lower, upper)
    span = upper - lower
    if span == 0:
        return pd.Series(np.zeros(len(values)), index=values.index)
    return (clipped - lower) / span


def score_regions(features: pd.DataFrame, weights: dict[str, float] | None = None) -> pd.DataFrame:
    weights = weights or DEFAULT_WEIGHTS
    scored = features.copy()
    score = pd.Series(np.zeros(len(scored)), index=scored.index, dtype=float)
    for column, weight in weights.items():
        if column in scored:
            score += robust_minmax(scored[column]) * weight
    scored["night_vitality_score"] = (score * 100).round(2)
    return scored.sort_values("night_vitality_score", ascending=False).reset_index(drop=True)
