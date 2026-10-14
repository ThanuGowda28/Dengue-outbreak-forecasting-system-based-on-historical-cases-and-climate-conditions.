from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.preprocessing import LabelEncoder, StandardScaler

from ..config import (
    DEFAULT_INPUT_PATH,
    DEFAULT_OUTPUT_DIR,
    DEFAULT_RANDOM_STATE,
    DEFAULT_TARGET_COLUMN,
    DEFAULT_TEST_SIZE,
    MISSING_CATEGORY,
    OUTLIER_IQR_MULTIPLIER,
)
from .data_validation import canonical_column_name, climate_range_key, validate_dataset
from .feature_engineering import engineer_features
from .split_dataset import split_dataset


@dataclass(frozen=True)
class PreprocessingResult:
    """Paths and concise metadata produced by preprocessing (no model is trained)."""

    output_dir: Path
    processed_dataset_path: Path
    train_path: Path
    test_path: Path
    scaler_path: Path
    label_encoder_path: Path
    report_path: Path
    report: dict[str, Any]


def preprocess_dataset(
    input_path: str | Path = DEFAULT_INPUT_PATH,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    target_column: str = DEFAULT_TARGET_COLUMN,
    test_size: float = DEFAULT_TEST_SIZE,
    random_state: int = DEFAULT_RANDOM_STATE,
    outlier_iqr_multiplier: float = OUTLIER_IQR_MULTIPLIER,
) -> PreprocessingResult:
    """Validate, clean, engineer, split, and transform a CSV dataset without training."""
    input_path = Path(input_path)
    output_dir = Path(output_dir)
    if not input_path.is_file():
        raise FileNotFoundError(f"Input CSV does not exist: {input_path}")
    if outlier_iqr_multiplier <= 0:
        raise ValueError("outlier_iqr_multiplier must be greater than zero.")

    try:
        source = pd.read_csv(input_path)
    except (OSError, pd.errors.ParserError, UnicodeError) as error:
        raise ValueError(f"Could not read CSV dataset '{input_path}': {error}") from error

    cleaned, validation_report = validate_dataset(source, target_column)
    target = canonical_column_name(target_column)
    duplicate_count = int(cleaned.duplicated().sum())
    cleaned = cleaned.drop_duplicates().copy()

    missing_target_count = int(cleaned[target].isna().sum())
    if missing_target_count:
        cleaned = cleaned.loc[cleaned[target].notna()].copy()
    if len(cleaned) < 2:
        raise ValueError("At least two rows with a valid target are required after cleaning.")

    engineered, feature_report = engineer_features(cleaned)
    x_train, x_test, y_train, y_test, split_report = split_dataset(
        engineered, target, test_size=test_size, random_state=random_state
    )

    climate_columns = [
        column
        for column in x_train.columns
        if climate_range_key(column) is not None
        and pd.api.types.is_numeric_dtype(x_train[column])
    ]
    x_train, x_test, outlier_report = _cap_climate_outliers(
        x_train, x_test, climate_columns, outlier_iqr_multiplier
    )

    categorical_columns = [
        column
        for column in x_train.columns
        if not pd.api.types.is_numeric_dtype(x_train[column])
        or pd.api.types.is_bool_dtype(x_train[column])
    ]
    numeric_columns = [column for column in x_train.columns if column not in categorical_columns]

    numeric_medians: dict[str, float] = {}
    for column in numeric_columns:
        numeric = pd.to_numeric(x_train[column], errors="coerce")
        median = numeric.median()
        numeric_medians[column] = float(median) if pd.notna(median) else 0.0
        x_train[column] = numeric.fillna(numeric_medians[column])
        x_test[column] = pd.to_numeric(x_test[column], errors="coerce").fillna(numeric_medians[column])

    categorical_fill_values = {column: MISSING_CATEGORY for column in categorical_columns}
    feature_encoders: dict[str, LabelEncoder] = {}
    unseen_category_counts: dict[str, int] = {}
    for column in categorical_columns:
        train_values = x_train[column].fillna(MISSING_CATEGORY).astype(str)
        test_values = x_test[column].fillna(MISSING_CATEGORY).astype(str)
        encoder = LabelEncoder()
        x_train[column] = encoder.fit_transform(train_values)
        known = set(encoder.classes_)
        unseen = ~test_values.isin(known)
        unseen_category_counts[column] = int(unseen.sum())
        x_test[column] = test_values.map(
            lambda value: int(encoder.transform([value])[0]) if value in known else -1
        ).astype(int)
        feature_encoders[column] = encoder

    scaler = StandardScaler() if numeric_columns else None
    if scaler is not None:
        scaled_train = scaler.fit_transform(x_train[numeric_columns])
        scaled_test = scaler.transform(x_test[numeric_columns])
        for position, column in enumerate(numeric_columns):
            x_train[column] = scaled_train[:, position]
            x_test[column] = scaled_test[:, position]

    target_encoder = None
    if not pd.api.types.is_numeric_dtype(y_train):
        target_encoder = LabelEncoder()
        all_target_values = pd.concat([y_train, y_test]).astype(str)
        target_encoder.fit(all_target_values)
        y_train = target_encoder.transform(y_train.astype(str))
        y_test = target_encoder.transform(y_test.astype(str))

    train = x_train.copy()
    train[target] = np.asarray(y_train)
    test = x_test.copy()
    test[target] = np.asarray(y_test)
    processed = pd.concat([train, test], axis=0).sort_index()

    output_dir.mkdir(parents=True, exist_ok=True)
    processed_path = output_dir / "processed_dataset.csv"
    train_path = output_dir / "train.csv"
    test_path = output_dir / "test.csv"
    scaler_path = output_dir / "scaler.joblib"
    label_encoder_path = output_dir / "label_encoder.joblib"
    imputer_path = output_dir / "imputer.joblib"
    report_path = output_dir / "preprocessing_report.json"

    processed.to_csv(processed_path, index=False)
    train.to_csv(train_path, index=False)
    test.to_csv(test_path, index=False)
    joblib.dump(scaler, scaler_path)
    joblib.dump({"features": feature_encoders, "target": target_encoder}, label_encoder_path)
    joblib.dump(
        {
            "numeric_medians": numeric_medians,
            "categorical_fill_values": categorical_fill_values,
            "outlier_bounds": outlier_report["bounds"],
            "numeric_columns": numeric_columns,
            "categorical_columns": categorical_columns,
            "feature_columns": list(x_train.columns),
            "target_column": target,
        },
        imputer_path,
    )

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "input_path": str(input_path.resolve()),
        "target_column": target,
        "rows_read": int(len(source)),
        "duplicate_rows_removed": duplicate_count,
        "rows_with_missing_target_removed": missing_target_count,
        "rows_processed": int(len(processed)),
        "validation": validation_report,
        "feature_engineering": feature_report,
        "outliers": outlier_report,
        "missing_values": {
            "numeric_medians": numeric_medians,
            "categorical_fill_values": categorical_fill_values,
        },
        "categorical_encoding": {
            "encoded_feature_columns": categorical_columns,
            "unseen_test_categories_mapped_to_minus_one": unseen_category_counts,
            "target_encoded": target_encoder is not None,
            "target_classes": target_encoder.classes_.tolist() if target_encoder is not None else [],
        },
        "scaling": {
            "method": "StandardScaler",
            "columns": numeric_columns,
            "fitted_on_training_rows_only": True,
        },
        "split": split_report,
        "outputs": {
            "processed_dataset": str(processed_path),
            "train": str(train_path),
            "test": str(test_path),
            "scaler": str(scaler_path),
            "label_encoder": str(label_encoder_path),
            "imputer": str(imputer_path),
        },
        "model_trained": False,
    }
    report_path.write_text(json.dumps(report, indent=2, allow_nan=False), encoding="utf-8")
    return PreprocessingResult(
        output_dir=output_dir,
        processed_dataset_path=processed_path,
        train_path=train_path,
        test_path=test_path,
        scaler_path=scaler_path,
        label_encoder_path=label_encoder_path,
        report_path=report_path,
        report=report,
    )


