from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from nightsense.enrichment.poi_features import infer_poi_features
from nightsense.enrichment.transport_hubs import infer_hub_features
from nightsense.geo.h3_grid import geometry_centroid, h3_feature_from_centroid


def read_json(path: str | Path) -> dict[str, Any]:
    source = Path(path)
    if not source.exists():
        return {"type": "FeatureCollection", "features": []}
    return json.loads(source.read_text(encoding="utf-8"))


def write_json(path: str | Path, data: dict[str, Any]) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


def load_amap_regeocode_cache(output: Path) -> dict[str, dict[str, Any]]:
    cache_path = output / "grid_name_lookup_raw.json"
    if not cache_path.exists():
        return {}
    raw = json.loads(cache_path.read_text(encoding="utf-8"))
    cache = {}
    for spatial_unit, response in raw.items():
        if isinstance(response, dict) and response.get("status") == "1":
            cache[str(spatial_unit)] = response.get("regeocode") or {}
    return cache


def build_phase2_outputs(
    output_dir: str | Path,
    h3_resolution: int = 8,
    scored_geojson_name: str = "region_scores_geojson.json",
) -> dict[str, Any]:
    output = Path(output_dir)
    geojson_path = output / scored_geojson_name
    scores_path = output / "region_scores.csv"
    if not geojson_path.exists() or not scores_path.exists():
        return {}

    geojson = read_json(geojson_path)
    scores = pd.read_csv(scores_path)
    scores["spatial_unit"] = scores["spatial_unit"].astype(str)
    score_map = scores.set_index("spatial_unit").to_dict(orient="index")
    amap_regeocode = load_amap_regeocode_cache(output)

    poi_rows = []
    hub_rows = []
    h3_features = []
    enriched_features = []

    for feature in geojson.get("features", []):
        properties = dict(feature.get("properties", {}) or {})
        spatial_unit = str(properties.get("spatial_unit"))
        row = pd.Series({**score_map.get(spatial_unit, {}), **properties})
        zone_name = str(properties.get("zone") or properties.get("Zone") or f"活动网格 {spatial_unit}")
        borough = properties.get("borough") or properties.get("Borough")
        poi = infer_poi_features(zone_name, borough, properties.get("Shape_Area"), amap_regeocode.get(spatial_unit))
        hub = infer_hub_features(row)

        adjusted_score = max(0.0, float(row.get("night_vitality_score", 0) or 0) - float(hub["hub_penalty"]))
        adjusted_type = "transport_hub_like" if hub["is_transport_hub"] else str(row.get("region_type", "no_activity"))

        poi_rows.append({"spatial_unit": spatial_unit, **poi})
        hub_rows.append({"spatial_unit": spatial_unit, **hub})

        enriched = dict(properties)
        enriched.update(poi)
        enriched.update(hub)
        enriched["adjusted_night_vitality_score"] = round(adjusted_score, 2)
        enriched["region_type"] = adjusted_type

        enriched_feature = dict(feature)
        enriched_feature["properties"] = enriched
        enriched_features.append(enriched_feature)

        centroid = geometry_centroid(feature.get("geometry") or {})
        if centroid:
            h3_features.append(h3_feature_from_centroid(centroid, h3_resolution, enriched, spatial_unit, zone_name))

    poi_features = pd.DataFrame(poi_rows)
    hub_features = pd.DataFrame(hub_rows)
    phase2_scores = scores.merge(poi_features, on="spatial_unit", how="left").merge(hub_features, on="spatial_unit", how="left")
    phase2_scores["adjusted_night_vitality_score"] = (
        phase2_scores["night_vitality_score"].astype(float) - phase2_scores["hub_penalty"].fillna(0).astype(float)
    ).clip(lower=0).round(2)
    phase2_scores.loc[phase2_scores["is_transport_hub"].fillna(False), "region_type"] = "transport_hub_like"

    poi_features.to_csv(output / "poi_features.csv", index=False)
    hub_features.to_csv(output / "hub_features.csv", index=False)
    phase2_scores.to_csv(output / "region_scores_phase2.csv", index=False)

    grid_phase2 = {
        "type": "FeatureCollection",
        "name": "urban_nightsense_activity_grids_phase2",
        "features": enriched_features,
    }
    h3_geojson = {
        "type": "FeatureCollection",
        "name": f"urban_nightsense_h3_r{h3_resolution}",
        "features": h3_features,
    }
    write_json(output / "region_scores_geojson_phase2.json", grid_phase2)
    write_json(output / "h3_region_scores_geojson.json", h3_geojson)
    if h3_features:
        pd.DataFrame([feature["properties"] for feature in h3_features]).to_csv(output / "h3_region_scores.csv", index=False)

    return {
        "poi_features": poi_features,
        "hub_features": hub_features,
        "phase2_scores": phase2_scores,
        "grid_geojson": grid_phase2,
        "h3_geojson": h3_geojson,
    }
