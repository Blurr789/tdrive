from __future__ import annotations

import json

from flask import Flask, jsonify, request

from backend.services.output_store import OutputStore


def register_api_routes(app: Flask, store: OutputStore) -> None:
    @app.get("/api/health")
    def health():
        return jsonify({"status": "ok", "output_dir": str(store.output_dir)})

    @app.get("/api/summary")
    def summary():
        summary_path = store.output_dir / "pipeline_summary.json"
        if summary_path.exists():
            data = json.loads(summary_path.read_text(encoding="utf-8"))
            if (store.output_dir / "h3_region_scores_geojson.json").exists():
                data["spatial_views"] = ["h3"]
            elif (store.output_dir / "region_scores_phase2.csv").exists():
                data["phase"] = "phase2"
                data["spatial_views"] = ["h3"]
            return jsonify(store.json_safe(data))

        scores = store.read_csv(store.scores_filename())
        anomalies = store.read_csv(store.anomalies_filename())
        return jsonify(
            {
                "region_count": int(len(scores)),
                "anomaly_count": int(len(anomalies)),
                "top_regions": store.dataframe_records(scores.head(10)) if not scores.empty else [],
            }
        )

    @app.get("/api/regions")
    def regions():
        spatial_unit_type = (request.args.get("spatial_unit") or request.args.get("unit") or "h3").lower()
        if spatial_unit_type == "h3":
            scores = store.read_csv("h3_region_scores.csv")
            return jsonify(store.dataframe_records(scores))
        scores = store.enrich_regions(store.read_csv(store.scores_filename()))
        return jsonify(store.dataframe_records(scores))

    @app.get("/api/regions/<spatial_unit>")
    def region_detail(spatial_unit: str):
        spatial_unit_type = (request.args.get("spatial_unit") or request.args.get("unit") or "h3").lower()
        if spatial_unit_type == "h3":
            scores = store.read_csv("h3_region_scores.csv")
        else:
            scores = store.enrich_regions(store.read_csv(store.scores_filename()))
        activity = store.read_csv("hourly_activity.csv")
        anomalies = store.read_csv(store.anomalies_filename())
        explanations = store.read_json("region_explanations.json")

        row = scores[scores["spatial_unit"].astype(str) == str(spatial_unit)]
        if row.empty:
            return jsonify({"error": "region not found"}), 404

        detail = row.iloc[0].to_dict()
        if not activity.empty:
            region_activity = activity[activity["spatial_unit"].astype(str) == str(spatial_unit)]
            hourly_series = (
                region_activity.groupby("hour", as_index=False)["activity_count"].sum()
                .sort_values("hour")
                .to_dict(orient="records")
            )
        else:
            hourly_series = []

        if not anomalies.empty:
            region_anomalies = anomalies[anomalies["spatial_unit"].astype(str) == str(spatial_unit)].head(20)
            anomaly_rows = region_anomalies.to_dict(orient="records")
        else:
            anomaly_rows = []

        detail["hourly_activity"] = hourly_series
        detail["anomalies"] = anomaly_rows
        detail["explanation"] = explanations.get(str(spatial_unit), {})
        return jsonify(store.json_safe(detail))

    @app.get("/api/hourly")
    def hourly():
        activity = store.read_csv("hourly_activity.csv")
        if activity.empty:
            return jsonify([])
        hourly_activity = activity.groupby("hour", as_index=False)["activity_count"].sum()
        return jsonify(store.dataframe_records(hourly_activity))

    @app.get("/api/anomalies")
    def anomalies():
        table = store.enrich_anomalies(store.read_csv(store.anomalies_filename()))
        return jsonify(store.dataframe_records(table.head(100)))

    @app.get("/api/score-methods")
    def score_methods():
        table = store.enrich_regions(store.read_csv("score_method_comparison.csv"))
        return jsonify(store.dataframe_records(table))

    @app.get("/api/forecast-metrics")
    def forecast_metrics():
        table = store.read_csv("forecast_metrics.csv")
        return jsonify(store.dataframe_records(table))

    @app.get("/api/forecasts")
    def forecasts():
        table = store.enrich_regions(store.read_csv("region_forecasts.csv"))
        return jsonify(store.dataframe_records(table))

    @app.get("/api/region-types")
    def region_types():
        scores = store.read_csv(store.scores_filename())
        if scores.empty or "region_type" not in scores.columns:
            return jsonify([])
        grouped = scores.groupby("region_type", as_index=False).size().rename(columns={"size": "count"})
        return jsonify(store.dataframe_records(grouped.sort_values("count", ascending=False)))

    @app.get("/api/report")
    def report():
        path = store.output_dir / "report.md"
        if not path.exists():
            return jsonify({"error": "report not found"}), 404
        return jsonify({"path": str(path), "content": path.read_text(encoding="utf-8")})

    @app.get("/api/geojson")
    def geojson():
        hour = request.args.get("hour")
        spatial_unit_type = (request.args.get("spatial_unit") or request.args.get("unit") or "h3").lower()
        if spatial_unit_type == "h3":
            if hour is not None and hour != "all":
                return jsonify(store.json_safe(store.build_h3_hourly_geojson(int(hour))))
            geojson_path = store.output_dir / "h3_region_scores_geojson.json"
            if not geojson_path.exists():
                return jsonify({"type": "FeatureCollection", "features": []})
            return jsonify(store.json_safe(store.enrich_geojson(json.loads(geojson_path.read_text(encoding="utf-8")))))
        if hour is not None and hour != "all":
            return jsonify(store.json_safe(store.build_hourly_geojson(int(hour))))
        geojson_path = store.output_dir / store.geojson_filename(spatial_unit_type)
        if not geojson_path.exists():
            return jsonify({"type": "FeatureCollection", "features": []})
        return jsonify(store.json_safe(store.enrich_geojson(json.loads(geojson_path.read_text(encoding="utf-8")))))

    @app.get("/api/poi")
    def poi():
        table = store.read_csv("poi_features.csv")
        return jsonify(store.dataframe_records(table))