def _cap_climate_outliers(
    x_train: pd.DataFrame,
    x_test: pd.DataFrame,
    columns: list[str],
    multiplier: float,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    train = x_train.copy()
    test = x_test.copy()
    bounds: dict[str, dict[str, float]] = {}
    counts: dict[str, dict[str, int]] = {}
    for column in columns:
        values = pd.to_numeric(train[column], errors="coerce")
        q1, q3 = values.quantile([0.25, 0.75])
        if pd.isna(q1) or pd.isna(q3):
            continue
        iqr = float(q3 - q1)
        lower = float(q1 - multiplier * iqr)
        upper = float(q3 + multiplier * iqr)
        train_outliers = values.notna() & ((values < lower) | (values > upper))
        test_values = pd.to_numeric(test[column], errors="coerce")
        test_outliers = test_values.notna() & ((test_values < lower) | (test_values > upper))
        bounds[column] = {"lower": lower, "upper": upper}
        counts[column] = {
            "train": int(train_outliers.sum()),
            "test": int(test_outliers.sum()),
        }
        train[column] = values.clip(lower=lower, upper=upper)
        test[column] = test_values.clip(lower=lower, upper=upper)
    return train, test, {
        "method": "IQR clipping",
        "iqr_multiplier": multiplier,
        "bounds_fit_on_training_rows_only": True,
        "bounds": bounds,
        "clipped_counts": counts,
    }


def _main() -> None:
    parser = argparse.ArgumentParser(description="Preprocess dengue/climate CSV data; does not train a model.")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT_PATH, help="Source CSV path")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR, help="Output directory")
    parser.add_argument("--target", default=DEFAULT_TARGET_COLUMN, help="Target column name")
    parser.add_argument("--test-size", type=float, default=DEFAULT_TEST_SIZE)
    parser.add_argument("--random-state", type=int, default=DEFAULT_RANDOM_STATE)
    args = parser.parse_args()
    result = preprocess_dataset(
        input_path=args.input,
        output_dir=args.output_dir,
        target_column=args.target,
        test_size=args.test_size,
        random_state=args.random_state,
    )
    print(f"Preprocessing complete (no model trained). Report: {result.report_path}")


if __name__ == "__main__":
    _main()
