from __future__ import annotations

from typing import Any


AgentDict = dict[str, Any]


def anomaly_event_id(spatial_unit: str, night_date: str, hour: int | str) -> str:
    return f"{spatial_unit}|{night_date}|{int(hour)}"

