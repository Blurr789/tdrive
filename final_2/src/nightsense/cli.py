from __future__ import annotations

import argparse

from .core.pipeline import run_from_file


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Urban NightSense mobility analytics pipeline")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run = subparsers.add_parser("run", help="Run the pipeline on CSV or Parquet trip data")
    run.add_argument("--input", required=True)
    run.add_argument("--city", default="Unknown")
    run.add_argument("--output", default="outputs/run")
    run.add_argument("--limit", type=int, default=None)

    return parser


def main() -> None:
    args = build_parser().parse_args()
    results = run_from_file(args.input, output_dir=args.output, city=args.city, limit=args.limit)

    top = results["region_scores"][["spatial_unit", "night_vitality_score", "region_type"]].head(5)
    print("Urban NightSense pipeline finished.")
    print(top.to_string(index=False))


if __name__ == "__main__":
    main()
