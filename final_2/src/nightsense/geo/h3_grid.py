from __future__ import annotations

import math
from typing import Any

import h3


def iter_positions(geometry: dict[str, Any]):
    geom_type = geometry.get("type")
    coordinates = geometry.get("coordinates") or []
    if geom_type == "Point":
        if len(coordinates) >= 2:
            yield coordinates
    elif geom_type in {"LineString", "MultiPoint"}:
        for position in coordinates:
            if len(position) >= 2:
                yield position
    elif geom_type in {"Polygon", "MultiLineString"}:
        for ring in coordinates:
            for position in ring:
                if len(position) >= 2:
                    yield position
    elif geom_type == "MultiPolygon":
        for polygon in coordinates:
            for ring in polygon:
                for position in ring:
                    if len(position) >= 2:
                        yield position


def geometry_centroid(geometry: dict[str, Any]) -> tuple[float, float] | None:
    positions = list(iter_positions(geometry))
    if not positions:
        return None
    lon = sum(float(position[0]) for position in positions) / len(positions)
    lat = sum(float(position[1]) for position in positions) / len(positions)
    if not math.isfinite(lat) or not math.isfinite(lon):
        return None
    return lat, lon


def h3_feature_from_centroid(
    centroid: tuple[float, float],
    resolution: int,
    properties: dict[str, Any],
    source_spatial_unit: str,
    source_zone: str,
) -> dict[str, Any]:
    lat, lon = centroid
    h3_cell = h3.latlng_to_cell(lat, lon, resolution)
    boundary = h3.cell_to_boundary(h3_cell)
    polygon = [[float(lng), float(lat)] for lat, lng in boundary]
    polygon.append(polygon[0])

    h3_properties = dict(properties)
    h3_properties["spatial_unit"] = h3_cell
    h3_properties["source_spatial_unit"] = source_spatial_unit
    h3_properties["source_zone"] = source_zone
    h3_properties["spatial_unit_type"] = "h3"
    return {
        "type": "Feature",
        "geometry": {"type": "Polygon", "coordinates": [polygon]},
        "properties": h3_properties,
    }
