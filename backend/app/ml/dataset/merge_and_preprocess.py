"""Merge existing annual dengue and NASA POWER files into ML-ready splits.

This module reads local CSVs only. It does not download, regenerate, or train.
"""
from __future__ import annotations

import argparse
import html
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder, StandardScaler

from .climate_data_acquisition import canonical_state_name

DATASET_DIR = Path(__file__).resolve().parent
RAW_DIR = DATASET_DIR / "raw"
MERGED_DIR = DATASET_DIR / "merged"
PROCESSED_DIR = DATASET_DIR / "processed"
DENGUE_CSV = RAW_DIR / "ncvbdc_dengue.csv"
CLIMATE_CSV = RAW_DIR / "climate_data.csv"
MERGED_CSV = MERGED_DIR / "dengue_climate_dataset.csv"

# Explicit annual case-count labels; boundaries are in confirmed cases per State/UT/year.
RISK_THRESHOLDS = {"low_max_exclusive": 1000, "moderate_max_exclusive": 10000}
CASE_COLUMNS = ["state_ut", "year", "confirmed_cases", "deaths"]
CLIMATE_SOURCE_COLUMNS = {
    "temperature_c": "average_temperature_c",
    "relative_humidity_pct": "average_relative_humidity_pct",
    "precipitation_mm_day": "total_rainfall_mm",
    "wind_speed_m_s": "average_wind_speed_m_s",
    "surface_pressure_kpa": "average_surface_pressure_kpa",
    "solar_radiation_mj_m2_day": "average_solar_radiation_mj_m2_day",
}
CLIMATE_METRICS = list(CLIMATE_SOURCE_COLUMNS.values())
FEATURE_COLUMNS = [
    "year", "average_temperature_c", "average_relative_humidity_pct",
    "total_rainfall_mm", "average_wind_speed_m_s",
    "average_surface_pressure_kpa", "average_solar_radiation_mj_m2_day",
    "temperature_humidity_interaction", "state_ut", "season",
    "rainfall_category", "humidity_category", "temperature_category",
]


class DatasetError(ValueError):
    """Raised for invalid source or merged dataset structure."""


def _read_csv(path: Path, required_columns: list[str]) -> pd.DataFrame:
    if not path.is_file():
        raise FileNotFoundError(f"Required source dataset not found: {path}")
    try:
        frame = pd.read_csv(path)
    except (OSError, pd.errors.ParserError, UnicodeError) as error:
        raise DatasetError(f"Could not read '{path}': {error}") from error
    missing = sorted(set(required_columns) - set(frame.columns))
    if missing:
        raise DatasetError(f"'{path.name}' is missing required columns: {missing}")
    if frame.empty:
        raise DatasetError(f"'{path}' contains no data rows.")
    return frame


def normalize_dengue_data(path: Path = DENGUE_CSV) -> tuple[pd.DataFrame, dict[str, Any]]:
    source = _read_csv(path, ["state_ut"])
    source_rows = len(source)
    source["state_ut"] = source["state_ut"].map(canonical_state_name)
    source = source.loc[source["state_ut"].notna()].copy()
    year_columns: dict[int, tuple[str, str]] = {}
    for column in source.columns:
        if column.startswith("cases_"):
            suffix = column.removeprefix("cases_").rstrip("*")
            if suffix.isdigit() and f"deaths_{suffix}" in source.columns:
                year_columns[int(suffix)] = (column, f"deaths_{suffix}")
    if not year_columns:
        raise DatasetError("No matched annual cases_YYYY/deaths_YYYY columns were found.")

    records: list[pd.DataFrame] = []
    for year, (case_column, death_column) in sorted(year_columns.items()):
        annual = source[["state_ut", case_column, death_column]].rename(
            columns={case_column: "confirmed_cases", death_column: "deaths"}
        )
        annual["year"] = year
        records.append(annual[CASE_COLUMNS])
    normalized = pd.concat(records, ignore_index=True)
    for column in ("confirmed_cases", "deaths"):
        normalized[column] = pd.to_numeric(normalized[column], errors="coerce")
    duplicates = int(normalized.duplicated(["state_ut", "year"]).sum())
    invalid_mask = (
        normalized["confirmed_cases"].isna()
        | normalized["deaths"].isna()
        | ~normalized["confirmed_cases"].map(np.isfinite)
        | ~normalized["deaths"].map(np.isfinite)
        | (normalized["confirmed_cases"] < 0)
        | (normalized["deaths"] < 0)
        | (normalized["deaths"] > normalized["confirmed_cases"])
    )
    invalid_rows = int(invalid_mask.sum())
    normalized = normalized.loc[~invalid_mask].drop_duplicates(["state_ut", "year"]).copy()
    normalized["year"] = normalized["year"].astype(int)
    normalized["confirmed_cases"] = normalized["confirmed_cases"].astype(int)
    normalized["deaths"] = normalized["deaths"].astype(int)
    if normalized.empty:
        raise DatasetError("No valid annual dengue rows remain after validation.")
    return normalized, {
        "source_rows": source_rows,
        "normalized_rows": int(len(normalized)),
        "source_non_state_rows_excluded": source_rows - int(source["state_ut"].notna().sum()),
        "duplicate_state_year_rows_removed": duplicates,
        "invalid_case_death_rows_removed": invalid_rows,
        "years": sorted(int(year) for year in normalized["year"].unique()),
        "states": int(normalized["state_ut"].nunique()),
    }


