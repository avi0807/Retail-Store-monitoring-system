"""End-to-end pipeline tests using the stub analyzer."""

from __future__ import annotations

from pathlib import Path

import cv2

from retail_monitor.analyzers import StubVisionAnalyzer
from retail_monitor.models import (
    AlertPriority,
    AnalysisContext,
    SpaceType,
    TrafficLevel,
    YOLODetection,
)
from retail_monitor.pipeline import MonitoringPipeline
from retail_monitor.services.storage import IncidentStore


def _ctx() -> AnalysisContext:
    return AnalysisContext(
        space_type=SpaceType.AISLE,
        traffic_level=TrafficLevel.MEDIUM,
        store_tier="standard",
        hours_since_cleaned=2.0,
        camera_id="test-cam",
    )


def test_clean_frame_no_alert(blank_image, fake_detector):
    pipeline = MonitoringPipeline(
        detector=fake_detector(),
        analyzer=StubVisionAnalyzer(),
    )
    result = pipeline.analyze_frame(blank_image, _ctx(), mode="cleanliness")

    assert result.cleanliness_analysis is not None
    assert result.cleanliness_analysis.overall_cleanliness_score >= 7
    assert result.alert_decision.alert_required is False
    assert result.alert_decision.priority is AlertPriority.NONE


def test_dirty_frame_triggers_alert(blank_image, fake_detector):
    detections = [
        YOLODetection(class_name="trash", confidence=0.9, bbox=[0, 0, 10, 10]),
        YOLODetection(class_name="spill", confidence=0.8, bbox=[20, 20, 30, 30]),
    ]
    pipeline = MonitoringPipeline(
        detector=fake_detector(detections),
        analyzer=StubVisionAnalyzer(),
    )
    result = pipeline.analyze_frame(blank_image, _ctx(), mode="cleanliness")

    assert result.alert_decision.alert_required is True
    assert result.alert_decision.priority in {AlertPriority.HIGH, AlertPriority.MEDIUM}
    assert result.cleanliness_analysis is not None
    assert result.cleanliness_analysis.spills_present is True


def test_merchandise_mode(blank_image, fake_detector):
    pipeline = MonitoringPipeline(
        detector=fake_detector(),
        analyzer=StubVisionAnalyzer(),
    )
    result = pipeline.analyze_frame(blank_image, _ctx(), mode="merchandise")
    assert result.merchandise_analysis is not None
    assert result.cleanliness_analysis is None


def test_storage_persists_results(tmp_path: Path, blank_image, fake_detector):
    db = tmp_path / "incidents.db"
    store = IncidentStore(database_url=f"sqlite:///{db}")
    pipeline = MonitoringPipeline(
        detector=fake_detector(
            [YOLODetection(class_name="trash", confidence=0.9, bbox=[0, 0, 10, 10])]
        ),
        analyzer=StubVisionAnalyzer(),
        store=store,
    )
    pipeline.analyze_frame(blank_image, _ctx(), mode="cleanliness")
    rows = store.recent(limit=10)
    assert len(rows) == 1
    assert rows[0]["camera_id"] == "test-cam"


def test_image_file_loader(tmp_path: Path, blank_image, fake_detector):
    img_path = tmp_path / "frame.jpg"
    cv2.imwrite(str(img_path), blank_image)
    pipeline = MonitoringPipeline(
        detector=fake_detector(),
        analyzer=StubVisionAnalyzer(),
    )
    result = pipeline.analyze_image_file(img_path, _ctx())
    assert result is not None
    assert result.cleanliness_analysis is not None
