from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd


REGION_TYPE_LABELS = {
    "nightlife_core": "夜间活动核心区",
    "transport_hub_like": "交通枢纽型网格",
    "return_destination": "夜间到达热点",
    "departure_hotspot": "夜间出发热点",
    "mixed_evening_area": "混合夜间活动区",
    "low_activity": "低活跃区",
    "no_activity": "暂无活跃记录",
    "insufficient_data": "数据不足",
}


def load_zone_lookup(scored_geojson_path: str | Path) -> dict[str, dict[str, Any]]:
    path = Path(scored_geojson_path)
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    lookup = {}
    for feature in data.get("features", []):
        properties = feature.get("properties", {}) or {}
        spatial_unit = properties.get("spatial_unit")
        if spatial_unit is None:
            continue
        lookup[str(spatial_unit)] = {
            "zone": properties.get("zone") or properties.get("Zone"),
            "borough": properties.get("borough") or properties.get("Borough"),
        }
    return lookup


def percentile_rank(series: pd.Series, value: float) -> float:
    numeric = pd.to_numeric(series, errors="coerce").fillna(0)
    if numeric.empty:
        return 0.0
    return float((numeric <= value).mean() * 100)


def describe_region(row: pd.Series, features: pd.DataFrame, zone_name: str) -> list[str]:
    reasons = []
    pickup_pct = percentile_rank(features["pickup_count"], row.get("pickup_count", 0))
    dropoff_pct = percentile_rank(features["dropoff_count"], row.get("dropoff_count", 0))
    late_pct = percentile_rank(features["late_pickup_ratio"], row.get("late_pickup_ratio", 0))
    weekend_pct = percentile_rank(features["weekend_boost"], row.get("weekend_boost", 0))
    short_pct = percentile_rank(features["short_trip_ratio"], row.get("short_trip_ratio", 0))

    if pickup_pct >= 90:
        reasons.append(f"夜间活动起点数位于全市前 {100 - pickup_pct:.0f}% 左右，说明 {zone_name} 是重要的夜间出发热点。")
    elif pickup_pct >= 75:
        reasons.append("夜间活动起点数高于大多数网格，具备较强的晚间活动吸引力。")

    if dropoff_pct >= 90:
        reasons.append("夜间活动终点数处于高位，说明该网格也是夜间到达或返程的重要目的地。")

    if late_pct >= 75:
        reasons.append("凌晨 0-3 点仍保持较高活动占比，说明深夜时段仍有明显出租车活动。")

    if weekend_pct >= 75:
        reasons.append("周末夜间活跃度明显高于工作日，显示出休闲娱乐活动特征。")

    if short_pct >= 75:
        reasons.append("短距离活动比例较高，可能对应局部接驳、短程返程或近距离夜间活动。")

    if bool(row.get("is_transport_hub", False)):
        reasons.append("该网格具有交通枢纽特征，长距离活动、机场或车站相关活动会对活力分数进行修正，避免被简单归为夜间活动核心区。")

    if float(row.get("bar_density", 0) or 0) > 0 or float(row.get("entertainment_poi_count", 0) or 0) > 0:
        reasons.append("POI 画像显示餐饮、酒吧或娱乐设施较集中，为夜间活跃提供了空间解释。")

    if float(row.get("tourism_poi_count", 0) or 0) > 0:
        reasons.append("旅游和公共活动类 POI 较多，说明夜间客流可能与观光、演出或公共空间活动有关。")

    if not reasons:
        reasons.append("该网格的夜间出租车活动较为平稳，未出现特别突出的单项指标。")

    return reasons


def build_region_explanations(
    output_dir: str | Path,
    scored_geojson_path: str | Path | None = None,
) -> dict[str, Any]:
    output = Path(output_dir)
    scores_path = output / "region_scores.csv"
    if not scores_path.exists():
        return {}

    features = pd.read_csv(scores_path)
    phase2_scores_path = output / "region_scores_phase2.csv"
    if phase2_scores_path.exists():
        features = pd.read_csv(phase2_scores_path)
    lookup = load_zone_lookup(scored_geojson_path or output / "region_scores_geojson.json")
    explanations: dict[str, Any] = {}

    for _, row in features.iterrows():
        spatial_unit = str(row["spatial_unit"])
        zone_info = lookup.get(spatial_unit, {})
        zone_name = zone_info.get("zone") or f"活动网格 {spatial_unit}"
        borough = zone_info.get("borough")
        region_type = row.get("region_type", "no_activity")
        type_label = REGION_TYPE_LABELS.get(region_type, str(region_type))
        reasons = describe_region(row, features, zone_name)
        title = f"{zone_name} 被识别为{type_label}"
        if borough:
            title = f"{zone_name}（{borough}）被识别为{type_label}"

        explanations[spatial_unit] = {
            "spatial_unit": spatial_unit,
            "zone": zone_info.get("zone"),
            "borough": borough,
            "region_type": region_type,
            "region_type_label": type_label,
            "title": title,
            "summary": f"{title}，综合活力分数为 {float(row.get('night_vitality_score', 0)):.2f}。",
            "reasons": reasons,
        }

    target = output / "region_explanations.json"
    target.write_text(json.dumps(explanations, ensure_ascii=False, indent=2), encoding="utf-8")
    return explanations
