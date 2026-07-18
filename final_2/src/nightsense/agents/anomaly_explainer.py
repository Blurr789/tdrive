from __future__ import annotations

import os
from pathlib import Path
from typing import Any
import json

from nightsense.agents.anomaly_context import AnomalyContextBuilder
from nightsense.agents.cache import AgentCache
from nightsense.agents.providers.openai_compatible import provider_from_env


class AnomalyExplainer:
    def __init__(self, output_dir: str | Path):
        self.output_dir = Path(output_dir)
        self.context_builder = AnomalyContextBuilder(self.output_dir)
        self.cache = AgentCache(self._cache_path())

    def _cache_path(self) -> Path:
        configured = os.environ.get("NIGHTSENSE_AGENT_CACHE")
        if configured:
            return Path(configured)
        project_root = self.output_dir.parents[1] if len(self.output_dir.parents) > 1 else Path.cwd()
        return project_root / ".cache" / "anomaly_agent_explanations.json"

    def _text_items(self, value: Any) -> list[str]:
        if value is None:
            return []
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        if isinstance(value, dict):
            return [str(item).strip() for item in value.values() if str(item).strip()]
        text = str(value).strip()
        if not text:
            return []
        if text.startswith("[") and text.endswith("]"):
            try:
                return self._text_items(json.loads(text))
            except json.JSONDecodeError:
                return [text]
        return [item.strip(" -*•0123456789.、") for item in text.replace("；", ";").split(";") if item.strip()]

    def _normalize_result(self, result: dict[str, Any]) -> dict[str, Any]:
        normalized = dict(result)
        summary_items = self._text_items(normalized.get("summary"))
        normalized["summary"] = "；".join(summary_items) if summary_items else "暂无摘要。"
        for field in ["likely_causes", "evidence", "recommended_checks"]:
            normalized[field] = self._text_items(normalized.get(field))
        return normalized

    def explain(self, spatial_unit: str, night_date: str, hour: int | str, force: bool = False) -> dict[str, Any]:
        context = self.context_builder.build(spatial_unit, night_date, hour)
        event_id = context["event_id"]
        cache_enabled = os.environ.get("LLM_ENABLE_CACHE", "true").lower() != "false"
        if cache_enabled and not force:
            cached = self.cache.get(event_id)
            if cached:
                cached = self._normalize_result(cached)
                cached["cached"] = True
                return cached

        provider = provider_from_env()
        result = self._normalize_result(provider.explain(context))
        response = {
            "event_id": event_id,
            "zone": context["event"].get("zone"),
            "borough": context["event"].get("borough"),
            "display_name": context["event"].get("display_name"),
            "cached": False,
            **result,
        }
        if cache_enabled:
            self.cache.set(event_id, response)
        return response
