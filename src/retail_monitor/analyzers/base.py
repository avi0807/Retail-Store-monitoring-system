"""Vision analyzer protocol."""

from __future__ import annotations

from typing import Protocol

import numpy as np

from retail_monitor.models import (
    AlertDecision,
    AnalysisContext,
    CleanlinessAnalysis,
    MerchandiseAnalysis,
    SpatialAnalysis,
    YOLODetection,
)


class VisionAnalyzer(Protocol):
    def analyze_cleanliness(
        self,
        image: np.ndarray,
        detections: list[YOLODetection],
        context: AnalysisContext,
    ) -> tuple[CleanlinessAnalysis, SpatialAnalysis]: ...

    def analyze_merchandise(
        self,
        image: np.ndarray,
        detections: list[YOLODetection],
        context: AnalysisContext,
    ) -> MerchandiseAnalysis: ...

    def make_alert_decision(
        self,
        cleanliness: CleanlinessAnalysis | None,
        spatial: SpatialAnalysis | None,
        merchandise: MerchandiseAnalysis | None,
        context: AnalysisContext,
    ) -> AlertDecision: ...