def aggregate_climate_data(path: Path = CLIMATE_CSV) -> tuple[pd.DataFrame, dict[str, Any]]:
    source_columns = ["state_ut", "year", *CLIMATE_SOURCE_COLUMNS.keys()]
    source = _read_csv(path, source_columns)
    source_rows = len(source)
    source["state_ut"] = source["state_ut"].map(canonical_state_name)
    source["year"] = pd.to_numeric(source["year"], errors="coerce")
    for column in CLIMATE_SOURCE_COLUMNS:
        source[column] = pd.to_numeric(source[column], errors="coerce")
    invalid_key = source["state_ut"].isna() | source["year"].isna() | ~source["year"].between(2021, 2026)
    invalid_rows = int(invalid_key.sum())
    source = source.loc[~invalid_key].copy()
    source["year"] = source["year"].astype(int)
    source = source.drop_duplicates(["state_ut", "date"] if "date" in source.columns else ["state_ut", "year"])

    grouped = source.groupby(["state_ut", "year"], as_index=False).agg(
        average_temperature_c=("temperature_c", "mean"),
        average_relative_humidity_pct=("relative_humidity_pct", "mean"),
        average_wind_speed_m_s=("wind_speed_m_s", "mean"),
        average_surface_pressure_kpa=("surface_pressure_kpa", "mean"),
        average_solar_radiation_mj_m2_day=("solar_radiation_mj_m2_day", "mean"),
    )
    rainfall = source.groupby(["state_ut", "year"])["precipitation_mm_day"].sum(min_count=1)
    grouped = grouped.merge(rainfall.rename("total_rainfall_mm"), on=["state_ut", "year"], validate="one_to_one")
    if grouped.empty:
        raise DatasetError("No valid annual climate summaries remain after validation.")
    return grouped, {
        "source_rows": source_rows,
        "annual_rows": int(len(grouped)),
        "invalid_state_year_rows_excluded": invalid_rows,
        "duplicate_daily_rows_removed": int(source_rows - invalid_rows - len(source)),
        "states": int(grouped["state_ut"].nunique()),
        "years": sorted(int(year) for year in grouped["year"].unique()),
        "missing_annual_values_before_imputation": {
            column: int(grouped[column].isna().sum()) for column in CLIMATE_METRICS
        },
    }


