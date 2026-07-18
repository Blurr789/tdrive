from __future__ import annotations

from pathlib import Path
from typing import Any

from nightsense.agents.anomaly_explainer import AnomalyExplainer


class AgentService:
    def __init__(self, output_dir: str | Path):
        self.anomaly_explainer = AnomalyExplainer(output_dir)

    def explain_anomaly(self, payload: dict[str, Any]) -> dict[str, Any]:
        spatial_unit = payload.get("spatial_unit")
        night_date = payload.get("night_date")
        hour = payload.get("hour")
        force = bool(payload.get("force", False))
        if spatial_unit is None or night_date is None or hour is None:
            raise ValueError("spatial_unit, night_date and hour are required")
        return self.anomaly_explainer.explain(str(spatial_unit), str(night_date), hour, force=force)

