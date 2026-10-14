import tempfile
import unittest
from pathlib import Path

import joblib
import pandas as pd

try:
    from backend.app.ml.dataset.merge_and_preprocess import (
        CLIMATE_CSV,
        DENGUE_CSV,
        FEATURE_COLUMNS,
        MERGED_CSV,
        PROCESSED_DIR,
        RISK_THRESHOLDS,
        build_merged_dataset,
        preprocess_dataset,
        run,
    )
except ImportError as error:
    if "Application Control policy has blocked this file" not in str(error):
        raise
    PREPROCESSING_IMPORT_ERROR = str(error)
else:
    PREPROCESSING_IMPORT_ERROR = None


@unittest.skipIf(
    PREPROCESSING_IMPORT_ERROR is not None,
    f"scikit-learn is blocked by Windows Application Control: {PREPROCESSING_IMPORT_ERROR}",
)
class ExistingDatasetMergeTests(unittest.TestCase):
    def test_merge_uses_existing_sources_and_creates_ml_splits(self):
        self.assertTrue(DENGUE_CSV.is_file())
        self.assertTrue(CLIMATE_CSV.is_file())
        merged, report = build_merged_dataset()

        self.assertGreater(len(merged), 0)
        self.assertEqual(merged.duplicated(["state_ut", "year"]).sum(), 0)
        self.assertFalse(merged.isna().any().any())
        self.assertEqual(set(merged["outbreak_risk"].unique()), {"Low Risk", "Moderate Risk", "High Risk"})
        self.assertEqual(report["target_thresholds"]["Low Risk"], f"confirmed_cases < {RISK_THRESHOLDS['low_max_exclusive']}")
        self.assertTrue(set(FEATURE_COLUMNS).issubset(merged.columns))
        self.assertNotIn("month", merged.columns)

        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir)
            preprocessing = preprocess_dataset(merged, output)
            train = pd.read_csv(preprocessing["train_path"])
            test = pd.read_csv(preprocessing["test_path"])
            self.assertEqual(len(train), preprocessing["train_rows"])
            self.assertEqual(len(test), preprocessing["test_rows"])
            self.assertEqual(len(train) + len(test), len(merged))
            self.assertTrue((output / "scaler.pkl").is_file())
            self.assertTrue((output / "label_encoder.pkl").is_file())
            self.assertIsNotNone(joblib.load(output / "scaler.pkl"))
            self.assertEqual(joblib.load(output / "label_encoder.pkl").classes_.tolist(), ["High Risk", "Low Risk", "Moderate Risk"])

    def test_run_writes_requested_persistent_artifacts(self):
        self.assertTrue(MERGED_CSV.is_file())
        self.assertTrue((PROCESSED_DIR / "train.csv").is_file())
        self.assertTrue((PROCESSED_DIR / "test.csv").is_file())
        self.assertTrue((PROCESSED_DIR / "scaler.pkl").is_file())
        self.assertTrue((PROCESSED_DIR / "label_encoder.pkl").is_file())
        self.assertTrue((PROCESSED_DIR / "preprocessing_report.html").is_file())
        self.assertTrue((PROCESSED_DIR / "validation_report.html").is_file())
        self.assertTrue(pd.read_csv(MERGED_CSV).shape[0] > 0)


if __name__ == "__main__":
    unittest.main()
