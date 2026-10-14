from __future__ import annotations

import os
from pathlib import Path

ML_PACKAGE_DIR = Path(__file__).resolve().parent
DATASET_DIR = Path(os.getenv("ML_DATASET_DIR", ML_PACKAGE_DIR / "dataset"))
DEFAULT_INPUT_PATH = Path(os.getenv("ML_INPUT_CSV", DATASET_DIR / "dengue_climate.csv"))
DEFAULT_OUTPUT_DIR = Path(os.getenv("ML_PREPROCESSING_OUTPUT_DIR", DATASET_DIR / "processed"))
DEFAULT_TARGET_COLUMN = os.getenv("ML_TARGET_COLUMN", "dengue_cases")
DEFAULT_TEST_SIZE = float(os.getenv("ML_TEST_SIZE", "0.2"))
DEFAULT_RANDOM_STATE = int(os.getenv("ML_RANDOM_STATE", "42"))
OUTLIER_IQR_MULTIPLIER = float(os.getenv("ML_OUTLIER_IQR_MULTIPLIER", "1.5"))
MISSING_CATEGORY = "__missing__"
