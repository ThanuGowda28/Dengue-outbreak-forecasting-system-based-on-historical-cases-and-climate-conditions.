"""Train/evaluate three Keras ANNs and their soft-voting ensemble.

This is a standalone offline script. It reads existing processed CSVs and does
not import Flask or alter the dataset/preprocessing pipeline.
"""
from __future__ import annotations

import argparse
import html
import json
import os
import random
import shutil
import sys
import tempfile
import time
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
)
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder, StandardScaler
from tensorflow import keras
from tensorflow.keras import layers

ML_DIR = Path(__file__).resolve().parent
DATASET_DIR = ML_DIR / "dataset"
PROCESSED_DIR = DATASET_DIR / "processed"
MODEL_DIR = ML_DIR / "models"
TRAIN_CSV = PROCESSED_DIR / "train.csv"
TEST_CSV = PROCESSED_DIR / "test.csv"
SCALER_PATH = PROCESSED_DIR / "scaler.pkl"
ENCODER_PATH = PROCESSED_DIR / "label_encoder.pkl"

MODEL_NAMES = ("ANN1", "ANN2", "ANN3", "Ensemble")
CONFIDENCE_EXCLUDED = {"confirmed_cases", "deaths"}
MAX_EPOCHS = 200
EARLY_STOPPING_PATIENCE = 18
LR_PATIENCE = 7
MIN_DELTA = 1e-4
SEED = 42


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if isinstance(value, np.ndarray):
        return _json_safe(value.tolist())
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        number = float(value)
        return number if np.isfinite(number) else None
    if isinstance(value, (float,)):
        return value if np.isfinite(value) else None
    if isinstance(value, (np.bool_,)):
        return bool(value)
    return value


def load_processed_data(
    train_path: Path = TRAIN_CSV,
    test_path: Path = TEST_CSV,
    scaler_path: Path = SCALER_PATH,
    encoder_path: Path = ENCODER_PATH,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, list[str], LabelEncoder, StandardScaler, str]:
    for path in (train_path, test_path):
        if not path.is_file():
            raise FileNotFoundError(f"Required processed data/artifact is missing: {path}")

    train = pd.read_csv(train_path)
    test = pd.read_csv(test_path)
    if train.empty or test.empty:
        raise ValueError("Processed training and testing CSVs must both contain rows.")
    if list(train.columns) != list(test.columns):
        raise ValueError("Training and testing CSVs must have identical columns in identical order.")

    target_candidates = [name for name in ("outbreak_risk", "target", "label", "class") if name in train.columns]
    target_column = target_candidates[0] if target_candidates else train.columns[-1]
    feature_columns = [
        column for column in train.columns
        if column != target_column and column.casefold() not in CONFIDENCE_EXCLUDED
    ]
    if not feature_columns:
        raise ValueError("No model features remain after excluding the target and label-derived fields.")

    x_train_frame = train[feature_columns].apply(pd.to_numeric, errors="coerce")
    x_test_frame = test[feature_columns].apply(pd.to_numeric, errors="coerce")
    if x_train_frame.isna().any().any() or x_test_frame.isna().any().any():
        raise ValueError("Processed feature columns contain missing or nonnumeric values.")
    x_train = x_train_frame.to_numpy(dtype=np.float32)
    x_test = x_test_frame.to_numpy(dtype=np.float32)
    if not np.isfinite(x_train).all() or not np.isfinite(x_test).all():
        raise ValueError("Processed features contain non-finite values.")

    if scaler_path.is_file():
        try:
            scaler = joblib.load(scaler_path)
        except Exception as error:
            raise ValueError(f"Could not load scaler artifact: {error}") from error
        if not isinstance(scaler, StandardScaler):
            raise TypeError(f"Expected a fitted StandardScaler, found {type(scaler).__name__}.")
    else:
        scaler = StandardScaler().fit(x_train)
        scaler_path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(scaler, scaler_path)

    if encoder_path.is_file():
        try:
            label_encoder = joblib.load(encoder_path)
        except Exception as error:
            raise ValueError(f"Could not load label encoder artifact: {error}") from error
        if not isinstance(label_encoder, LabelEncoder):
            raise TypeError(f"Expected a fitted LabelEncoder, found {type(label_encoder).__name__}.")
    else:
        target_values = train[target_column]
        if target_values.isna().any():
            raise ValueError("Training target contains missing values.")
        numeric_target = pd.to_numeric(target_values, errors="coerce")
        encoder_values = numeric_target.to_numpy() if numeric_target.notna().all() else target_values.astype(str)
        label_encoder = LabelEncoder().fit(encoder_values)
        encoder_path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(label_encoder, encoder_path)

    if not hasattr(label_encoder, "classes_") or len(label_encoder.classes_) < 2:
        raise ValueError("The label encoder must contain at least two fitted classes.")

    def encode_target(series: pd.Series, name: str) -> np.ndarray:
        if series.isna().any():
            raise ValueError(f"{name} target contains missing values.")
        values = pd.to_numeric(series, errors="coerce")
        if values.notna().all():
            encoded = values.to_numpy(dtype=np.int64)
            if not np.equal(values.to_numpy(), encoded).all():
                raise ValueError(f"{name} target codes must be integers.")
            if np.any(encoded < 0) or np.any(encoded >= len(label_encoder.classes_)):
                raise ValueError(f"{name} contains class indices not represented by label_encoder.pkl.")
            return encoded
        try:
            return label_encoder.transform(series.astype(str))
        except ValueError as error:
            raise ValueError(f"{name} contains target labels absent from label_encoder.pkl: {error}") from error

    y_train = encode_target(train[target_column], "Training")
    y_test = encode_target(test[target_column], "Testing")
    if len(np.unique(y_train)) < 2:
        raise ValueError("Training data must contain at least two target classes.")
    if not set(np.unique(y_test)).issubset(set(np.unique(y_train))):
        raise ValueError("Test data contains a target class absent from training data.")
    return x_train, y_train, x_test, y_test, feature_columns, label_encoder, scaler, target_column


