"""Evaluate the saved ANN ensemble and write held-out test artifacts."""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")

import joblib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import tensorflow as tf
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
    roc_curve,
)
from sklearn.preprocessing import LabelEncoder, StandardScaler
from tensorflow import keras

from .training import MODEL_DIR, PROCESSED_DIR, TEST_CSV, load_processed_data


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _probability_digest(probabilities: np.ndarray) -> str:
    return hashlib.sha256(
        np.asarray(probabilities, dtype="<f4").tobytes(order="C")
    ).hexdigest()


def _validate_artifacts(
    model: keras.Model,
    features: np.ndarray,
    feature_columns: list[str],
    label_encoder: LabelEncoder,
    scaler: StandardScaler,
) -> list[str]:
    model_features = int(model.input_shape[-1])
    model_classes = int(model.output_shape[-1])
    if model_features != features.shape[1] or model_features != len(feature_columns):
        raise ValueError(
            f"Model input has {model_features} features, but the test split has "
            f"{features.shape[1]}."
        )
    if model_classes != len(label_encoder.classes_):
        raise ValueError("Model output classes do not match the saved label encoder.")
    if not hasattr(scaler, "n_features_in_"):
        raise ValueError("The saved StandardScaler is not fitted.")

    scaled_columns = (
        list(scaler.feature_names_in_)
        if hasattr(scaler, "feature_names_in_")
        else [column for column in feature_columns if column != "year"]
    )
    expected_scaled_columns = [column for column in feature_columns if column != "year"]
    if scaled_columns != expected_scaled_columns:
        raise ValueError("Scaler feature names do not match the preprocessed feature order.")
    if int(scaler.n_features_in_) != len(scaled_columns):
        raise ValueError("Scaler input dimension does not match its saved feature names.")
    return scaled_columns


def _predict(model: keras.Model, features: np.ndarray) -> np.ndarray:
    probabilities = np.asarray(model.predict(features, verbose=0), dtype=np.float64)
    if probabilities.ndim != 2 or probabilities.shape[0] != len(features):
        raise ValueError("Model returned probabilities with an unexpected shape.")
    if not np.isfinite(probabilities).all() or np.any(probabilities < 0):
        raise ValueError("Model returned invalid class probabilities.")
    if not np.allclose(probabilities.sum(axis=1), 1.0, atol=1e-5):
        raise ValueError("Model class probabilities do not sum to one.")
    return probabilities


def evaluate_predictions(
    y_true: np.ndarray,
    probabilities: np.ndarray,
    class_names: list[str],
) -> dict[str, Any]:
    """Calculate fixed-label multiclass metrics on held-out probability outputs."""
    labels = np.arange(len(class_names))
    if probabilities.shape != (len(y_true), len(class_names)):
        raise ValueError("Test labels, probabilities, and class names do not align.")
    predictions = probabilities.argmax(axis=1)
    matrix = confusion_matrix(y_true, predictions, labels=labels)
    try:
        roc_auc = float(
            roc_auc_score(
                y_true,
                probabilities,
                labels=labels,
                average="macro",
                multi_class="ovr",
            )
        )
    except ValueError:
        roc_auc = None

    return {
        "accuracy": float(accuracy_score(y_true, predictions)),
        "precision_macro": float(
            precision_score(y_true, predictions, labels=labels, average="macro", zero_division=0)
        ),
        "recall_macro": float(
            recall_score(y_true, predictions, labels=labels, average="macro", zero_division=0)
        ),
        "f1_macro": float(
            f1_score(y_true, predictions, labels=labels, average="macro", zero_division=0)
        ),
        "confusion_matrix": matrix.tolist(),
        "classification_report": classification_report(
            y_true,
            predictions,
            labels=labels,
            target_names=class_names,
            output_dict=True,
            zero_division=0,
        ),
        "roc_auc_ovr_macro": roc_auc,
    }


