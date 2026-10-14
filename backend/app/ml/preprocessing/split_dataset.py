from __future__ import annotations

from typing import Any

import pandas as pd
from sklearn.model_selection import train_test_split


def split_dataset(
    frame: pd.DataFrame,
    target_column: str,
    test_size: float = 0.2,
    random_state: int = 42,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.Series, dict[str, Any]]:
    """Split rows into train/test partitions without fitting transformations."""
    if target_column not in frame.columns:
        raise ValueError(f"Target column '{target_column}' is missing.")
    if len(frame) < 2:
        raise ValueError("At least two labeled rows are required for a train/test split.")
    if not 0 < test_size < 1:
        raise ValueError("test_size must be greater than 0 and less than 1.")

    features = frame.drop(columns=[target_column])
    target = frame[target_column]
    stratify = None
    stratification_used = False
    if not pd.api.types.is_numeric_dtype(target):
        class_counts = target.value_counts(dropna=True)
        test_count = max(1, int(round(len(frame) * test_size)))
        if len(class_counts) > 1 and class_counts.min() >= 2 and test_count >= len(class_counts):
            stratify = target
            stratification_used = True

    x_train, x_test, y_train, y_test = train_test_split(
        features,
        target,
        test_size=test_size,
        random_state=random_state,
        stratify=stratify,
    )
    return x_train, x_test, y_train, y_test, {
        "train_rows": int(len(x_train)),
        "test_rows": int(len(x_test)),
        "test_size": test_size,
        "random_state": random_state,
        "stratified": stratification_used,
    }