def select_hyperparameters(row_count: int) -> dict[str, Any]:
    """Choose conservative fit parameters from the available training sample size."""
    batch_size = min(32, max(8, int(round(np.sqrt(row_count)))))
    validation_fraction = 0.2 if row_count >= 30 else 0.15
    validation_rows = max(2, int(round(row_count * validation_fraction)))
    validation_rows = min(validation_rows, row_count - 2)
    effective_validation_fraction = validation_rows / row_count
    return {
        "max_epochs": MAX_EPOCHS,
        "batch_size": batch_size,
        "validation_split": round(effective_validation_fraction, 4),
        "validation_rows": validation_rows,
        "early_stopping_patience": EARLY_STOPPING_PATIENCE,
        "reduce_lr_patience": LR_PATIENCE,
        "optimizer": "Adam",
        "loss": "categorical_crossentropy",
        "seed": SEED,
    }


def build_ann1(input_dim: int, class_count: int) -> keras.Model:
    inputs = keras.Input(shape=(input_dim,), name="features")
    x = layers.Dense(128, activation="relu", name="dense_128")(inputs)
    x = layers.Dropout(0.30, name="dropout_030")(x)
    x = layers.Dense(64, activation="relu", name="dense_64")(x)
    x = layers.Dropout(0.20, name="dropout_020")(x)
    outputs = layers.Dense(class_count, activation="softmax", name="class_probabilities")(x)
    return keras.Model(inputs, outputs, name="ann1")


def build_ann2(input_dim: int, class_count: int) -> keras.Model:
    inputs = keras.Input(shape=(input_dim,), name="features")
    x = layers.Dense(256, activation="relu", name="dense_256")(inputs)
    x = layers.BatchNormalization(name="batch_normalization")(x)
    x = layers.Dropout(0.40, name="dropout_040")(x)
    x = layers.Dense(128, activation="relu", name="dense_128")(x)
    x = layers.Dropout(0.30, name="dropout_030")(x)
    outputs = layers.Dense(class_count, activation="softmax", name="class_probabilities")(x)
    return keras.Model(inputs, outputs, name="ann2")


