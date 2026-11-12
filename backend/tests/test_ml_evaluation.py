import json
import tempfile
import unittest
from pathlib import Path

import numpy as np

from backend.app.ml.evaluate_model import evaluate_predictions, evaluate_saved_model


class ModelEvaluationTests(unittest.TestCase):
    def test_evaluate_predictions_returns_multiclass_metrics_and_roc_auc(self):
        actual = np.asarray([0, 0, 1, 1, 2, 2])
        probabilities = np.asarray(
            [
                [0.8, 0.1, 0.1],
                [0.6, 0.3, 0.1],
                [0.2, 0.7, 0.1],
                [0.1, 0.8, 0.1],
                [0.1, 0.2, 0.7],
                [0.2, 0.1, 0.7],
            ]
        )

        metrics = evaluate_predictions(
            actual, probabilities, ["High Risk", "Low Risk", "Moderate Risk"]
        )

        self.assertEqual(metrics["accuracy"], 1.0)
        self.assertEqual(metrics["precision_macro"], 1.0)
        self.assertEqual(metrics["recall_macro"], 1.0)
        self.assertEqual(metrics["f1_macro"], 1.0)
        self.assertEqual(
            metrics["confusion_matrix"],
            [[2, 0, 0], [0, 2, 0], [0, 0, 2]],
        )
        self.assertEqual(metrics["roc_auc_ovr_macro"], 1.0)

    def test_saved_ensemble_evaluation_is_reproducible_and_writes_reports(self):
        try:
            import tensorflow  # noqa: F401
        except ImportError as error:
            if "Application Control policy has blocked this file" in str(error):
                self.skipTest(
                    "TensorFlow native components are blocked by Windows Application Control."
                )
            raise

        with tempfile.TemporaryDirectory() as temp_directory:
            output = Path(temp_directory)
            report = evaluate_saved_model(
                output_dir=output,
                seed=42,
            )
            persisted = json.loads(
                (output / "evaluation_metrics.json").read_text(encoding="utf-8")
            )

            self.assertTrue(report["preprocessing_validation"]["feature_order_matches_model"])
            self.assertEqual(report["preprocessing_validation"]["scaler_features"], 47)
            self.assertEqual(report["feature_count"], 48)
            self.assertEqual(
                report["class_names"],
                ["High Risk", "Low Risk", "Moderate Risk"],
            )
            self.assertTrue(report["preprocessing_validation"]["scaler_fit_on_training_rows_only"])
            self.assertTrue(report["reproducibility"]["inference_repeatability_verified"])
            self.assertTrue(report["roc_curve_available"])
            self.assertEqual(persisted["metrics"], report["metrics"])
            self.assertTrue((output / "confusion_matrix.png").is_file())
            self.assertTrue((output / "roc_curve.png").is_file())
            self.assertTrue((output / "evaluation_report.html").is_file())
            self.assertTrue(report["metrics"]["confusion_matrix"])
            self.assertEqual(report["test_rows"], 38)


if __name__ == "__main__":
    unittest.main()