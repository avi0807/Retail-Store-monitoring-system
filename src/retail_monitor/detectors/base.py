"""Detector protocol used by the pipeline."""

from __future__ import annotations

from typing import Protocol

import numpy as np

from retail_monitor.models import YOLODetection


class ObjectDetector(Protocol):
    def detect(self, image: np.ndarray) -> tuple[list[YOLODetection], int, int]:
        """Return ``(detections, width, height)``."""
        ...
