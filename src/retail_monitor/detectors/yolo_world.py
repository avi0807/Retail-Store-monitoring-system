"""YOLO-World based open-vocabulary detector.

YOLO-World accepts class names at runtime, which fits the retail use
case (``spill``, ``trash``, ``fallen product``) without fine-tuning.
Falls back to YOLOv8m if the World weights cannot be loaded.
"""

from __future__ import annotations

import logging

import numpy as np

from retail_monitor.models import YOLODetection

logger = logging.getLogger(__name__)


class YOLOWorldDetector:
    """Open-vocabulary YOLO detector with graceful fallback."""

    def __init__(
        self,
        model: str = "yolov8s-worldv2.pt",
        fallback_model: str = "yolov8m.pt",
        confidence: float = 0.25,
        iou_threshold: float = 0.45,
        device: str = "auto",
        classes: list[str] | None = None,
    ) -> None:
        # Lazy import keeps test runs light when ultralytics isn't needed.
        from ultralytics import YOLO

        self.confidence = confidence
        self.iou_threshold = iou_threshold
        self.device = None if device == "auto" else device
        self.classes = classes or []

        try:
            logger.info("Loading detector: %s", model)
            self.model = YOLO(model)
            self._is_world_model = "world" in model.lower()
        except Exception as exc:
            logger.warning(
                "Failed to load %s (%s). Falling back to %s.",
                model, exc, fallback_model,
            )
            self.model = YOLO(fallback_model)
            self._is_world_model = "world" in fallback_model.lower()

        if self._is_world_model and self.classes:
            try:
                self.model.set_classes(self.classes)
                logger.info("YOLO-World vocabulary set to: %s", self.classes)
            except Exception as exc:
                logger.warning("Could not set YOLO-World classes: %s", exc)

    def detect(self, image: np.ndarray) -> tuple[list[YOLODetection], int, int]:
        height, width = image.shape[:2]
        kwargs = {"conf": self.confidence, "iou": self.iou_threshold, "verbose": False}
        if self.device is not None:
            kwargs["device"] = self.device

        results = self.model(image, **kwargs)
        detections: list[YOLODetection] = []

        for result in results:
            names = result.names
            for box in result.boxes:
                detections.append(
                    YOLODetection(
                        class_name=names[int(box.cls[0])],
                        confidence=float(box.conf[0]),
                        bbox=[float(v) for v in box.xyxy[0].tolist()],
                    )
                )

        return detections, width, height
