from __future__ import annotations

import threading
from importlib import import_module
from pathlib import Path

from PIL import Image


class ModelUnavailableError(RuntimeError):
    pass


class IncompatibleDetectorError(RuntimeError):
    pass


_CLASS_RISK = {
    "high_risk_breeding_site": "High Risk Breeding Site",
    "breeding_site": "High Risk Breeding Site",
    "standing_water": "High Risk Breeding Site",
    "stagnant_water": "High Risk Breeding Site",
    "water_pool": "High Risk Breeding Site",
    "water_puddle": "High Risk Breeding Site",
    "pooled_water": "High Risk Breeding Site",
    "medium_risk_breeding_site": "Medium Risk Breeding Site",
    "tire": "Medium Risk Breeding Site",
    "tyre": "Medium Risk Breeding Site",
    "old_tire": "Medium Risk Breeding Site",
    "used_tire": "Medium Risk Breeding Site",
    "plastic_tire": "Medium Risk Breeding Site",
    "old_tyre": "Medium Risk Breeding Site",
    "bucket": "Medium Risk Breeding Site",
    "plastic_bucket": "Medium Risk Breeding Site",
    "open_bucket": "Medium Risk Breeding Site",
    "flower_pot": "Medium Risk Breeding Site",
    "flowerpot": "Medium Risk Breeding Site",
    "plant_pot": "Medium Risk Breeding Site",
    "water_tank": "Medium Risk Breeding Site",
    "open_water_tank": "Medium Risk Breeding Site",
    "drain": "Medium Risk Breeding Site",
    "open_drain": "Medium Risk Breeding Site",
    "storm_drain": "Medium Risk Breeding Site",
    "container": "Medium Risk Breeding Site",
    "low_risk": "Low Risk",
    "dry_container": "Low Risk",
    "covered_water": "Low Risk",
    "no_breeding_site": "No Breeding Site Detected",
    "no_water": "No Breeding Site Detected",
    "no_breeding": "No Breeding Site Detected",
}
_RISK_RANK = {
    "No Breeding Site Detected": 0,
    "Low Risk": 1,
    "Medium Risk Breeding Site": 2,
    "High Risk Breeding Site": 3,
}
_RECOMMENDATIONS = {
    "High Risk Breeding Site": [
        "Drain stagnant water immediately.",
        "Clean the container and surrounding area.",
        "Cover water storage tanks.",
        "Apply larvicide only as directed by local health authorities.",
    ],
    "Medium Risk Breeding Site": [
        "Empty and scrub containers that can collect water.",
        "Turn over or cover buckets, tires, and flower pots.",
        "Check drains and water storage regularly.",
    ],
    "Low Risk": [
        "Keep containers covered and check them after rainfall.",
        "Maintain the area to prevent water from accumulating.",
    ],
    "No Breeding Site Detected": [
        "No target breeding-site objects were detected in this image.",
        "Check the location again after rainfall or if standing water appears.",
    ],
}


def _normalized_label(label: str) -> str:
    return "_".join(str(label).strip().casefold().replace("-", " ").split())


def _human_label(label: str) -> str:
    aliases = {
        "standing_water": "Standing Water",
        "stagnant_water": "Stagnant Water",
        "water_pool": "Water Pool",
        "water_puddle": "Water Puddle",
        "pooled_water": "Pooled Water",
        "high_risk_breeding_site": "High Risk Breeding Site",
        "medium_risk_breeding_site": "Medium Risk Breeding Site",
        "flower_pot": "Flower Pot",
        "flowerpot": "Flower Pot",
        "plant_pot": "Plant Pot",
        "water_tank": "Water Tank",
        "open_water_tank": "Open Water Tank",
        "plastic_bucket": "Plastic Bucket",
        "open_bucket": "Open Bucket",
        "plastic_tire": "Plastic Tire",
        "old_tire": "Old Tire",
        "used_tire": "Used Tire",
        "old_tyre": "Old Tyre",
        "open_drain": "Open Drain",
        "storm_drain": "Storm Drain",
        "dry_container": "Dry Container",
        "covered_water": "Covered Water",
        "no_breeding_site": "No Breeding Site",
        "no_breeding": "No Breeding Site",
        "no_water": "No Water",
    }
    return aliases.get(label, label.replace("_", " ").title())


class DetectionModel:
    """Lazy YOLOv8 adapter; the supplied weights must use the documented class labels."""

    def __init__(self, model_path: str):
        self.model_path = Path(model_path)
        self._model = None
        self._lock = threading.Lock()

    def _get_model(self):
        if self._model is not None:
            return self._model
        if not self.model_path.is_file():
            raise ModelUnavailableError("Mosquito detector weights were not found.")
        with self._lock:
            if self._model is None:
                try:
                    YOLO = import_module("ultralytics").YOLO
                    self._model = YOLO(str(self.model_path))
                except Exception as error:
                    raise ModelUnavailableError(
                        "The mosquito detector could not be loaded. Check its weights "
                        "and install the configured inference dependencies."
                    ) from error
        return self._model

    def analyze(self, image: Image.Image) -> dict:
        model = self._get_model()
        try:
            results = model.predict(source=image.convert("RGB"), verbose=False)
        except Exception as error:
            raise RuntimeError("Mosquito image inference failed.") from error
        if not results:
            raise RuntimeError("The detector returned no inference result.")
        result = results[0]
        boxes = getattr(result, "boxes", None)
        detections = []
        if boxes is not None and len(boxes):
            classes = boxes.cls.detach().cpu().tolist()
            confidences = boxes.conf.detach().cpu().tolist()
            names = result.names
            for class_id, confidence in zip(classes, confidences):
                raw_label = names[int(class_id)]
                label = _normalized_label(raw_label)
                risk = _CLASS_RISK.get(label)
                if risk is None:
                    raise IncompatibleDetectorError(
                        f"The detector class '{raw_label}' is not in the supported "
                        "mosquito-breeding class vocabulary."
                    )
                detections.append(
                    {
                        "label": _human_label(label),
                        "risk": risk,
                        "confidence": max(0.0, min(100.0, float(confidence) * 100)),
                    }
                )

        if detections:
            prediction = max(
                detections,
                key=lambda item: (
                    _RISK_RANK[item["risk"]],
                    item["confidence"],
                ),
            )["risk"]
            confidence = max(
                item["confidence"]
                for item in detections
                if item["risk"] == prediction
            )
        else:
            prediction = "No Breeding Site Detected"
            confidence = 0.0

        annotated_image = None
        if detections and hasattr(result, "plot"):
            annotated_image = result.plot()

        return {
            "prediction": prediction,
            "confidence": round(confidence, 2),
            "objects_detected": list(dict.fromkeys(item["label"] for item in detections)),
            "recommendation": _RECOMMENDATIONS[prediction],
            "annotated_image": annotated_image,
        }
