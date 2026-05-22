"""Deterministic offline analyzer used by tests, CI, and demos."""

from __future__ import annotations

import numpy as np

from retail_monitor.models import (
    AlertDecision,
    AlertPriority,
    AnalysisContext,
    CleanlinessAnalysis,
    MerchandiseAnalysis,
    SpatialAnalysis,
    YOLODetection,
)


class StubVisionAnalyzer:
    """Rule-based analyzer that satisfies the VisionAnalyzer protocol."""

    def analyze_cleanliness(
        self,
        image: np.ndarray,
        detections: list[YOLODetection],
        context: AnalysisContext,
    ) -> tuple[CleanlinessAnalysis, SpatialAnalysis]:
        bad_terms = {"trash", "spill", "garbage", "fallen product", "wet floor"}
        bad_count = sum(1 for d in detections if d.class_name.lower() in bad_terms)
        score = max(0.0, 9.0 - bad_count * 1.5)

        cleanliness = CleanlinessAnalysis(
            overall_cleanliness_score=score,
            floor_condition="clean" if score >= 7 else "moderately_dirty",
            visible_debris=[d.class_name for d in detections if d.class_name.lower() in bad_terms],
            debris_locations=["floor"] if bad_count else [],
            spills_present=any("spill" in d.class_name.lower() for d in detections),
            stains_present=False,
            reasoning="Stub analyzer using detection heuristics (no LLM).",
        )
        spatial = SpatialAnalysis(
            floor_objects=[{"object": d.class_name, "location": "floor"} for d in detections],
            shelf_objects=[],
            misplaced_items=[],
            spatial_reasoning="Stub spatial reasoning.",
        )
        return cleanliness, spatial

    def analyze_merchandise(
        self,
        image: np.ndarray,
        detections: list[YOLODetection],
        context: AnalysisContext,
    ) -> MerchandiseAnalysis:
        fallen = sum(1 for d in detections if "fallen" in d.class_name.lower())
        return MerchandiseAnalysis(
            shelf_fullness_score=7.5,
            shelf_organization_score=7.0,
            empty_spaces_count=0,
            misplaced_products_count=0,
            fallen_products_count=fallen,
            reasoning="Stub merchandise analyzer.",
        )

    def make_alert_decision(
        self,
        cleanliness: CleanlinessAnalysis | None,
        spatial: SpatialAnalysis | None,
        merchandise: MerchandiseAnalysis | None,
        context: AnalysisContext,
    ) -> AlertDecision:
        if cleanliness is not None:
            score = cleanliness.overall_cleanliness_score
            # Score is 0-10 where 10 is pristine: lower = dirtier.
            if cleanliness.spills_present or score < 4:
                return AlertDecision(
                    alert_required=True,
                    priority=AlertPriority.HIGH,
                    reasoning=f"Cleanliness score {score:.1f}/10 (stub).",
                    recommended_action="Clean immediately.",
                    estimated_time_minutes=15,
                    confidence_level=0.6,
                )
            if score < 6:
                return AlertDecision(
                    alert_required=True,
                    priority=AlertPriority.MEDIUM,
                    reasoning=f"Cleanliness score {score:.1f}/10 (stub).",
                    recommended_action="Schedule cleaning.",
                    estimated_time_minutes=10,
                    confidence_level=0.6,
                )
            return AlertDecision(
                alert_required=False,
                priority=AlertPriority.NONE,
                reasoning="Acceptable conditions (stub).",
                recommended_action="Continue normal schedule.",
                estimated_time_minutes=0,
                confidence_level=0.6,
            )
        if merchandise is not None and merchandise.fallen_products_count > 0:
            return AlertDecision(
                alert_required=True,
                priority=AlertPriority.HIGH,
                reasoning=f"{merchandise.fallen_products_count} fallen products (stub).",
                recommended_action="Restock and reshelve.",
                estimated_time_minutes=10,
                confidence_level=0.6,
            )
        return AlertDecision(
            alert_required=False,
            priority=AlertPriority.NONE,
            reasoning="No issues found (stub).",
            recommended_action="None.",
            estimated_time_minutes=0,
            confidence_level=0.5,
        )
