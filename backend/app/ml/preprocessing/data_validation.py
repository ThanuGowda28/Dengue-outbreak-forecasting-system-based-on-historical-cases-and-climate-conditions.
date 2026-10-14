from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

CLIMATE_RANGES = {
    "temperature": (-10.0, 60.0),
    "humidity": (0.0, 100.0),
    "rainfall": (0.0, 2000.0),
    "precipitation": (0.0, 2000.0),
    "pressure": (800.0, 1100.0),
    "wind_speed": (0.0, 150.0),
    "windspeed": (0.0, 150.0),
    "cloud_cover": (0.0, 100.0),
    "cloudcover": (0.0, 100.0),
    "latitude": (-90.0, 90.0),
    "longitude": (-180.0, 180.0),
}
CLIMATE_ALIASES = {
    "temp": "temperature", "temp_c": "temperature", "temperature_c": "temperature",
    "avg_temp": "temperature", "average_temperature": "temperature",
    "humidity_pct": "humidity", "relative_humidity": "humidity",
    "rainfall_mm": "rainfall", "precipitation_mm": "precipitation",
    "pressure_hpa": "pressure", "surface_pressure": "pressure",
    "wind_speed_mps": "wind_speed", "windspeed_mps": "windspeed",
    "cloud_cover_pct": "cloud_cover", "cloudcover_pct": "cloudcover",
    "lat": "latitude", "lon": "longitude", "lng": "longitude",
}


def climate_range_key(column: str) -> str | None:
    if column in CLIMATE_ALIASES:
        return CLIMATE_ALIASES[column]
    for alias, canonical in CLIMATE_ALIASES.items():
        if column.endswith(f"_{alias}"):
            return canonical
    return next(
        (key for key in CLIMATE_RANGES if column == key or column.endswith(f"_{key}")),
        None,
    )


def canonical_column_name(name: Any) -> str:
    name = re.sub(r"[^a-z0-9]+", "_", str(name).strip().lower())
    return name.strip("_")


def validate_dataset(
    frame: pd.DataFrame, target_column: str | None = None
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Validate tabular input and replace malformed/out-of-range climate values with NaN."""
    if not isinstance(frame, pd.DataFrame):
        raise TypeError("Dataset must be a pandas DataFrame.")
    if frame.empty:
        raise ValueError("Dataset contains no rows.")
    if len(frame.columns) == 0:
        raise ValueError("Dataset contains no columns.")

    normalized = [canonical_column_name(name) for name in frame.columns]
    if any(not name for name in normalized):
        raise ValueError("Dataset contains an empty column name.")
    duplicated = sorted({name for name in normalized if normalized.count(name) > 1})
    if duplicated:
        raise ValueError(f"Column names are duplicated after normalization: {duplicated}.")

    result = frame.copy()
    result.columns = normalized
    target = canonical_column_name(target_column) if target_column else None
    if target and target not in result.columns:
        raise ValueError(f"Target column '{target}' was not found in the CSV.")

    invalid_counts: dict[str, int] = {}
    invalid_examples: dict[str, list[Any]] = {}
    for column in result.columns:
        range_key = climate_range_key(column)
        if range_key is None:
            continue
        lower, upper = CLIMATE_RANGES[range_key]
        values = pd.to_numeric(result[column], errors="coerce")
        finite = values.map(lambda value: pd.isna(value) or np.isfinite(value))
        invalid = values.notna() & (~finite | (values < lower) | (values > upper))
        count = int(invalid.sum())
        if count:
            invalid_counts[column] = count
            invalid_examples[column] = result.loc[invalid, column].astype(str).head(5).tolist()
        result.loc[invalid, column] = np.nan
        result[column] = values.mask(invalid)

    if target:
        target_values = result[target]
        if pd.api.types.is_numeric_dtype(target_values):
            negative = pd.to_numeric(target_values, errors="coerce") < 0
            if negative.any():
                invalid_counts[target] = invalid_counts.get(target, 0) + int(negative.sum())
                invalid_examples[target] = target_values.loc[negative].astype(str).head(5).tolist()
                result.loc[negative, target] = np.nan

    report = {
        "row_count": int(len(result)),
        "column_count": int(len(result.columns)),
        "columns": list(result.columns),
        "target_column": target,
        "invalid_climate_values": invalid_counts,
        "invalid_value_examples": invalid_examples,
    }
    return result, report
