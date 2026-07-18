from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from .anomaly import detect_anomalies
from .clustering import cluster_regions
from .features import build_region_features, hourly_activity
from .io import load_trip_data, write_outputs
from .preprocess import assign_spatial_units, clean_trips, filter_night_trips
from .schema import NightWindow
from .scoring import score_regions


def run_pipeline(
    trips: pd.DataFrame,
    output_dir: str | Path,
    night_start: int = 20,
    night_end: int = 3,
    n_clusters: int = 5,
    spatial_unit_type: str = "h3",
    h3_resolution: int = 8,
    grid_size: float = 0.005,
) -> dict[str, pd.DataFrame]:
    window = NightWindow(start_hour=night_start, end_hour=night_end)
    cleaned = clean_trips(trips)
    night = filter_night_trips(cleaned, window)
    assigned = assign_spatial_units(
        night,
        grid_size=grid_size,
        spatial_unit_type=spatial_unit_type,
        h3_resolution=h3_resolution,
    )
    activity = hourly_activity(assigned)
    features = build_region_features(assigned, activity)
    scored = score_regions(features)
    clustered = cluster_regions(scored, n_clusters=n_clusters)
    anomalies = detect_anomalies(activity)

    output_path = Path(output_dir)
    write_outputs(
        output_path,
        night_trips=assigned,
        hourly_activity=activity,
        region_features=features,
        region_scores=clustered,
        anomalies=anomalies,
    )

    summary = {
        "input_rows": int(len(trips)),
        "clean_rows": int(len(cleaned)),
        "night_rows": int(len(assigned)),
        "region_count": int(len(clustered)),
        "anomaly_count": int(len(anomalies)),
        "spatial_unit_type": spatial_unit_type,
        "top_regions": clustered[["spatial_unit", "night_vitality_score", "region_type"]].head(10).to_dict("records"),
    }
    output_path.mkdir(parents=True, exist_ok=True)
    (output_path / "pipeline_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    return {
        "night_trips": assigned,
        "hourly_activity": activity,
        "region_features": features,
        "region_scores": clustered,
        "anomalies": anomalies,
    }


def run_from_file(
    input_path: str | Path,
    output_dir: str | Path,
    city: str,
    limit: int | None = None,
    night_start: int = 20,
    night_end: int = 3,
    n_clusters: int = 5,
    spatial_unit_type: str = "h3",
    h3_resolution: int = 8,
    grid_size: float = 0.005,
) -> dict[str, pd.DataFrame]:
    trips = load_trip_data(input_path, city=city, limit=limit)
    return run_pipeline(
        trips,
        output_dir=output_dir,
        night_start=night_start,
        night_end=night_end,
        n_clusters=n_clusters,
        spatial_unit_type=spatial_unit_type,
        h3_resolution=h3_resolution,
        grid_size=grid_size,
    )
