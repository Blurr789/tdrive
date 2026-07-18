from __future__ import annotations

import pandas as pd


def detect_anomalies(activity: pd.DataFrame, min_activity: int = 20, z_threshold: float = 3.5) -> pd.DataFrame:
    """Detect abnormal region-hour activity against robust same-hour baselines."""
    if activity.empty:
        return activity.assign(z_score=pd.Series(dtype=float), is_anomaly=pd.Series(dtype=bool))

    baseline = (
        activity.groupby(["spatial_unit", "hour"])["activity_count"]
        .agg(
            baseline_median="median",
            baseline_mean="mean",
            sample_size="count",
        )
        .reset_index()
    )
    detected = activity.merge(baseline, on=["spatial_unit", "hour"], how="left")

    deviations = (detected["activity_count"] - detected["baseline_median"]).abs()
    detected["_abs_deviation"] = deviations
    mad = (
        detected.groupby(["spatial_unit", "hour"])["_abs_deviation"]
        .median()
        .rename("baseline_mad")
        .reset_index()
    )
    detected = detected.merge(mad, on=["spatial_unit", "hour"], how="left")
    robust_std = 1.4826 * detected["baseline_mad"]
    detected["z_score"] = ((detected["activity_count"] - detected["baseline_median"]) / robust_std.replace(0, pd.NA)).fillna(0)
    fallback_spike = (detected["baseline_mad"] == 0) & (detected["activity_count"] >= detected["baseline_median"] * 2.5 + min_activity)
    detected["is_anomaly"] = (detected["activity_count"] >= min_activity) & (detected["z_score"] >= z_threshold)
    detected["is_anomaly"] = detected["is_anomaly"] | fallback_spike
    detected = detected.drop(columns=["_abs_deviation"])
    return detected[detected["is_anomaly"]].sort_values("z_score", ascending=False).reset_index(drop=True)
