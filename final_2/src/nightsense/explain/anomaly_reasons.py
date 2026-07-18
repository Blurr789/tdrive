from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd


def zone_lookup(output: Path) -> dict[str, dict[str, Any]]:
    geojson_path = output / "region_scores_geojson_phase2.json"
    if not geojson_path.exists():
        geojson_path = output / "region_scores_geojson.json"
    if not geojson_path.exists():
        return {}
    data = json.loads(geojson_path.read_text(encoding="utf-8"))
    lookup = {}
    for feature in data.get("features", []):
        properties = feature.get("properties", {}) or {}
        spatial_unit = properties.get("spatial_unit")
        if spatial_unit is not None:
            lookup[str(spatial_unit)] = properties
    return lookup


def reason_for_anomaly(row: pd.Series, properties: dict[str, Any]) -> str:
    zone = str(properties.get("zone") or properties.get("Zone") or "")
    region_type = str(properties.get("region_type") or "")
    hour = int(row.get("hour", 0))
    activity = float(row.get("activity_count", 0) or 0)
    baseline = float(row.get("baseline_median", 0) or 0)
    is_weekend = bool(row.get("is_weekend", False))

    if properties.get("is_transport_hub"):
        return "可能与机场、车站或交通枢纽的集中到发有关。"
    if any(keyword in zone.lower() for keyword in ["garden", "square", "theater", "theatre", "stadium", "arena"]):
        return "可能与演出、赛事或大型场馆活动散场有关。"
    if is_weekend and hour in [22, 23, 0, 1, 2] and "nightlife" in region_type:
        return "可能与周末夜间活动高峰有关。"
    if activity >= baseline * 3 and baseline > 0:
        return "活动量显著高于同网格同小时历史基线，可能存在短时事件或局部需求激增。"
    if hour in [0, 1, 2]:
        return "凌晨时段仍出现异常高活动，可能与夜间返程、交通接驳或局部活动结束有关。"
    return "活动量偏离历史基线，建议结合当天活动、天气或交通信息进一步核查。"


def build_anomaly_attribution(output_dir: str | Path) -> pd.DataFrame:
    output = Path(output_dir)
    path = output / "anomalies.csv"
    if not path.exists():
        return pd.DataFrame()
    anomalies = pd.read_csv(path)
    lookup = zone_lookup(output)
    reasons = []
    for _, row in anomalies.iterrows():
        properties = lookup.get(str(row.get("spatial_unit")), {})
        reasons.append(reason_for_anomaly(row, properties))
    anomalies = anomalies.copy()
    anomalies["possible_reason"] = reasons
    anomalies.to_csv(output / "anomalies_attributed.csv", index=False)
    return anomalies
