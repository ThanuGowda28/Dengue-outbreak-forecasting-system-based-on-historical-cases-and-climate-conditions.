import tempfile
import unittest
from pathlib import Path

import pandas as pd

try:
    from backend.app.ml.preprocessing.preprocessing import preprocess_dataset
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
class PreprocessingPipelineTests(unittest.TestCase):
    def test_pipeline_cleans_splits_scales_and_writes_artifacts_without_training(self):
        rows = []
        for index in range(24):
            rows.append(
                {
                    "Weather Date": f"2025-01-{index + 1:02d}",
                    "District": "Mysuru" if index % 2 else "Bengaluru",
                    "Temperature C": 25.0 + index / 10,
                    "Humidity Pct": 60 + index % 10,
                    "Rainfall Mm": float(index % 4),
                    "Dengue Cases": index + 1,
                }
            )
        rows[3]["Temperature C"] = 120
        rows[20]["Temperature C"] = 58
        rows.append(rows[0].copy())

        with tempfile.TemporaryDirectory() as temp_dir:
            source = Path(temp_dir) / "climate.csv"
            output = Path(temp_dir) / "processed"
            pd.DataFrame(rows).to_csv(source, index=False)
            result = preprocess_dataset(
                input_path=source,
                output_dir=output,
                target_column="Dengue Cases",
                test_size=0.25,
                random_state=7,
            )

            self.assertTrue(result.processed_dataset_path.is_file())
            self.assertTrue(result.train_path.is_file())
            self.assertTrue(result.test_path.is_file())
            self.assertTrue(result.scaler_path.is_file())
            self.assertTrue(result.label_encoder_path.is_file())
            self.assertTrue(result.report_path.is_file())
            self.assertEqual(result.report["duplicate_rows_removed"], 1)
            self.assertEqual(result.report["validation"]["invalid_climate_values"]["temperature_c"], 1)
            self.assertFalse(result.report["model_trained"])
            self.assertEqual(
                len(pd.read_csv(result.train_path)) + len(pd.read_csv(result.test_path)),
                result.report["rows_processed"],
            )
            self.assertFalse(pd.read_csv(result.processed_dataset_path).isna().any().any())


if __name__ == "__main__":
    unittest.main()
