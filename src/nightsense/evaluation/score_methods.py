from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.decomposition import PCA
from sklearn.preprocessing import MinMaxScaler, StandardScaler

from nightsense.core.scoring import DEFAULT_WEIGHTS, robust_minmax


SCORE_FEATURES = [
    "pickup_count",
    "dropoff_count",
    "late_pickup_ratio",
    "weekend_boost",
    "activity_persistence",
    "short_trip_ratio",
    "max_hourly_activity",
]


def read_scores(output: Path) -> pd.DataFrame:
    phase2 = output / "region_scores_phase2.csv"
    if phase2.exists():
        return pd.read_csv(phase2)
    return pd.read_csv(output / "region_scores.csv")


def feature_matrix(scores: pd.DataFrame) -> pd.DataFrame:
    usable = [column for column in SCORE_FEATURES if column in scores.columns]
    return scores[usable].replace([np.inf, -np.inf], 0).fillna(0).astype(float)


def entropy_weights(matrix: pd.DataFrame) -> dict[str, float]:
    normalized = matrix.apply(robust_minmax).clip(lower=0)
    totals = normalized.sum(axis=0).replace(0, np.nan)
    proportions = normalized.divide(totals, axis=1).fillna(0)
    n = len(normalized)
    if n <= 1:
        return {column: 1 / len(matrix.columns) for column in matrix.columns}
    entropy = -(proportions * np.log(proportions.replace(0, np.nan))).sum(axis=0).fillna(0) / np.log(n)
    diversity = 1 - entropy
    if float(diversity.sum()) == 0:
        return {column: 1 / len(matrix.columns) for column in matrix.columns}
    weights = diversity / diversity.sum()
    return {column: float(weight) for column, weight in weights.items()}


def weighted_score(matrix: pd.DataFrame, weights: dict[str, float]) -> pd.Series:
    score = pd.Series(np.zeros(len(matrix)), index=matrix.index, dtype=float)
    for column, weight in weights.items():
        score += robust_minmax(matrix[column]) * weight
    return (score * 100).round(2)


def pca_score(matrix: pd.DataFrame) -> pd.Series:
    scaled = StandardScaler().fit_transform(matrix)
    component = PCA(n_components=1, random_state=42).fit_transform(scaled).ravel()
    score = MinMaxScaler(feature_range=(0, 100)).fit_transform(component.reshape(-1, 1)).ravel()
    if np.corrcoef(score, matrix["pickup_count"].to_numpy())[0, 1] < 0:
        score = 100 - score
    return pd.Series(score, index=matrix.index).round(2)


def build_score_method_comparison(output_dir: str | Path) -> pd.DataFrame:
    output = Path(output_dir)
    scores = read_scores(output)
    matrix = feature_matrix(scores)
    manual_weights = {column: DEFAULT_WEIGHTS.get(column, 0) for column in matrix.columns}
    manual_total = sum(manual_weights.values()) or 1
    manual_weights = {column: weight / manual_total for column, weight in manual_weights.items()}
    entropy = entropy_weights(matrix)

    comparison = scores[["spatial_unit", "region_type"]].copy()
    for name in ["zone", "borough", "Zone", "Borough"]:
        if name in scores.columns:
            comparison[name] = scores[name]
    comparison["manual_score"] = weighted_score(matrix, manual_weights)
    comparison["entropy_score"] = weighted_score(matrix, entropy)
    comparison["pca_score"] = pca_score(matrix)
    comparison["score_spread"] = (
        comparison[["manual_score", "entropy_score", "pca_score"]].max(axis=1)
        - comparison[["manual_score", "entropy_score", "pca_score"]].min(axis=1)
    )
    comparison["manual_rank"] = comparison["manual_score"].rank(ascending=False, method="min").astype(int)
    comparison["entropy_rank"] = comparison["entropy_score"].rank(ascending=False, method="min").astype(int)
    comparison["pca_rank"] = comparison["pca_score"].rank(ascending=False, method="min").astype(int)
    comparison = comparison.sort_values("manual_rank").reset_index(drop=True)
    comparison.to_csv(output / "score_method_comparison.csv", index=False)

    weight_summary = {
        "manual": manual_weights,
        "entropy": entropy,
        "pca": {"first_component": "standardized composite vitality axis"},
    }
    (output / "score_method_weights.json").write_text(json.dumps(weight_summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return comparison