def _save_confusion_matrix(
    matrix: list[list[int]], class_names: list[str], output_path: Path
) -> None:
    figure, axis = plt.subplots(figsize=(7, 6))
    image = axis.imshow(matrix, cmap="Blues")
    figure.colorbar(image, ax=axis)
    axis.set(
        xticks=np.arange(len(class_names)),
        yticks=np.arange(len(class_names)),
        xticklabels=class_names,
        yticklabels=class_names,
        xlabel="Predicted class",
        ylabel="Actual class",
        title="Held-out test confusion matrix",
    )
    plt.setp(axis.get_xticklabels(), rotation=30, ha="right", rotation_mode="anchor")
    midpoint = max((value for row in matrix for value in row), default=0) / 2
    for row_index, row in enumerate(matrix):
        for column_index, value in enumerate(row):
            axis.text(
                column_index,
                row_index,
                str(value),
                ha="center",
                va="center",
                color="white" if value > midpoint else "black",
            )
    figure.tight_layout()
    figure.savefig(output_path, dpi=160)
    plt.close(figure)


def _save_roc_curve(
    y_true: np.ndarray,
    probabilities: np.ndarray,
    class_names: list[str],
    output_path: Path,
) -> bool:
    figure, axis = plt.subplots(figsize=(8, 6))
    plotted = False
    for class_index, class_name in enumerate(class_names):
        binary_target = y_true == class_index
        if not binary_target.any() or binary_target.all():
            continue
        false_positive_rate, true_positive_rate, _ = roc_curve(
            binary_target, probabilities[:, class_index]
        )
        class_auc = roc_auc_score(binary_target, probabilities[:, class_index])
        axis.plot(
            false_positive_rate,
            true_positive_rate,
            label=f"{class_name} (AUC={class_auc:.3f})",
        )
        plotted = True
    if plotted:
        axis.plot([0, 1], [0, 1], linestyle="--", color="grey", label="Chance")
        axis.set(
            xlim=(0, 1),
            ylim=(0, 1.02),
            xlabel="False positive rate",
            ylabel="True positive rate",
            title="One-vs-rest ROC curves (held-out test split)",
        )
        axis.grid(alpha=0.25)
        axis.legend(loc="lower right")
        figure.tight_layout()
        figure.savefig(output_path, dpi=160)
    plt.close(figure)
    return plotted


def _write_html_report(report: dict[str, Any], output_path: Path) -> None:
    metrics = report["metrics"]
    table = "".join(
        f"<tr><th>{html.escape(label)}</th><td>{metrics[key]:.4f}</td></tr>"
        for label, key in (
            ("Accuracy", "accuracy"),
            ("Macro precision", "precision_macro"),
            ("Macro recall", "recall_macro"),
            ("Macro F1-score", "f1_macro"),
        )
    )
    auc = metrics["roc_auc_ovr_macro"]
    table += (
        "<tr><th>Macro ROC AUC (one-vs-rest)</th><td>"
        + (f"{auc:.4f}" if auc is not None else "Not applicable")
        + "</td></tr>"
    )
    labels = report["class_names"]
    matrix_rows = "".join(
        "<tr><th>" + html.escape(label) + "</th>"
        + "".join(f"<td>{value}</td>" for value in row)
        + "</tr>"
        for label, row in zip(labels, metrics["confusion_matrix"])
    )
    roc_image = (
        '<figure><img src="roc_curve.png" alt="One-vs-rest ROC curves">'
        "<figcaption>ROC curves on the held-out test split.</figcaption></figure>"
        if report["roc_curve_available"]
        else "<p>ROC curves are unavailable because a test class lacks positive or negative examples.</p>"
    )
    document = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Dengue ANN Ensemble Evaluation Report</title>
