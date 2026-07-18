from __future__ import annotations

import argparse
from pathlib import Path

import yaml

try:
    from _bootstrap import ensure_project_src
except ModuleNotFoundError:  # Allows importing this file as scripts.run_config.
    from scripts._bootstrap import ensure_project_src

PROJECT_ROOT = ensure_project_src()

from nightsense.core.pipeline import run_from_file
from nightsense.enrichment.phase2_outputs import build_phase2_outputs
from nightsense.evaluation.phase3_outputs import build_phase3_outputs
from nightsense.explain.region_explanations import build_region_explanations
from nightsense.geo.spatial_units import build_spatial_unit_geojson
from nightsense.reporting.markdown_report import generate_report


def resolve_project_path(value: str | Path) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return (PROJECT_ROOT / path).resolve()


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Urban NightSense from a YAML config file.")
    parser.add_argument("config", help="Path to a YAML config file.")
    args = parser.parse_args()

    config_path = Path(args.config)
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))

    input_path = resolve_project_path(config["input_path"])
    output_dir = resolve_project_path(config["output_dir"])
    night_window = config.get("night_window", {})
    pipeline = config.get("pipeline", {})
    spatial_unit = config.get("spatial_unit", {})
    spatial_unit_type = str(spatial_unit.get("type", "h3")).lower()
    h3_resolution = spatial_unit.get("resolution", 8)
    grid_size = spatial_unit.get("grid_size", 0.005)

    run_from_file(
        input_path,
        output_dir=output_dir,
        city=config.get("city", "Unknown"),
        limit=config.get("limit"),
        night_start=night_window.get("start_hour", 20),
        night_end=night_window.get("end_hour", 3),
        n_clusters=pipeline.get("n_clusters", 5),
        spatial_unit_type=spatial_unit_type,
        h3_resolution=h3_resolution,
        grid_size=grid_size,
    )

    if spatial_unit_type in {"h3", "grid"}:
        build_spatial_unit_geojson(
            f"{output_dir}/region_scores.csv",
            f"{output_dir}/region_scores_geojson.json",
            spatial_unit_type=spatial_unit_type,
            grid_size=grid_size,
            h3_geojson_output=f"{output_dir}/h3_region_scores_geojson.json" if spatial_unit_type == "h3" else None,
            h3_scores_output=f"{output_dir}/h3_region_scores.csv" if spatial_unit_type == "h3" else None,
        )
    else:
        raise ValueError(f"Unsupported spatial_unit.type for the Beijing pipeline: {spatial_unit_type}")

    phase2 = config.get("phase2", {})
    if phase2.get("enabled", False):
        build_phase2_outputs(output_dir, h3_resolution=h3_resolution)

    phase3 = config.get("phase3", {})
    if phase3.get("enabled", False):
        build_phase3_outputs(output_dir)

    build_region_explanations(output_dir)
    report_path = generate_report(output_dir)
    print(f"Pipeline finished. Report written to {report_path}")


if __name__ == "__main__":
    main()
