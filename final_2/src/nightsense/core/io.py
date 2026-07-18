from __future__ import annotations

from pathlib import Path

import pandas as pd

from .schema import normalize_columns, require_any


def load_trip_data(path: str | Path, city: str = "Unknown", limit: int | None = None) -> pd.DataFrame:
    """Load CSV or Parquet trip data and normalize it."""
    source = Path(path)
    if not source.exists():
        raise FileNotFoundError(source)

    if source.suffix.lower() in {".parquet", ".pq"}:
        raw = pd.read_parquet(source)
    elif source.suffix.lower() in {".csv", ".txt"}:
        raw = pd.read_csv(source)
    else:
        raise ValueError(f"Unsupported input format: {source.suffix}")

    if limit is not None:
        raw = raw.head(limit)

    normalized = normalize_columns(raw, city=city)
    require_any(normalized, [["start_time"], ["start_zone", "start_lat", "start_lon"]])
    return normalized


def write_outputs(output_dir: str | Path, **tables: pd.DataFrame) -> None:
    target = Path(output_dir)
    target.mkdir(parents=True, exist_ok=True)
    for name, table in tables.items():
        table.to_csv(target / f"{name}.csv", index=False)