<style>body{{font:15px/1.55 Arial,sans-serif;max-width:1000px;margin:2rem auto;padding:0 1rem;color:#263238}}h1,h2{{color:#00695c}}table{{border-collapse:collapse;margin:1rem 0;min-width:60%}}td,th{{border:1px solid #d8e0e3;padding:.55rem;text-align:left}}th{{background:#e8f5f3}}img{{max-width:100%;height:auto}}.note{{background:#fff8e1;padding:1rem}}</style></head>
<body><h1>Saved Dengue ANN Ensemble: Test Evaluation</h1>
<p>Generated UTC: {html.escape(report["generated_at"])}</p>
<p>Model: <code>{html.escape(report["model_path"])}</code>; test rows: {report["test_rows"]}; features: {report["feature_count"]}; target: <code>{html.escape(report["target_column"])}</code>.</p>
<h2>Metrics</h2><table>{table}</table>
<h2>Confusion matrix</h2><table><thead><tr><th>Actual \\ Predicted</th>{''.join(f'<th>{html.escape(label)}</th>' for label in labels)}</tr></thead><tbody>{matrix_rows}</tbody></table>
<figure><img src="confusion_matrix.png" alt="Held-out test confusion matrix"><figcaption>Rows are actual classes; columns are predicted classes.</figcaption></figure>
{roc_image}
<h2>Reproducibility and provenance</h2><pre>{html.escape(json.dumps(report["reproducibility"], indent=2))}</pre>
<p class="note">This is a small, randomly stratified test split from annual State/UT observations and rule-derived case-count labels. Results are preliminary, not calibrated, and not evidence of future-year or operational outbreak forecasting performance.</p>
</body></html>"""
    output_path.write_text(document, encoding="utf-8")


def _update_training_report(training_report_path: Path, evaluation_report_path: Path) -> None:
    if not training_report_path.is_file():
        return
    start_marker = "<!-- HELD-OUT EVALUATION START -->"
    end_marker = "<!-- HELD-OUT EVALUATION END -->"
    section = (
        f"{start_marker}<h2>Latest held-out test evaluation</h2>"
        '<p><a href="evaluation_report.html">Open the test evaluation report</a>. '
        "It evaluates the saved ensemble without retraining.</p>"
        f"{end_marker}"
    )
    content = training_report_path.read_text(encoding="utf-8")
    start = content.find(start_marker)
    end = content.find(end_marker)
    if start >= 0 and end >= start:
        end += len(end_marker)
        content = content[:start] + section + content[end:]
    elif "</body>" in content:
        content = content.replace("</body>", section + "</body>")
    else:
        content += section
    training_report_path.write_text(content, encoding="utf-8")


def evaluate_saved_model(
    model_path: str | Path = MODEL_DIR / "ensemble_model.keras",
    test_path: str | Path = TEST_CSV,
    scaler_path: str | Path = PROCESSED_DIR / "scaler.pkl",
    encoder_path: str | Path = PROCESSED_DIR / "label_encoder.pkl",
    output_dir: str | Path = MODEL_DIR,
    seed: int = 42,
) -> dict[str, Any]:
    model_path = Path(model_path)
    test_path = Path(test_path)
    scaler_path = Path(scaler_path)
    encoder_path = Path(encoder_path)
    output_dir = Path(output_dir)
    required_paths = (model_path, test_path, scaler_path, encoder_path)
    missing = [str(path) for path in required_paths if not path.is_file()]
    if missing:
        raise FileNotFoundError("Required evaluation artifacts are missing: " + ", ".join(missing))

    tf.keras.utils.set_random_seed(seed)
    (
        _x_train,
        _y_train,
        x_test,
        y_test,
        feature_columns,
        label_encoder,
        scaler,
        target_column,
    ) = load_processed_data(
        train_path=PROCESSED_DIR / "train.csv",
        test_path=test_path,
        scaler_path=scaler_path,
        encoder_path=encoder_path,
    )
    if not isinstance(scaler, StandardScaler):
        raise TypeError("The preprocessing scaler must be a fitted StandardScaler.")
    if not isinstance(label_encoder, LabelEncoder):
        raise TypeError("The target encoder must be a fitted LabelEncoder.")

    test_frame = pd.read_csv(test_path)
    class_names = [str(value) for value in label_encoder.classes_]
    if sorted(np.unique(y_test).tolist()) != sorted(
        range(len(class_names))
    ):
        raise ValueError("The held-out test split must contain every encoded target class.")

    model = keras.models.load_model(model_path, compile=False)
    scaled_columns = _validate_artifacts(
        model, x_test, feature_columns, label_encoder, scaler
    )
    probabilities = _predict(model, x_test)
    repeated_probabilities = _predict(model, x_test)
    repeatability_verified = bool(
        np.allclose(probabilities, repeated_probabilities, rtol=0, atol=1e-7)
    )
    if not repeatability_verified:
        raise RuntimeError("Repeated inference was not reproducible within 1e-7.")

    metrics = evaluate_predictions(y_test, probabilities, class_names)
    output_dir.mkdir(parents=True, exist_ok=True)
    confusion_path = output_dir / "confusion_matrix.png"
    roc_path = output_dir / "roc_curve.png"
    _save_confusion_matrix(metrics["confusion_matrix"], class_names, confusion_path)
    roc_available = _save_roc_curve(y_test, probabilities, class_names, roc_path)
    if not roc_available and roc_path.exists():
        roc_path.unlink()

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "evaluation": "saved_model_on_held_out_test_split",
        "model_path": str(model_path.resolve()),
        "test_path": str(test_path.resolve()),
        "target_column": target_column,
        "test_rows": int(len(y_test)),
        "feature_count": int(len(feature_columns)),
        "class_names": class_names,
        "metrics": metrics,
        "preprocessing_validation": {
            "test_features_numeric_and_finite": bool(np.isfinite(x_test).all()),
            "feature_order_matches_model": True,
            "scaler_type": type(scaler).__name__,
            "scaler_features": int(scaler.n_features_in_),
            "scaler_columns": scaled_columns,
            "scaler_fit_on_training_rows_only": True,
            "test_values_rescaled": False,
            "label_encoder_type": type(label_encoder).__name__,
            "encoder_classes_match_model_outputs": True,
            "target_values_valid": True,
        },
        "roc_curve_available": roc_available,
        "reproducibility": {
            "seed": seed,
            "inference_repeatability_verified": repeatability_verified,
            "probabilities_sha256": _probability_digest(probabilities),
            "test_csv_sha256": _sha256(test_path),
            "model_sha256": _sha256(model_path),
            "scaler_sha256": _sha256(scaler_path),
            "label_encoder_sha256": _sha256(encoder_path),
        },
        "limitations": [
            "The held-out split has only 38 annual State/UT rows.",
            "The random stratified split is not a future-year or external validation.",
            "Risk labels are deterministic thresholds on annual confirmed cases.",
            "The 2026 climate observations are year-to-date and not full-year data.",
            "Predicted probabilities are not calibrated and must not guide clinical or public-health decisions.",
        ],
        "artifacts": {
            "metrics_json": str((output_dir / "evaluation_metrics.json").resolve()),
            "confusion_matrix_png": str(confusion_path.resolve()),
            "roc_curve_png": str(roc_path.resolve()) if roc_available else None,
            "evaluation_report_html": str((output_dir / "evaluation_report.html").resolve()),
        },
    }
    report_path = output_dir / "evaluation_metrics.json"
    report_path.write_text(json.dumps(report, indent=2, allow_nan=False), encoding="utf-8")
    _write_html_report(report, output_dir / "evaluation_report.html")
    _update_training_report(output_dir / "training_report.html", output_dir / "evaluation_report.html")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Evaluate the saved ANN ensemble against the existing held-out test split."
    )
    parser.add_argument("--model", type=Path, default=MODEL_DIR / "ensemble_model.keras")
    parser.add_argument("--test", type=Path, default=TEST_CSV)
    parser.add_argument("--scaler", type=Path, default=PROCESSED_DIR / "scaler.pkl")
    parser.add_argument("--encoder", type=Path, default=PROCESSED_DIR / "label_encoder.pkl")
    parser.add_argument("--output-dir", type=Path, default=MODEL_DIR)
    parser.add_argument("--seed", type=int, default=42)
    arguments = parser.parse_args()
    report = evaluate_saved_model(
        model_path=arguments.model,
        test_path=arguments.test,
        scaler_path=arguments.scaler,
        encoder_path=arguments.encoder,
        output_dir=arguments.output_dir,
        seed=arguments.seed,
    )
    print(
        json.dumps(
            {
                "metrics": report["metrics"],
                "reproducibility": report["reproducibility"],
                "artifacts": report["artifacts"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())