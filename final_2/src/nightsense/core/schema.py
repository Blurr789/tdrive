from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import pandas as pd


CANONICAL_COLUMNS = [
    "trip_id",
    "city",
    "start_time",
    "end_time",
    "start_lat",
    "start_lon",
    "end_lat",
    "end_lon",
    "start_zone",
    "end_zone",
    "distance",
    "duration_min",
    "price",
    "vehicle_type",
]


@dataclass(frozen=True)
class NightWindow:
    start_hour: int = 20
    end_hour: int = 3

    def contains_hours(self, hours: pd.Series) -> pd.Series:
        if self.start_hour > self.end_hour:
            return (hours >= self.start_hour) | (hours < self.end_hour)
        return (hours >= self.start_hour) & (hours < self.end_hour)


def normalize_columns(df: pd.DataFrame, city: str = "Unknown") -> pd.DataFrame:
    """Normalize common trip schemas into the Urban NightSense canonical schema."""
    renamed = df.copy()
    if renamed.columns.duplicated().any():
        deduped = pd.DataFrame(index=renamed.index)
        for column in dict.fromkeys(renamed.columns):
            same_name = renamed.loc[:, renamed.columns == column]
            if isinstance(same_name, pd.Series) or same_name.shape[1] == 1:
                deduped[column] = same_name.iloc[:, 0] if isinstance(same_name, pd.DataFrame) else same_name
            else:
                deduped[column] = same_name.bfill(axis=1).iloc[:, 0]
        renamed = deduped

    for column in CANONICAL_COLUMNS:
        if column not in renamed.columns:
            renamed[column] = pd.NA

    renamed["city"] = renamed["city"].fillna(city)
    renamed["start_time"] = pd.to_datetime(renamed["start_time"], errors="coerce")
    renamed["end_time"] = pd.to_datetime(renamed["end_time"], errors="coerce")

    if renamed["trip_id"].isna().all():
        renamed["trip_id"] = range(1, len(renamed) + 1)

    if renamed["duration_min"].isna().all() and renamed["end_time"].notna().any():
        duration = renamed["end_time"] - renamed["start_time"]
        renamed["duration_min"] = duration.dt.total_seconds() / 60

    for column in ["start_lat", "start_lon", "end_lat", "end_lon", "distance", "duration_min", "price"]:
        renamed[column] = pd.to_numeric(renamed[column], errors="coerce")

    return renamed[CANONICAL_COLUMNS].copy()


def require_any(df: pd.DataFrame, column_groups: Iterable[Iterable[str]]) -> None:
    missing_groups = []
    for group in column_groups:
        if not any(column in df.columns and df[column].notna().any() for column in group):
            missing_groups.append(list(group))
    if missing_groups:
        raise ValueError(f"Input data is missing usable columns for: {missing_groups}")