def _impute_climate(merged: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Any]]:
    result = merged.sort_values(["state_ut", "year"]).copy()
    before = {column: int(result[column].isna().sum()) for column in CLIMATE_METRICS}
    methods: dict[str, dict[str, int]] = {}
    for column in CLIMATE_METRICS:
        original_missing = result[column].isna()
        # Only interpolate within a state's observed annual series, then fall back
        # to same-year cross-state median and finally the global median.
        interpolated = result.groupby("state_ut", sort=False)[column].transform(
            lambda values: values.interpolate(method="linear", limit_direction="both")
        )
        result[column] = result[column].fillna(interpolated)
        state_interpolated = int((original_missing & result[column].notna()).sum())
        remaining = result[column].isna()
        annual_medians = result.groupby("year")[column].transform("median")
        result[column] = result[column].fillna(annual_medians)
        annual_filled = int((remaining & result[column].notna()).sum())
        remaining = result[column].isna()
        global_median = result[column].median()
        if pd.isna(global_median):
            raise DatasetError(f"Climate column '{column}' has no usable values for imputation.")
        result[column] = result[column].fillna(global_median)
        global_filled = int(remaining.sum())
        methods[column] = {
            "within_state_linear_interpolation": state_interpolated,
            "same_year_cross_state_median": annual_filled,
            "global_median_fallback": global_filled,
        }
    return result, {"missing_before": before, "imputation_counts": methods}


def _risk_label(cases: int) -> str:
    if cases < RISK_THRESHOLDS["low_max_exclusive"]:
        return "Low Risk"
    if cases < RISK_THRESHOLDS["moderate_max_exclusive"]:
        return "Moderate Risk"
    return "High Risk"


def build_merged_dataset(dengue_csv: Path = DENGUE_CSV, climate_csv: Path = CLIMATE_CSV) -> tuple[pd.DataFrame, dict[str, Any]]:
    dengue, dengue_report = normalize_dengue_data(dengue_csv)
    climate, climate_report = aggregate_climate_data(climate_csv)
    merged = dengue.merge(climate, on=["state_ut", "year"], how="left", validate="one_to_one", indicator=True)
    unmatched = merged.loc[merged["_merge"] != "both", ["state_ut", "year"]]
    merge_report = {
        "dengue_keys_without_climate": unmatched.to_dict(orient="records"),
        "dengue_rows_without_climate": int(len(unmatched)),
        "climate_rows_without_dengue": int(len(climate.merge(dengue[["state_ut", "year"]], on=["state_ut", "year"], how="left", indicator=True).query("_merge == 'left_only'"))),
    }
    merged = merged.drop(columns="_merge")
    merged, imputation_report = _impute_climate(merged)
    merged["season"] = "Annual"
    merged["temperature_humidity_interaction"] = (
        merged["average_temperature_c"] * merged["average_relative_humidity_pct"]
    )
    merged["rainfall_category"] = pd.cut(
        merged["total_rainfall_mm"], bins=[-np.inf, 500, 1500, np.inf],
        labels=["Low", "Moderate", "High"], right=False,
    ).astype("string")
    merged["humidity_category"] = pd.cut(
        merged["average_relative_humidity_pct"], bins=[-np.inf, 40, 70, np.inf],
        labels=["Low", "Moderate", "High"], right=False,
    ).astype("string")
    merged["temperature_category"] = pd.cut(
        merged["average_temperature_c"], bins=[-np.inf, 20, 30, np.inf],
        labels=["Cool", "Moderate", "Hot"], right=False,
    ).astype("string")
    merged["outbreak_risk"] = merged["confirmed_cases"].map(_risk_label)

    required = ["state_ut", "year", "confirmed_cases", "deaths", *CLIMATE_METRICS, "outbreak_risk"]
    missing_required = merged[required].isna().any(axis=1)
    invalid = (
        merged["confirmed_cases"].lt(0) | merged["deaths"].lt(0)
        | merged["deaths"].gt(merged["confirmed_cases"])
        | ~merged["year"].between(2021, 2026)
    )
    invalid_count = int((missing_required | invalid).sum())
    merged = merged.loc[~(missing_required | invalid)].copy()
    merged = merged.sort_values(["state_ut", "year"]).reset_index(drop=True)
    if merged.empty:
        raise DatasetError("No rows remain after merge validation and cleaning.")
    if merged.duplicated(["state_ut", "year"]).any():
        raise DatasetError("Merged dataset contains duplicate State/UT-year records.")
    report = {
        "dengue": dengue_report,
        "climate": climate_report,
        "merge": merge_report,
        "imputation": imputation_report,
        "invalid_merged_rows_removed": invalid_count,
        "final_shape": [int(merged.shape[0]), int(merged.shape[1])],
        "duplicate_state_year_rows": int(merged.duplicated(["state_ut", "year"]).sum()),
        "missing_values_after_imputation": {column: int(count) for column, count in merged.isna().sum().items()},
        "target_thresholds": {
            "Low Risk": f"confirmed_cases < {RISK_THRESHOLDS['low_max_exclusive']}",
            "Moderate Risk": f"{RISK_THRESHOLDS['low_max_exclusive']} <= confirmed_cases < {RISK_THRESHOLDS['moderate_max_exclusive']}",
            "High Risk": f"confirmed_cases >= {RISK_THRESHOLDS['moderate_max_exclusive']}",
        },
        "target_class_distribution": {str(k): int(v) for k, v in merged["outbreak_risk"].value_counts().items()},
        "partial_year_note": "Climate data for 2026 covers only dates available in the source file; 2026 annual totals/means are year-to-date.",
    }
    return merged, report


