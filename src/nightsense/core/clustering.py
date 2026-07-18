from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler


CLUSTER_FEATURES = [
    "pickup_count",
    "dropoff_count",
    "late_pickup_ratio",
    "weekend_boost",
    "activity_persistence",
    "short_trip_ratio",
    "inflow_outflow_balance",
    "avg_distance",
]


def cluster_regions(scored: pd.DataFrame, n_clusters: int = 5, random_state: int = 42) -> pd.DataFrame:
    clustered = scored.copy()
    usable = [column for column in CLUSTER_FEATURES if column in clustered.columns]
    if len(clustered) < 2 or not usable:
        clustered["cluster_id"] = 0
        clustered["region_type"] = "insufficient_data"
        return clustered

    k = min(n_clusters, len(clustered))
    matrix = clustered[usable].replace([np.inf, -np.inf], 0).fillna(0)
    matrix = StandardScaler().fit_transform(matrix)
    labels = KMeans(n_clusters=k, random_state=random_state, n_init="auto").fit_predict(matrix)
    clustered["cluster_id"] = labels
    clustered["region_type"] = label_clusters(clustered)
    return clustered


def label_clusters(df: pd.DataFrame) -> pd.Series:
    summary = (
        df.groupby("cluster_id")
        .agg(
            score=("night_vitality_score", "mean"),
            late=("late_pickup_ratio", "mean"),
            weekend=("weekend_boost", "mean"),
            balance=("inflow_outflow_balance", "mean"),
            distance=("avg_distance", "mean"),
            total=("total_activity", "mean"),
        )
    )

    highest_score = summary["score"].idxmax()
    longest_distance = summary["distance"].idxmax()
    strongest_inflow = summary["balance"].idxmax()
    strongest_outflow = summary["balance"].idxmin()

    labels = {}
    for cluster_id, row in summary.iterrows():
        if cluster_id == highest_score:
            labels[cluster_id] = "nightlife_core"
        elif cluster_id == longest_distance and row["distance"] > summary["distance"].median():
            labels[cluster_id] = "transport_hub_like"
        elif cluster_id == strongest_inflow and row["balance"] > 0.15:
            labels[cluster_id] = "return_destination"
        elif cluster_id == strongest_outflow and row["balance"] < -0.15:
            labels[cluster_id] = "departure_hotspot"
        elif row["score"] < summary["score"].median():
            labels[cluster_id] = "low_activity"
        else:
            labels[cluster_id] = "mixed_evening_area"

    return df["cluster_id"].map(labels)
