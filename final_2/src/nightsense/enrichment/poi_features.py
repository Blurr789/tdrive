from __future__ import annotations

import math
from collections import Counter
from typing import Any


ENTERTAINMENT_KEYWORDS = [
    "village",
    "soho",
    "tribeca",
    "chelsea",
    "theater",
    "theatre",
    "times sq",
    "meatpacking",
    "east village",
    "lower east side",
    "williamsburg",
    "dumbo",
    "greenwich",
    "alphabet city",
]
TOURISM_KEYWORDS = [
    "park",
    "museum",
    "times sq",
    "battery",
    "central park",
    "world trade",
    "lincoln square",
    "madison",
    "un",
]
SUBWAY_HINT_KEYWORDS = [
    "midtown",
    "downtown",
    "village",
    "chelsea",
    "soho",
    "tribeca",
    "upper",
    "lower",
    "brooklyn",
    "queens",
    "bronx",
]

AMAP_CATEGORY_GROUPS = {
    "dining": {"餐饮服务"},
    "shopping": {"购物服务"},
    "leisure": {"体育休闲服务", "风景名胜", "生活服务", "事件活动"},
    "hotel": {"住宿服务"},
    "transport": {"交通设施服务", "通行设施", "道路附属设施"},
    "culture": {"科教文化服务"},
    "residential": {"商务住宅"},
    "office": {"公司企业"},
    "public_service": {"政府机构及社会团体", "医疗保健服务", "金融保险服务", "公共设施"},
    "auto": {"汽车服务", "汽车维修", "汽车销售", "摩托车服务"},
}

AMAP_IGNORED_CATEGORIES = {"地名地址信息", "室内设施", "虚拟数据"}
NIGHTLIFE_GROUPS = {"dining", "shopping", "leisure", "hotel"}
TOURISM_GROUPS = {"leisure", "culture"}


def keyword_score(text: str, keywords: list[str]) -> int:
    lowered = text.lower()
    return sum(1 for keyword in keywords if keyword in lowered)


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return default
    return parsed if math.isfinite(parsed) else default


def _major_category(poi_type: str) -> str:
    return str(poi_type or "").split(";", maxsplit=1)[0].strip()


def _category_group(category: str) -> str | None:
    for group, categories in AMAP_CATEGORY_GROUPS.items():
        if category in categories:
            return group
    return None


def _normalized_entropy(counts: Counter[str]) -> float:
    total = sum(counts.values())
    if total <= 0 or len(counts) <= 1:
        return 0.0
    entropy = 0.0
    for count in counts.values():
        share = count / total
        entropy -= share * math.log(share)
    return entropy / math.log(len(AMAP_CATEGORY_GROUPS))


def infer_amap_poi_features(regeocode: dict[str, Any] | None) -> dict[str, float]:
    """Infer Beijing POI features from AMap reverse-geocoding results.

    AMap returns nearby POIs with Chinese category paths. We convert those
    categories into stable functional groups, then score diversity by both
    category spread and local POI coverage.
    """
    if not regeocode:
        return {}

    pois = [poi for poi in regeocode.get("pois", []) if isinstance(poi, dict)]
    aois = [aoi for aoi in regeocode.get("aois", []) if isinstance(aoi, dict)]
    address_component = regeocode.get("addressComponent") or {}
    business_areas = address_component.get("businessAreas") or []

    category_counts: Counter[str] = Counter()
    group_counts: Counter[str] = Counter()
    weighted_distance_sum = 0.0
    weighted_count = 0.0

    for poi in pois:
        category = _major_category(str(poi.get("type") or ""))
        if not category or category in AMAP_IGNORED_CATEGORIES:
            continue
        group = _category_group(category)
        if not group:
            continue
        category_counts[category] += 1
        group_counts[group] += 1
        distance = max(_safe_float(poi.get("distance"), 1000.0), 1.0)
        weight = 1 / math.sqrt(distance)
        weighted_distance_sum += distance * weight
        weighted_count += weight

    meaningful_count = sum(group_counts.values())
    category_count = len(group_counts)
    entropy_score = _normalized_entropy(group_counts)
    category_spread = min(1.0, category_count / 8)
    coverage = min(1.0, meaningful_count / 20)
    poi_diversity = (0.65 * entropy_score + 0.35 * category_spread) * (0.35 + 0.65 * coverage)

    nightlife_count = sum(group_counts[group] for group in NIGHTLIFE_GROUPS)
    tourism_count = sum(group_counts[group] for group in TOURISM_GROUPS)
    transport_count = group_counts["transport"]
    restaurant_count = group_counts["dining"]
    business_area_count = len([area for area in business_areas if isinstance(area, dict) and area.get("name")])
    aoi_count = len(aois)
    avg_poi_distance = weighted_distance_sum / weighted_count if weighted_count else 1000.0

    bar_density = min(1.0, (nightlife_count + 0.5 * business_area_count) / 18)
    restaurant_density = min(1.0, (restaurant_count + 0.35 * group_counts["shopping"]) / 15)
    subway_distance = max(0.15, 1.8 - min(1.35, transport_count * 0.08))

    return {
        "bar_density": round(bar_density, 4),
        "restaurant_density": round(restaurant_density, 4),
        "subway_distance": round(subway_distance, 3),
        "entertainment_poi_count": float(nightlife_count),
        "tourism_poi_count": float(tourism_count),
        "poi_diversity": round(min(1.0, poi_diversity), 3),
        "poi_total_count": float(len(pois)),
        "poi_meaningful_count": float(meaningful_count),
        "poi_category_count": float(category_count),
        "nightlife_poi_count": float(nightlife_count),
        "transport_poi_count": float(transport_count),
        "business_area_count": float(business_area_count),
        "aoi_count": float(aoi_count),
        "avg_poi_distance": round(avg_poi_distance, 2),
    }


def infer_poi_features(
    zone_name: str,
    borough: str | None,
    area: float | None,
    amap_regeocode: dict[str, Any] | None = None,
) -> dict[str, float]:
    amap_features = infer_amap_poi_features(amap_regeocode)
    if amap_features:
        return amap_features

    text = f"{zone_name} {borough or ''}".strip()
    entertainment = keyword_score(text, ENTERTAINMENT_KEYWORDS)
    tourism = keyword_score(text, TOURISM_KEYWORDS)
    subway_hint = keyword_score(text, SUBWAY_HINT_KEYWORDS)

    base_area = max(float(area or 0.0001), 0.0001)
    bar_density = round((entertainment * 8 + tourism * 1.5) / base_area, 4)
    restaurant_density = round((entertainment * 10 + tourism * 3 + subway_hint * 1.5) / base_area, 4)
    entertainment_poi_count = float(entertainment * 12 + tourism * 3)
    tourism_poi_count = float(tourism * 10)
    poi_diversity = min(1.0, (entertainment + tourism + subway_hint) / 6)
    subway_distance = round(max(0.15, 1.8 - subway_hint * 0.22 - entertainment * 0.18), 3)

    return {
        "bar_density": bar_density,
        "restaurant_density": restaurant_density,
        "subway_distance": subway_distance,
        "entertainment_poi_count": entertainment_poi_count,
        "tourism_poi_count": tourism_poi_count,
        "poi_diversity": round(poi_diversity, 3),
        "poi_total_count": 0.0,
        "poi_meaningful_count": 0.0,
        "poi_category_count": 0.0,
        "nightlife_poi_count": 0.0,
        "transport_poi_count": 0.0,
        "business_area_count": 0.0,
        "aoi_count": 0.0,
        "avg_poi_distance": 0.0,
    }