def preprocess_dataset(merged: pd.DataFrame, output_dir: Path = PROCESSED_DIR, test_size: float = 0.2, random_state: int = 42) -> dict[str, Any]:
    if not 0 < test_size < 1:
        raise DatasetError("test_size must be greater than zero and less than one.")
    if len(merged) < 2 or merged["outbreak_risk"].nunique() < 2:
        raise DatasetError("At least two records and two target classes are required for a stratified split.")
    if merged["outbreak_risk"].value_counts().min() < 2:
        raise DatasetError("Every risk class needs at least two examples for a stratified split.")

    feature_frame = merged[FEATURE_COLUMNS].copy()
    target = merged["outbreak_risk"].astype(str)
    categorical_features = ["state_ut", "season", "rainfall_category", "humidity_category", "temperature_category"]
    feature_frame = pd.get_dummies(feature_frame, columns=categorical_features, dtype=float)
    feature_frame = feature_frame.astype(float)
    x_train, x_test, y_train, y_test = train_test_split(
        feature_frame, target, test_size=test_size, random_state=random_state, stratify=target
    )
    label_encoder = LabelEncoder()
    y_train_encoded = label_encoder.fit_transform(y_train)
    y_test_encoded = label_encoder.transform(y_test)
    scaler_columns = [column for column in feature_frame.columns if column not in {"year"}]
    scaler = StandardScaler()
    x_train.loc[:, scaler_columns] = scaler.fit_transform(x_train[scaler_columns])
    x_test.loc[:, scaler_columns] = scaler.transform(x_test[scaler_columns])

    train = x_train.copy()
    train["outbreak_risk"] = y_train_encoded
    test = x_test.copy()
    test["outbreak_risk"] = y_test_encoded
    output_dir.mkdir(parents=True, exist_ok=True)
    train_path, test_path = output_dir / "train.csv", output_dir / "test.csv"
    scaler_path, encoder_path = output_dir / "scaler.pkl", output_dir / "label_encoder.pkl"
    train.to_csv(train_path, index=False)
    test.to_csv(test_path, index=False)
    joblib.dump(scaler, scaler_path)
    joblib.dump(label_encoder, encoder_path)
    return {
        "train_rows": int(len(train)), "test_rows": int(len(test)),
        "risk_thresholds": {
            "Low Risk": f"confirmed_cases < {RISK_THRESHOLDS['low_max_exclusive']}",
            "Moderate Risk": f"{RISK_THRESHOLDS['low_max_exclusive']} <= confirmed_cases < {RISK_THRESHOLDS['moderate_max_exclusive']}",
            "High Risk": f"confirmed_cases >= {RISK_THRESHOLDS['moderate_max_exclusive']}",
        },
        "test_size": test_size, "random_state": random_state,
        "target_classes": label_encoder.classes_.tolist(),
        "train_path": str(train_path), "test_path": str(test_path),
        "scaler_path": str(scaler_path), "label_encoder_path": str(encoder_path),
        "feature_columns": list(feature_frame.columns),
        "training_class_distribution": {str(k): int(v) for k, v in y_train.value_counts().items()},
        "testing_class_distribution": {str(k): int(v) for k, v in y_test.value_counts().items()},
    }


