from __future__ import annotations

from pathlib import Path
from typing import Any

from nightsense.evaluation.forecasting import build_forecast_outputs
from nightsense.evaluation.score_methods import build_score_method_comparison
from nightsense.explain.anomaly_reasons import build_anomaly_attribution


def build_phase3_outputs(output_dir: str | Path) -> dict[str, Any]:
    comparison = build_score_method_comparison(output_dir)
    anomalies = build_anomaly_attribution(output_dir)
    metrics, forecasts = build_forecast_outputs(output_dir)
    return {
        "score_method_comparison": comparison,
        "anomalies_attributed": anomalies,
        "forecast_metrics": metrics,
        "region_forecasts": forecasts,
    }

