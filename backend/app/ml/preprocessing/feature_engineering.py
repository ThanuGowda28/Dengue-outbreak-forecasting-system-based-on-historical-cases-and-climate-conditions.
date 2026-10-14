from __future__ import annotations

from typing import Any

import pandas as pd

DATE_COLUMNS = ("date", "weather_date", "observation_date", "timestamp", "datetime")


def engineer_features(frame: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Derive calendar features from recognized date columns without using future data."""
    result = frame.copy()
    derived: dict[str, list[str]] = {}
    invalid_dates: dict[str, int] = {}
    dropped: list[str] = []

    for column in DATE_COLUMNS:
        if column not in result.columns:
            continue
        parsed = pd.to_datetime(result[column], errors="coerce", utc=True)
        invalid_dates[column] = int(parsed.isna().sum())
        result[f"{column}_year"] = parsed.dt.year
        result[f"{column}_month"] = parsed.dt.month
        result[f"{column}_day"] = parsed.dt.day
        result[f"{column}_dayofweek"] = parsed.dt.dayofweek
        result[f"{column}_dayofyear"] = parsed.dt.dayofyear
        derived[column] = [
            f"{column}_year",
            f"{column}_month",
            f"{column}_day",
            f"{column}_dayofweek",
            f"{column}_dayofyear",
        ]
        result = result.drop(columns=column)
        dropped.append(column)

    return result, {
        "derived_date_features": derived,
        "invalid_dates": invalid_dates,
        "dropped_source_columns": dropped,
    }
