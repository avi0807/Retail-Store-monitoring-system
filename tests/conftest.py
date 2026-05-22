"""Shared test fixtures."""

from __future__ import annotations

import numpy as np
import pytest

from retail_monitor.models import YOLODetection


class FakeDetector:
    def __init__(self, detections: list[YOLODetection] | None = None) -> None:
        self._detections = detections or []

    def detect(self, image: np.ndarray) -> tuple[list[YOLODetection], int, int]:
        h, w = image.shape[:2]
        return list(self._detections), w, h


@pytest.fixture
def blank_image() -> np.ndarray:
    return np.zeros((480, 640, 3), dtype=np.uint8)


@pytest.fixture
def fake_detector():
    return FakeDetector
