from __future__ import annotations

import numpy as np
import pandas as pd

from .schema import NightWindow

try:
    import h3
except ImportError:  # pragma: no cover - h3 is optional for non-H3 runs.
    h3 = None


def clean_trips(df: pd.DataFrame) -> pd.DataFrame:
    """Remove records that cannot produce meaningful night activity features."""
    cleaned = df.copy()
    cleaned = cleaned.dropna(subset=["start_time"])

    if "duration_min" in cleaned:
        cleaned = cleaned[(cleaned["duration_min"].isna()) | ((cleaned["duration_min"] >= 1) & (cleaned["duration_min"] <= 240))]
    if "distance" in cleaned:
        cleaned = cleaned[(cleaned["distance"].isna()) | ((cleaned["distance"] >= 0) & (cleaned["distance"] <= 200))]
    if "price" in cleaned:
        cleaned = cleaned[(cleaned["price"].isna()) | ((cleaned["price"] >= 0) & (cleaned["price"] <= 1000))]

    has_zone = cleaned["start_zone"].notna()
    has_coordinates = cleaned["start_lat"].notna() & cleaned["start_lon"].notna()
    cleaned = cleaned[has_zone | has_coordinates]
    return cleaned.reset_index(drop=True)


def filter_night_trips(df: pd.DataFrame, window: NightWindow) -> pd.DataFrame:
    night = df.copy()
    hours = night["start_time"].dt.hour
    night = night[window.contains_hours(hours)].copy()
    night["hour"] = night["start_time"].dt.hour
    night["day_of_week"] = night["start_time"].dt.dayofweek
    night["is_weekend"] = night["day_of_week"].isin([4, 5, 6])
    night["night_date"] = np.where(
        night["hour"] < window.end_hour,
        (night["start_time"] - pd.Timedelta(days=1)).dt.date,
        night["start_time"].dt.date,
    )
    return night.reset_index(drop=True)


def _h3_cell(lat: float | int | None, lon: float | int | None, resolution: int) -> str | pd.NA:
    if h3 is None or pd.isna(lat) or pd.isna(lon):
        return pd.NA
    return h3.latlng_to_cell(float(lat), float(lon), resolution)


def assign_spatial_units(
    df: pd.DataFrame,
    grid_size: float = 0.005,
    spatial_unit_type: str = "h3",
    h3_resolution: int = 8,
) -> pd.DataFrame:
    """Assign city-independent spatial units.

    H3 cells are the default for the Beijing T-Drive workflow. Latitude/longitude
    grids are available as a lightweight fallback.
    """
    assigned = df.copy()
    unit_type = (spatial_unit_type or "h3").lower()
    if unit_type == "h3" and h3 is None:
        raise RuntimeError("h3 is required when spatial_unit_type='h3'. Install h3 or use spatial_unit_type='grid'.")

    start_zone = assigned["start_zone"].astype("string")
    end_zone = assigned["end_zone"].astype("string")

    start_grid = (
        (assigned["start_lat"] / grid_size).round().astype("Int64").astype("string")
        + "_"
        + (assigned["start_lon"] / grid_size).round().astype("Int64").astype("string")
    )
    end_grid = (
        (assigned["end_lat"] / grid_size).round().astype("Int64").astype("string")
        + "_"
        + (assigned["end_lon"] / grid_size).round().astype("Int64").astype("string")
    )

    if unit_type == "h3":
        start_h3 = assigned.apply(lambda row: _h3_cell(row.get("start_lat"), row.get("start_lon"), h3_resolution), axis=1)
        end_h3 = assigned.apply(lambda row: _h3_cell(row.get("end_lat"), row.get("end_lon"), h3_resolution), axis=1)
        assigned["pickup_unit"] = start_h3.astype("string").where(pd.Series(start_h3).notna(), start_grid)
        assigned["dropoff_unit"] = end_h3.astype("string").where(pd.Series(end_h3).notna(), end_grid)
    elif unit_type == "grid":
        assigned["pickup_unit"] = start_grid
        assigned["dropoff_unit"] = end_grid
    else:
        assigned["pickup_unit"] = start_zone.where(start_zone.notna(), start_grid)
        assigned["dropoff_unit"] = end_zone.where(end_zone.notna(), end_grid)

    assigned["pickup_unit"] = assigned["pickup_unit"].fillna("unknown")
    assigned["dropoff_unit"] = assigned["dropoff_unit"].fillna("unknown")
    return assigned