def write_html_report(path: Path, title: str, report: dict[str, Any]) -> None:
    def render(value: Any) -> str:
        if isinstance(value, dict):
            rows = "".join(
                f"<tr><th>{html.escape(str(key))}</th><td>{render(item)}</td></tr>"
                for key, item in value.items()
            )
            return f"<table>{rows}</table>"
        if isinstance(value, list):
            return "<ul>" + "".join(f"<li>{render(item)}</li>" for item in value) + "</ul>"
        return html.escape(str(value))

    path.parent.mkdir(parents=True, exist_ok=True)
    document = (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1"><title>'
        + html.escape(title)
        + '</title><style>body{font:15px/1.5 Arial,sans-serif;max-width:1100px;'
        'margin:2rem auto;padding:0 1rem;color:#24313d}h1{color:#00695c}'
        'table{border-collapse:collapse;width:100%;margin:1rem 0}'
        'th,td{border:1px solid #d4dde4;padding:.5rem;text-align:left;vertical-align:top}'
        'th{background:#e8f5f3}</style></head><body><h1>'
        + html.escape(title)
        + '</h1><p>Generated UTC: '
        + datetime.now(timezone.utc).isoformat()
        + '</p>' + render(report) + '</body></html>'
    )
    path.write_text(document, encoding="utf-8")


def run(dengue_csv: Path = DENGUE_CSV, climate_csv: Path = CLIMATE_CSV, merged_csv: Path = MERGED_CSV, processed_dir: Path = PROCESSED_DIR, test_size: float = 0.2, random_state: int = 42) -> tuple[pd.DataFrame, dict[str, Any]]:
    merged, validation_report = build_merged_dataset(dengue_csv, climate_csv)
    merged_csv.parent.mkdir(parents=True, exist_ok=True)
    merged.to_csv(merged_csv, index=False)
    validation_path = processed_dir / "validation_report.html"
    write_html_report(validation_path, "Dengue/Climate Dataset Validation Report", validation_report)
    preprocessing_report = preprocess_dataset(merged, processed_dir, test_size, random_state)
    preprocessing_report["source_rows"] = int(len(merged))
    preprocessing_report["merged_dataset_path"] = str(merged_csv)
    preprocessing_report["validation_report_path"] = str(validation_path)
    preprocessing_report["scaler_fit_on_training_rows_only"] = True
    preprocessing_report["model_trained"] = False
    write_html_report(processed_dir / "preprocessing_report.html", "Dengue/Climate Preprocessing Report", preprocessing_report)
    return merged, {"validation": validation_report, "preprocessing": preprocessing_report}


def main() -> int:
    parser = argparse.ArgumentParser(description="Merge existing NCVBDC and NASA POWER data; preprocess without model training.")
    parser.add_argument("--dengue", type=Path, default=DENGUE_CSV)
    parser.add_argument("--climate", type=Path, default=CLIMATE_CSV)
    parser.add_argument("--merged-output", type=Path, default=MERGED_CSV)
    parser.add_argument("--processed-dir", type=Path, default=PROCESSED_DIR)
    parser.add_argument("--test-size", type=float, default=0.2)
    parser.add_argument("--random-state", type=int, default=42)
    args = parser.parse_args()
    try:
        merged, reports = run(args.dengue, args.climate, args.merged_output, args.processed_dir, args.test_size, args.random_state)
    except (DatasetError, FileNotFoundError, OSError, ValueError) as error:
        print(f"Dataset merge/preprocessing failed: {error}", file=sys.stderr)
        return 1
    print(f"Merged dataset shape: {merged.shape}")
    print(f"Column names: {list(merged.columns)}")
    print(f"Missing values: {merged.isna().sum().to_dict()}")
    print(f"Target class distribution: {merged['outbreak_risk'].value_counts().to_dict()}")
    print(f"Training rows: {reports['preprocessing']['train_rows']}")
    print(f"Testing rows: {reports['preprocessing']['test_rows']}")
    print("First five rows:")
    print(merged.head().to_string(index=False))
    print(f"Merged dataset: {args.merged_output}")
    print(f"Processed artifacts: {args.processed_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
