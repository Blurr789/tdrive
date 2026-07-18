from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from nightsense.agents.schemas import anomaly_event_id


class AnomalyContextBuilder:
    def __init__(self, output_dir: str | Path):
        self.output_dir = Path(output_dir)

    def _read_csv(self, name: str) -> pd.DataFrame:
        path = self.output_dir / name
        if not path.exists():
            return pd.DataFrame()
        return pd.read_csv(path)

    def _read_json(self, name: str) -> dict[str, Any]:
        path = self.output_dir / name
        if not path.exists():
            return {}
        return json.loads(path.read_text(encoding="utf-8"))

    def _anomalies(self) -> pd.DataFrame:
        attributed = self.output_dir / "anomalies_attributed.csv"
        if attributed.exists():
            return pd.read_csv(attributed)
        return self._read_csv("anomalies.csv")

    def _scores(self) -> pd.DataFrame:
        phase2 = self.output_dir / "region_scores_phase2.csv"
        if phase2.exists():
            return pd.read_csv(phase2)
        return self._read_csv("region_scores.csv")

    def _zone_lookup(self) -> dict[str, dict[str, Any]]:
        geojson_name = "region_scores_geojson_phase2.json"
        if not (self.output_dir / geojson_name).exists():
            geojson_name = "region_scores_geojson.json"
        data = self._read_json(geojson_name)
        lookup = {}
        for feature in data.get("features", []):
            properties = feature.get("properties", {}) or {}
            spatial_unit = properties.get("spatial_unit")
            if spatial_unit is not None:
                lookup[str(spatial_unit)] = properties
        return lookup

    def _row_to_dict(self, row: pd.Series | None) -> dict[str, Any]:
        if row is None:
            return {}
        data = row.to_dict()
        return {key: self._json_safe(value) for key, value in data.items()}

    def _json_safe(self, value: Any) -> Any:
        if pd.isna(value):
            return None
        if hasattr(value, "item"):
            try:
                return value.item()
            except ValueError:
                return value
        return value

    def build(self, spatial_unit: str, night_date: str, hour: int | str) -> dict[str, Any]:
        spatial_unit = str(spatial_unit)
        hour_int = int(hour)
        anomalies = self._anomalies()
        if anomalies.empty:
            raise ValueError("anomalies data not found")

        anomalies["spatial_unit"] = anomalies["spatial_unit"].astype(str)
        match = anomalies[
            (anomalies["spatial_unit"] == spatial_unit)
            & (anomalies["night_date"].astype(str) == str(night_date))
            & (anomalies["hour"].astype(int) == hour_int)
        ]
        if match.empty:
            raise ValueError("anomaly event not found")

        event_row = match.iloc[0]
        scores = self._scores()
        score_row = None
        if not scores.empty:
            scores["spatial_unit"] = scores["spatial_unit"].astype(str)
            score_match = scores[scores["spatial_unit"] == spatial_unit]
            if not score_match.empty:
                score_row = score_match.iloc[0]

        zone_lookup = self._zone_lookup()
        zone = zone_lookup.get(spatial_unit, {})
        zone_name = zone.get("zone") or zone.get("Zone") or self._row_to_dict(score_row).get("zone") or f"区域 {spatial_unit}"
        borough = zone.get("borough") or zone.get("Borough") or self._row_to_dict(score_row).get("borough")
        hourly_context = self._hourly_context(spatial_unit, str(night_date), hour_int)
        explanations = self._read_json("region_explanations.json")

        return {
            "event_id": anomaly_event_id(spatial_unit, str(night_date), hour_int),
            "event": {
                **self._row_to_dict(event_row),
                "spatial_unit": spatial_unit,
                "zone": zone_name,
                "borough": borough,
                "display_name": f"{zone_name}, {borough}" if borough else zone_name,
            },
            "region_profile": self._row_to_dict(score_row),
            "zone_properties": {key: self._json_safe(value) for key, value in zone.items()},
            "hourly_context": hourly_context,
            "region_explanation": explanations.get(spatial_unit, {}),
        }

    def _hourly_context(self, spatial_unit: str, night_date: str, hour: int) -> dict[str, Any]:
        hourly = self._read_csv("hourly_activity.csv")
        if hourly.empty:
            return {}
        hourly["spatial_unit"] = hourly["spatial_unit"].astype(str)
        region = hourly[
            (hourly["spatial_unit"] == str(spatial_unit))
            & (hourly["night_date"].astype(str) == str(night_date))
        ].sort_values("hour")
        if region.empty:
            return {}
        previous_hour = (hour - 1) % 24
        next_hour = (hour + 1) % 24
        current = region[region["hour"].astype(int) == hour]
        previous = region[region["hour"].astype(int) == previous_hour]
        following = region[region["hour"].astype(int) == next_hour]
        return {
            "same_night_series": region[["hour", "activity_count", "pickup_count", "dropoff_count"]].to_dict(orient="records"),
            "current_hour": self._row_to_dict(current.iloc[0]) if not current.empty else {},
            "previous_hour": self._row_to_dict(previous.iloc[0]) if not previous.empty else {},
            "next_hour": self._row_to_dict(following.iloc[0]) if not following.empty else {},
        }