def build_ann3(input_dim: int, class_count: int) -> keras.Model:
    inputs = keras.Input(shape=(input_dim,), name="features")
    x = layers.Dense(64, activation="relu", name="dense_64_a")(inputs)
    x = layers.Dense(64, activation="relu", name="dense_64_b")(x)
    x = layers.Dropout(0.25, name="dropout_025")(x)
    x = layers.Dense(32, activation="relu", name="dense_32")(x)
    outputs = layers.Dense(class_count, activation="softmax", name="class_probabilities")(x)
    return keras.Model(inputs, outputs, name="ann3")


def _compile(model: keras.Model) -> None:
    model.compile(
        optimizer=keras.optimizers.Adam(),
        loss="categorical_crossentropy",
        metrics=[keras.metrics.CategoricalAccuracy(name="accuracy")],
    )


def _validation_split(
    x: np.ndarray, y: np.ndarray, validation_rows: int, seed: int
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    indices = np.arange(len(y))
    counts = np.bincount(y)
    stratify = y if len(counts) > 1 and counts.min() >= 2 and validation_rows >= len(counts) else None
    train_indices, validation_indices = train_test_split(
        indices, test_size=validation_rows, random_state=seed, stratify=stratify
    )
    return x[train_indices], x[validation_indices], y[train_indices], y[validation_indices]


def _callbacks(checkpoint_path: Path) -> list[keras.callbacks.Callback]:
    return [
        keras.callbacks.EarlyStopping(
            monitor="val_loss", patience=EARLY_STOPPING_PATIENCE,
            min_delta=MIN_DELTA, restore_best_weights=True, verbose=1,
        ),
        keras.callbacks.ReduceLROnPlateau(
            monitor="val_loss", factor=0.5, patience=LR_PATIENCE,
            min_lr=1e-6, min_delta=MIN_DELTA, verbose=1,
        ),
        keras.callbacks.ModelCheckpoint(
            filepath=str(checkpoint_path), monitor="val_loss",
            mode="min", save_best_only=True, verbose=0,
        ),
    ]


def evaluate_probabilities(
    y_true: np.ndarray, probabilities: np.ndarray, class_names: list[str]
) -> dict[str, Any]:
    predictions = np.argmax(probabilities, axis=1)
    labels = np.arange(len(class_names))
    result: dict[str, Any] = {
        "accuracy": accuracy_score(y_true, predictions),
        "precision_macro": precision_score(y_true, predictions, labels=labels, average="macro", zero_division=0),
        "recall_macro": recall_score(y_true, predictions, labels=labels, average="macro", zero_division=0),
        "f1_macro": f1_score(y_true, predictions, labels=labels, average="macro", zero_division=0),
        "confusion_matrix": confusion_matrix(y_true, predictions, labels=labels).tolist(),
        "classification_report": classification_report(
            y_true, predictions, labels=labels, target_names=class_names,
            output_dict=True, zero_division=0,
        ),
        "roc_auc_ovr_macro": None,
    }
    try:
        one_hot = keras.utils.to_categorical(y_true, num_classes=len(class_names))
        result["roc_auc_ovr_macro"] = roc_auc_score(
            one_hot, probabilities, average="macro", multi_class="ovr"
        )
    except ValueError:
        pass
    return _json_safe(result)


def _predict(model: keras.Model, features: np.ndarray, batch_size: int) -> np.ndarray:
    return np.asarray(model.predict(features, batch_size=batch_size, verbose=0), dtype=np.float64)


def _save_confusion_matrix(matrix: list[list[int]], class_names: list[str], output: Path) -> None:
    figure, axis = plt.subplots(figsize=(7, 6))
    image = axis.imshow(matrix, cmap="Blues")
    figure.colorbar(image, ax=axis)
    axis.set(
        xticks=np.arange(len(class_names)), yticks=np.arange(len(class_names)),
        xticklabels=class_names, yticklabels=class_names,
        xlabel="Predicted class", ylabel="Actual class", title="Ensemble confusion matrix",
    )
    plt.setp(axis.get_xticklabels(), rotation=30, ha="right", rotation_mode="anchor")
    midpoint = max(matrix_value for row in matrix for matrix_value in row) / 2 if matrix else 0
    for row_index, row in enumerate(matrix):
        for column_index, value in enumerate(row):
            axis.text(column_index, row_index, str(value), ha="center", va="center",
                      color="white" if value > midpoint else "black")
    figure.tight_layout()
    figure.savefig(output, dpi=160)
    plt.close(figure)


def _feature_importance(
    model: keras.Model,
    features: np.ndarray,
    labels: np.ndarray,
    feature_names: list[str],
    batch_size: int,
    seed: int,
) -> list[dict[str, Any]]:
    baseline = accuracy_score(labels, np.argmax(_predict(model, features, batch_size), axis=1))
    rng = np.random.default_rng(seed)
    results = []
    for index, name in enumerate(feature_names):
        drops = []
        for _ in range(3):
            permuted = features.copy()
            permuted[:, index] = rng.permutation(permuted[:, index])
            score = accuracy_score(labels, np.argmax(_predict(model, permuted, batch_size), axis=1))
            drops.append(baseline - score)
        results.append({"feature": name, "importance": float(np.mean(drops)), "std": float(np.std(drops))})
    return sorted(results, key=lambda item: item["importance"], reverse=True)


def _save_plots(
    histories: dict[str, dict[str, list[float]]],
    ensemble_metrics: dict[str, Any],
    class_distribution: dict[str, int],
    importance: list[dict[str, Any]],
    class_names: list[str],
    output_dir: Path,
) -> dict[str, str]:
    paths: dict[str, str] = {}
    fig, axis = plt.subplots(figsize=(9, 5))
    for name, history in histories.items():
        if history.get("accuracy"):
            axis.plot(history["accuracy"], label=f"{name} train")
        if history.get("val_accuracy"):
            axis.plot(history["val_accuracy"], linestyle="--", label=f"{name} validation")
    axis.set(title="ANN training accuracy", xlabel="Epoch", ylabel="Categorical accuracy")
    axis.set_ylim(0, 1.02)
    axis.grid(alpha=0.25)
    axis.legend()
    fig.tight_layout()
    path = output_dir / "accuracy_curve.png"
    fig.savefig(path, dpi=160)
    plt.close(fig)
    paths["accuracy_curve"] = str(path)

    fig, axis = plt.subplots(figsize=(9, 5))
    for name, history in histories.items():
        if history.get("loss"):
            axis.plot(history["loss"], label=f"{name} train")
        if history.get("val_loss"):
            axis.plot(history["val_loss"], linestyle="--", label=f"{name} validation")
    axis.set(title="ANN training and validation loss", xlabel="Epoch", ylabel="Categorical crossentropy")
    axis.grid(alpha=0.25)
    axis.legend()
    fig.tight_layout()
    path = output_dir / "loss_curve.png"
    fig.savefig(path, dpi=160)
    plt.close(fig)
    paths["loss_curve"] = str(path)

    path = output_dir / "confusion_matrix.png"
    _save_confusion_matrix(ensemble_metrics["confusion_matrix"], class_names, path)
    paths["confusion_matrix"] = str(path)

    fig, axis = plt.subplots(figsize=(8, 5))
    axis.bar(list(class_distribution), list(class_distribution.values()), color="#009688")
    axis.set(title="Training class distribution", xlabel="Class", ylabel="Rows")
    axis.tick_params(axis="x", labelrotation=20)
    fig.tight_layout()
    path = output_dir / "class_distribution.png"
    fig.savefig(path, dpi=160)
    plt.close(fig)
    paths["class_distribution"] = str(path)

    top = importance[:20]
    fig, axis = plt.subplots(figsize=(10, max(5, len(top) * 0.28)))
    axis.barh([item["feature"] for item in reversed(top)], [item["importance"] for item in reversed(top)], color="#1976d2")
    axis.set(title="Permutation feature importance (ensemble, test set)", xlabel="Accuracy decrease after permutation")
    axis.axvline(0, color="black", linewidth=0.7)
    fig.tight_layout()
    path = output_dir / "feature_importance.png"
    fig.savefig(path, dpi=160)
    plt.close(fig)
    paths["feature_importance"] = str(path)
    return paths


def _write_report(path: Path, report: dict[str, Any]) -> None:
    table_rows = []
    for name, metrics in report["model_comparison"].items():
        table_rows.append(
            "<tr><th>" + html.escape(name) + "</th>"
            + "".join(f"<td>{metrics[key]:.4f}</td>" for key in ("accuracy", "precision_macro", "recall_macro", "f1_macro"))
            + "</tr>"
        )
    metric_table = (
        "<table><thead><tr><th>Model</th><th>Accuracy</th><th>Precision (macro)</th>"
        "<th>Recall (macro)</th><th>F1 (macro)</th></tr></thead><tbody>"
        + "".join(table_rows) + "</tbody></table>"
    )
    image_tags = "".join(
        f'<figure><img src="{html.escape(Path(value).name)}" alt="{html.escape(key.replace("_", " "))}">'
        f'<figcaption>{html.escape(key.replace("_", " ").title())}</figcaption></figure>'
        for key, value in report["visualizations"].items()
    )
    style = "body{font:15px/1.55 Arial,sans-serif;max-width:1200px;margin:2rem auto;padding:0 1rem;color:#263238}h1,h2{color:#00695c}table{border-collapse:collapse;width:100%;margin:1rem 0}td,th{border:1px solid #d8e0e3;padding:.55rem;text-align:left}th{background:#e8f5f3}.graphs{display:grid;grid-template-columns:repeat(auto-fit,minmax(420px,1fr));gap:1rem}img{max-width:100%;height:auto;border:1px solid #ddd}figure{margin:0}pre{white-space:pre-wrap;background:#f4f6f8;padding:1rem;overflow-wrap:anywhere}"
    summary = html.escape(json.dumps(report["dataset_summary"], indent=2))
    architectures = html.escape(json.dumps(report["architectures"], indent=2))
    hyperparameters = html.escape(json.dumps(report["hyperparameters"], indent=2))
    classification = html.escape(json.dumps(report["classification_reports"], indent=2))
    document = (
        "<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width,initial-scale=1\"><title>Dengue ANN Ensemble Training Report</title><style>"
        + style + "</style></head><body><h1>Dengue ANN Ensemble Training Report</h1>"
        + "<p>Generated UTC: " + html.escape(report["generated_at"]) + "</p>"
        + "<h2>Dataset summary</h2><pre>" + summary + "</pre>"
        + "<h2>Architecture</h2><pre>" + architectures + "</pre>"
        + "<h2>Hyperparameters</h2><pre>" + hyperparameters + "</pre>"
        + "<h2>Training time (seconds)</h2><pre>" + html.escape(json.dumps(report["training_time_seconds"], indent=2)) + "</pre>"
        + "<h2>Model comparison</h2>" + metric_table
        + "<h2>Final ensemble accuracy: " + f"{report['ensemble_accuracy']:.4f}" + "</h2>"
        + "<h2>Classification reports</h2><pre>" + classification + "</pre>"
        + "<h2>Visualizations</h2><div class=\"graphs\">" + image_tags + "</div>"
        + "</body></html>"
    )
    path.write_text(document, encoding="utf-8")


def train_ensemble(
    train_path: Path = TRAIN_CSV,
    test_path: Path = TEST_CSV,
    scaler_path: Path = SCALER_PATH,
    encoder_path: Path = ENCODER_PATH,
    output_dir: Path = MODEL_DIR,
    seed: int = SEED,
) -> dict[str, Any]:
    np.random.seed(seed)
    random.seed(seed)
    tf.keras.utils.set_random_seed(seed)

    x_train, y_train, x_test, y_test, feature_names, label_encoder, scaler, target_column = load_processed_data(
        train_path, test_path, scaler_path, encoder_path
    )
    class_names = [str(value) for value in label_encoder.classes_]
    class_count = len(class_names)
    hyperparameters = select_hyperparameters(len(x_train))
    x_fit, x_validation, y_fit, y_validation = _validation_split(
        x_train, y_train, hyperparameters["validation_rows"], seed
    )
    y_fit_onehot = keras.utils.to_categorical(y_fit, num_classes=class_count)
    y_validation_onehot = keras.utils.to_categorical(y_validation, num_classes=class_count)
    builders = {"ANN1": build_ann1, "ANN2": build_ann2, "ANN3": build_ann3}
    models: dict[str, keras.Model] = {}
    histories: dict[str, dict[str, list[float]]] = {}
    training_times: dict[str, float] = {}
    architecture_summaries: dict[str, str] = {}

    output_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="ann_checkpoints_", dir=output_dir) as checkpoint_dir:
        for index, (name, builder) in enumerate(builders.items()):
            print(f"Training {name} ({index + 1}/3)...", flush=True)
            tf.keras.backend.clear_session()
            tf.keras.utils.set_random_seed(seed + index)
            model = builder(x_train.shape[1], class_count)
            _compile(model)
            summary_lines: list[str] = []
            model.summary(print_fn=summary_lines.append)
            architecture_summaries[name] = "\n".join(summary_lines)
            checkpoint_path = Path(checkpoint_dir) / f"{name.lower()}_best.keras"
            started = time.perf_counter()
            history = model.fit(
                x_fit, y_fit_onehot,
                validation_data=(x_validation, y_validation_onehot),
                epochs=MAX_EPOCHS,
                batch_size=hyperparameters["batch_size"],
                callbacks=_callbacks(checkpoint_path),
                verbose=0,
                shuffle=True,
            )
            training_times[name] = time.perf_counter() - started
            histories[name] = {key: [float(item) for item in values] for key, values in history.history.items()}
            if checkpoint_path.is_file():
                model = keras.models.load_model(checkpoint_path)
            model_path = output_dir / f"{name.lower()}.keras"
            model.save(model_path)
            models[name] = model
            print(
                f"{name}: best epoch {int(np.argmin(histories[name]['val_loss'])) + 1}, "
                f"validation loss {min(histories[name]['val_loss']):.4f}, "
                f"training time {training_times[name]:.1f}s",
                flush=True,
            )

    probabilities: dict[str, np.ndarray] = {
        name: _predict(model, x_test, hyperparameters["batch_size"])
        for name, model in models.items()
    }
    ensemble_probabilities = np.mean(np.stack(list(probabilities.values()), axis=0), axis=0)
    metrics = {
        name: evaluate_probabilities(y_test, probabilities[name], class_names)
        for name in builders
    }
    metrics["Ensemble"] = evaluate_probabilities(y_test, ensemble_probabilities, class_names)

    ensemble_input = keras.Input(shape=(x_train.shape[1],), name="features")
    component_outputs = [models[name](ensemble_input, training=False) for name in builders]
    ensemble_output = layers.Average(name="soft_voting_average")(component_outputs)
    ensemble_model = keras.Model(ensemble_input, ensemble_output, name="soft_voting_ensemble")
    ensemble_path = output_dir / "ensemble_model.keras"
    ensemble_model.save(ensemble_path)

    # Preserve the exact preprocessing artifacts used for the split data.
    saved_scaler = output_dir / "scaler.pkl"
    saved_encoder = output_dir / "label_encoder.pkl"
    shutil.copy2(scaler_path, saved_scaler)
    shutil.copy2(encoder_path, saved_encoder)

    class_distribution = {
        class_names[index]: int(count)
        for index, count in enumerate(np.bincount(y_train, minlength=class_count))
    }
    importance = _feature_importance(
        ensemble_model, x_test, y_test, feature_names,
        hyperparameters["batch_size"], seed,
    )
    paths = _save_plots(
        histories, metrics["Ensemble"], class_distribution, importance,
        class_names, output_dir,
    )
    comparison = {
        name: {key: metrics[name][key] for key in (
            "accuracy", "precision_macro", "recall_macro", "f1_macro", "roc_auc_ovr_macro"
        )}
        for name in MODEL_NAMES
    }
    report: dict[str, Any] = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "dataset_summary": {
            "train_path": str(train_path), "test_path": str(test_path),
            "training_rows": int(len(x_train)), "test_rows": int(len(x_test)),
            "feature_count": int(len(feature_names)), "feature_columns": feature_names,
            "target_column": target_column, "target_classes": class_names,
            "training_class_distribution": class_distribution,
            "test_class_distribution": {
                class_names[index]: int(count)
                for index, count in enumerate(np.bincount(y_test, minlength=class_count))
            },
            "scaler_loaded_from": str(scaler_path),
            "scaler_input_feature_count": int(getattr(scaler, "n_features_in_", -1)),
            "note": "CSV features were preprocessed and scaled by the existing pipeline; values were not scaled a second time.",
        },
        "architectures": {
            "ANN1": "Dense(128, ReLU) -> Dropout(0.30) -> Dense(64, ReLU) -> Dropout(0.20) -> Dense(softmax)",
            "ANN2": "Dense(256, ReLU) -> BatchNormalization -> Dropout(0.40) -> Dense(128, ReLU) -> Dropout(0.30) -> Dense(softmax)",
            "ANN3": "Dense(64, ReLU) -> Dense(64, ReLU) -> Dropout(0.25) -> Dense(32, ReLU) -> Dense(softmax)",
            "Ensemble": "Arithmetic mean of ANN1, ANN2, ANN3 softmax probabilities",
            "model_summaries": architecture_summaries,
        },
        "hyperparameters": hyperparameters,
        "training_time_seconds": {key: round(value, 3) for key, value in training_times.items()},
        "metrics": metrics,
        "model_comparison": comparison,
        "classification_reports": {
            name: metrics[name]["classification_report"] for name in MODEL_NAMES
        },
        "ensemble_accuracy": metrics["Ensemble"]["accuracy"],
        "feature_importance": importance,
        "visualizations": paths,
        "model_trained": True,
        "flask_integrated": False,
    }
    report = _json_safe(report)
    (output_dir / "training_metrics.json").write_text(
        json.dumps(report, indent=2, allow_nan=False), encoding="utf-8"
    )
    (output_dir / "model_summary.txt").write_text(
        "\n\n".join(f"{name}\n{'=' * len(name)}\n{summary}" for name, summary in architecture_summaries.items())
        + "\n\nSoft-voting ensemble\n====================\n"
        + "Arithmetic mean of the three component softmax probability vectors.",
        encoding="utf-8",
    )
    _write_report(output_dir / "training_report.html", report)

    sample_count = min(10, len(x_test))
    rng = np.random.default_rng(seed)
    sample_indices = np.sort(rng.choice(len(x_test), size=sample_count, replace=False))
    sample_probabilities = ensemble_probabilities[sample_indices]
    sample_predictions = np.argmax(sample_probabilities, axis=1)
    report["sample_predictions"] = [
        {
            "test_row_index": int(index),
            "actual_class": class_names[int(y_test[index])],
            "predicted_class": class_names[int(sample_predictions[offset])],
            "confidence": float(np.max(sample_probabilities[offset])),
            "probabilities": {
                class_names[class_index]: float(probability)
                for class_index, probability in enumerate(sample_probabilities[offset])
            },
        }
        for offset, index in enumerate(sample_indices)
    ]
    (output_dir / "training_metrics.json").write_text(
        json.dumps(_json_safe(report), indent=2, allow_nan=False), encoding="utf-8"
    )
    _write_report(output_dir / "training_report.html", report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Train three ANN classifiers and their soft-voting ensemble.")
    parser.add_argument("--train", type=Path, default=TRAIN_CSV)
    parser.add_argument("--test", type=Path, default=TEST_CSV)
    parser.add_argument("--scaler", type=Path, default=SCALER_PATH)
    parser.add_argument("--encoder", type=Path, default=ENCODER_PATH)
    parser.add_argument("--output-dir", type=Path, default=MODEL_DIR)
    parser.add_argument("--seed", type=int, default=SEED)
    args = parser.parse_args()

    try:
        report = train_ensemble(
            train_path=args.train,
            test_path=args.test,
            scaler_path=args.scaler,
            encoder_path=args.encoder,
            output_dir=args.output_dir,
            seed=args.seed,
        )
    except (FileNotFoundError, OSError, TypeError, ValueError) as error:
        parser.error(str(error))

    print(f"Ensemble accuracy: {report['ensemble_accuracy']:.4f}")
    print(f"Training outputs saved to: {args.output_dir.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

