from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

try:
    import h3
except ImportError:  # pragma: no cover - handled by validation in H3 builds.
    h3 = None


def _json_safe(value: Any) -> Any:
    if pd.isna(value):
        return None
    if hasattr(value, "item"):
        return value.item()
    return value


def _h3_polygon(cell: str) -> list[list[float]]:
    if h3 is None:
        raise RuntimeError("h3 is required to build H3 GeoJSON output.")
    boundary = h3.cell_to_boundary(cell)
    polygon = [[float(lng), float(lat)] for lat, lng in boundary]
    polygon.append(polygon[0])
    return polygon


def _grid_polygon(spatial_unit: str, grid_size: float) -> list[list[float]]:
    lat_index_text, lon_index_text = spatial_unit.split("_", maxsplit=1)
    lat_center = int(lat_index_text) * grid_size
    lon_center = int(lon_index_text) * grid_size
    half = grid_size / 2
    return [
        [lon_center - half, lat_center - half],
        [lon_center + half, lat_center - half],
        [lon_center + half, lat_center + half],
        [lon_center - half, lat_center + half],
        [lon_center - half, lat_center - half],
    ]


def _feature_properties(row: pd.Series, spatial_unit_type: str, max_score: float) -> dict[str, Any]:
    properties = {key: _json_safe(value) for key, value in row.to_dict().items()}
    spatial_unit = str(row.get("spatial_unit"))
    properties["spatial_unit"] = spatial_unit
    properties["spatial_unit_type"] = spatial_unit_type
    properties["zone"] = properties.get("zone") or f"活动网格 {spatial_unit}"
    properties["borough"] = properties.get("borough") or "Beijing"
    properties["score_ratio"] = (
        float(row.get("night_vitality_score", 0) or 0) / max_score if max_score else 0
    )
    return properties


def build_spatial_unit_geojson(
    region_scores_csv: str | Path,
    output_geojson: str | Path,
    spatial_unit_type: str = "h3",
    grid_size: float = 0.005,
    h3_geojson_output: str | Path | None = None,
    h3_scores_output: str | Path | None = None,
) -> dict[str, Any]:
    """Build GeoJSON directly from scored H3 or grid spatial units."""
    scores = pd.read_csv(region_scores_csv)
    unit_type = (spatial_unit_type or "h3").lower()
    if unit_type == "h3" and h3 is None:
        raise RuntimeError("h3 is required to build H3 GeoJSON output.")

    if scores.empty:
        geojson = {
            "type": "FeatureCollection",
            "name": f"urban_nightsense_{unit_type}_regions",
            "features": [],
        }
    else:
        scores["spatial_unit"] = scores["spatial_unit"].astype(str)
        max_score = float(scores["night_vitality_score"].max()) if "night_vitality_score" in scores else 0.0
        features = []

        for _, row in scores.iterrows():
            spatial_unit = str(row["spatial_unit"])
            if spatial_unit == "unknown":
                continue

            try:
                polygon = _h3_polygon(spatial_unit) if unit_type == "h3" else _grid_polygon(spatial_unit, grid_size)
            except (ValueError, RuntimeError):
                continue

            features.append(
                {
                    "type": "Feature",
                    "geometry": {"type": "Polygon", "coordinates": [polygon]},
                    "properties": _feature_properties(row, unit_type, max_score),
                }
            )

        geojson = {
            "type": "FeatureCollection",
            "name": f"urban_nightsense_{unit_type}_regions",
            "features": features,
        }

    output = Path(output_geojson)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(geojson, ensure_ascii=False), encoding="utf-8")

    if (spatial_unit_type or "").lower() == "h3":
        if h3_geojson_output is not None:
            target = Path(h3_geojson_output)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(json.dumps(geojson, ensure_ascii=False), encoding="utf-8")
        if h3_scores_output is not None:
            scores.to_csv(h3_scores_output, index=False)

    return geojson
