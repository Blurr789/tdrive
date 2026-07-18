from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import pandas as pd


class OutputStore:
    def __init__(self, output_dir: str | Path):
        self.output_dir = Path(output_dir).resolve()

    def read_csv(self, name: str) -> pd.DataFrame:
        path = self.output_dir / name
        if not path.exists():
            return pd.DataFrame()
        return pd.read_csv(path)

    def read_json(self, name: str) -> dict[str, Any]:
        path = self.output_dir / name
        if not path.exists():
            return {}
        return json.loads(path.read_text(encoding="utf-8"))

    @staticmethod
    def json_safe(value: Any) -> Any:
        if value is None:
            return None
        if value is pd.NA:
            return None
        if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
            return None
        if isinstance(value, dict):
            return {key: OutputStore.json_safe(item) for key, item in value.items()}
        if isinstance(value, list):
            return [OutputStore.json_safe(item) for item in value]
        return value

    def dataframe_records(self, table: pd.DataFrame) -> list[dict[str, Any]]:
        if table.empty:
            return []
        clean = table.astype(object).where(pd.notnull(table), None)
        return self.json_safe(clean.to_dict(orient="records"))

    def geojson_filename(self, spatial_unit_type: str | None = None, phase2: bool = True) -> str:
        unit = (spatial_unit_type or "h3").lower()
        if unit == "h3":
            return "h3_region_scores_geojson.json"
        if phase2 and (self.output_dir / "region_scores_geojson_phase2.json").exists():
            return "region_scores_geojson_phase2.json"
        return "region_scores_geojson.json"

    def scores_filename(self) -> str:
        if (self.output_dir / "region_scores_phase2.csv").exists():
            return "region_scores_phase2.csv"
        return "region_scores.csv"

    def anomalies_filename(self) -> str:
        if (self.output_dir / "anomalies_attributed.csv").exists():
            return "anomalies_attributed.csv"
        return "anomalies.csv"

    def grid_name_lookup(self) -> dict[str, dict[str, Any]]:
        table = self.read_csv("grid_name_lookup.csv")
        if table.empty or "spatial_unit" not in table.columns:
            return {}
        table = table.copy()
        table["spatial_unit"] = table["spatial_unit"].astype(str)
        clean = table.astype(object).where(pd.notnull(table), None)
        return clean.set_index("spatial_unit").to_dict(orient="index")

    def zone_lookup(self) -> dict[str, dict[str, Any]]:
        geojson_path = self.output_dir / self.geojson_filename(phase2=True)
        lookup = {}
        if geojson_path.exists():
            data = json.loads(geojson_path.read_text(encoding="utf-8"))
            for feature in data.get("features", []):
                properties = feature.get("properties", {}) or {}
                spatial_unit = properties.get("spatial_unit")
                if spatial_unit is not None:
                    lookup[str(spatial_unit)] = {
                        "zone": properties.get("zone") or properties.get("Zone"),
                        "borough": properties.get("borough") or properties.get("Borough"),
                    }
        for spatial_unit, names in self.grid_name_lookup().items():
            lookup[str(spatial_unit)] = {**lookup.get(str(spatial_unit), {}), **names}
        return lookup

    def enrich_geojson(self, data: dict[str, Any]) -> dict[str, Any]:
        lookup = self.grid_name_lookup()
        if not lookup:
            return data
        for feature in data.get("features", []):
            properties = feature.get("properties", {}) or {}
            spatial_unit = properties.get("spatial_unit")
            if spatial_unit is None:
                continue
            names = lookup.get(str(spatial_unit))
            if not names:
                continue
            for key in [
                "zone",
                "borough",
                "display_name",
                "district",
                "township",
                "business_area",
                "nearest_aoi",
                "nearest_poi",
                "adcode",
                "name_source",
                "name_confidence",
            ]:
                if names.get(key) is not None:
                    properties[key] = names.get(key)
            feature["properties"] = properties
        return data

    def enrich_regions(self, scores: pd.DataFrame) -> pd.DataFrame:
        if scores.empty:
            return scores
        lookup = self.zone_lookup()
        scores = scores.copy()
        scores["spatial_unit"] = scores["spatial_unit"].astype(str)
        for column in [
            "zone",
            "borough",
            "display_name",
            "district",
            "township",
            "business_area",
            "nearest_aoi",
            "nearest_poi",
            "adcode",
            "name_source",
            "name_confidence",
        ]:
            scores[column] = scores["spatial_unit"].map(lambda value, key=column: lookup.get(value, {}).get(key))
        return scores

    def enrich_anomalies(self, anomalies: pd.DataFrame) -> pd.DataFrame:
        if anomalies.empty:
            return anomalies
        lookup = self.zone_lookup()
        enriched = anomalies.copy()
        enriched["spatial_unit"] = enriched["spatial_unit"].astype(str)
        for column in [
            "zone",
            "borough",
            "display_name",
            "district",
            "township",
            "business_area",
            "nearest_aoi",
            "nearest_poi",
            "adcode",
            "name_source",
            "name_confidence",
        ]:
            enriched[column] = enriched["spatial_unit"].map(lambda value, key=column: lookup.get(value, {}).get(key))
        enriched["display_name"] = enriched.apply(
            lambda row: (
                row["display_name"]
                if pd.notnull(row.get("display_name"))
                else f"{row['zone']}, {row['borough']}"
                if pd.notnull(row.get("zone")) and pd.notnull(row.get("borough"))
                else f"活动网格 {row['spatial_unit']}"
            ),
            axis=1,
        )
        return enriched

    def build_hourly_geojson(self, hour: int) -> dict[str, Any]:
        geojson_path = self.output_dir / "region_scores_geojson.json"
        if not geojson_path.exists():
            return {"type": "FeatureCollection", "features": []}

        data = json.loads(geojson_path.read_text(encoding="utf-8"))
        activity = self.read_csv("hourly_activity.csv")
        if activity.empty:
            return data

        activity = activity[activity["hour"].astype(int) == int(hour)]
        grouped = (
            activity.groupby("spatial_unit", as_index=False)
            .agg(
                hour_pickup_count=("pickup_count", "sum"),
                hour_dropoff_count=("dropoff_count", "sum"),
                hour_activity_count=("activity_count", "sum"),
            )
        )
        grouped["spatial_unit"] = grouped["spatial_unit"].astype(str)
        hourly_map = grouped.set_index("spatial_unit").to_dict(orient="index")
        max_activity = float(grouped["hour_activity_count"].max()) if not grouped.empty else 0.0

        for feature in data.get("features", []):
            properties = feature.get("properties", {}) or {}
            spatial_unit = str(properties.get("spatial_unit"))
            row = hourly_map.get(spatial_unit, {})
            properties["hour"] = int(hour)
            properties["hour_pickup_count"] = int(row.get("hour_pickup_count", 0) or 0)
            properties["hour_dropoff_count"] = int(row.get("hour_dropoff_count", 0) or 0)
            properties["hour_activity_count"] = int(row.get("hour_activity_count", 0) or 0)
            properties["score_ratio"] = properties["hour_activity_count"] / max_activity if max_activity else 0
            feature["properties"] = properties

        return self.enrich_geojson(data)

    def build_h3_hourly_geojson(self, hour: int) -> dict[str, Any]:
        geojson_path = self.output_dir / "h3_region_scores_geojson.json"
        if not geojson_path.exists():
            return {"type": "FeatureCollection", "features": []}

        data = json.loads(geojson_path.read_text(encoding="utf-8"))
        activity = self.read_csv("hourly_activity.csv")
        if activity.empty:
            return data

        activity = activity[activity["hour"].astype(int) == int(hour)]
        grouped = (
            activity.groupby("spatial_unit", as_index=False)
            .agg(
                hour_pickup_count=("pickup_count", "sum"),
                hour_dropoff_count=("dropoff_count", "sum"),
                hour_activity_count=("activity_count", "sum"),
            )
        )
        grouped["spatial_unit"] = grouped["spatial_unit"].astype(str)
        hourly_map = grouped.set_index("spatial_unit").to_dict(orient="index")
        max_activity = float(grouped["hour_activity_count"].max()) if not grouped.empty else 0.0

        for feature in data.get("features", []):
            properties = feature.get("properties", {}) or {}
            h3_unit = str(properties.get("spatial_unit"))
            source_unit = str(properties.get("source_spatial_unit") or "")
            row = hourly_map.get(h3_unit, hourly_map.get(source_unit, {}))
            properties["hour"] = int(hour)
            properties["hour_pickup_count"] = int(row.get("hour_pickup_count", 0) or 0)
            properties["hour_dropoff_count"] = int(row.get("hour_dropoff_count", 0) or 0)
            properties["hour_activity_count"] = int(row.get("hour_activity_count", 0) or 0)
            properties["score_ratio"] = properties["hour_activity_count"] / max_activity if max_activity else 0
            feature["properties"] = properties

        return self.enrich_geojson(data)
