from __future__ import annotations

from flask import Flask, jsonify, request

from backend.services.agent_service import AgentService
from backend.services.output_store import OutputStore


def register_ai_routes(app: Flask, store: OutputStore) -> None:
    service = AgentService(store.output_dir)

    @app.post("/api/ai/anomalies/explain")
    def explain_anomaly():
        payload = request.get_json(silent=True) or {}
        try:
            result = service.explain_anomaly(payload)
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400
        except Exception as exc:
            return jsonify({"error": str(exc)}), 500
        return jsonify(store.json_safe(result))

