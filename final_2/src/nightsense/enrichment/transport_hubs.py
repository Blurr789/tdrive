from __future__ import annotations

import pandas as pd

from .poi_features import keyword_score


HUB_KEYWORDS = [
    "airport",
    "jfk",
    "laguardia",
    "newark",
    "station",
    "terminal",
    "penn station",
    "grand central",
    "ferry",
    "port authority",
]


def infer_hub_features(row: pd.Series) -> dict[str, float | bool]:
    zone_name = str(row.get("zone") or row.get("Zone") or "")
    borough = str(row.get("borough") or row.get("Borough") or "")
    text = f"{zone_name} {borough}"
    keyword_hits = keyword_score(text, HUB_KEYWORDS)
    avg_distance = float(row.get("avg_distance", 0) or 0)
    avg_price = float(row.get("avg_price", 0) or 0)
    short_trip_ratio = float(row.get("short_trip_ratio", 0) or 0)
    long_trip_ratio = max(0.0, min(1.0, (avg_distance - 4) / 12))
    airport_like_score = min(1.0, keyword_hits * 0.45 + long_trip_ratio * 0.45 + max(0, avg_price - 35) / 100)
    station_like_score = min(
        1.0,
        (0.35 if "station" in text.lower() or "terminal" in text.lower() else 0)
        + long_trip_ratio * 0.35
        + short_trip_ratio * 0.15,
    )
    hub_penalty = round(max(airport_like_score, station_like_score) * 18, 2)
    return {
        "long_trip_ratio": round(long_trip_ratio, 4),
        "airport_like_score": round(airport_like_score, 4),
        "station_like_score": round(station_like_score, 4),
        "hub_penalty": hub_penalty,
        "is_transport_hub": bool(max(airport_like_score, station_like_score) >= 0.55 or keyword_hits >= 1),
    }

