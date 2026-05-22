"""Tests for alert dispatch + threshold logic."""

from datetime import datetime

from retail_monitor.models import (
    AlertDecision,
    AlertPriority,
    AnalysisResult,
    CleanlinessAnalysis,
)
from retail_monitor.services.alerts import ConsoleAlertSink, serialize_result


def _make_result(priority: AlertPriority, required: bool = True) -> AnalysisResult:
    return AnalysisResult(
        alert_decision=AlertDecision(
            alert_required=required,
            priority=priority,
            reasoning="r",
            recommended_action="a",
            estimated_time_minutes=5,
            confidence_level=0.9,
        ),
        raw_detections=[],
        cleanliness_analysis=CleanlinessAnalysis(
            overall_cleanliness_score=7.5,
            floor_condition="clean",
        ),
        timestamp=datetime.utcnow(),
        camera_id="cam-1",
    )


def test_console_sink_filters_below_threshold(caplog):
    sink = ConsoleAlertSink(min_priority="high")
    with caplog.at_level("WARNING", logger="retail_monitor.services.alerts"):
        sink.emit(_make_result(AlertPriority.LOW))
    assert "ALERT" not in caplog.text


def test_console_sink_emits_at_or_above_threshold(caplog):
    sink = ConsoleAlertSink(min_priority="medium")
    with caplog.at_level("WARNING", logger="retail_monitor.services.alerts"):
        sink.emit(_make_result(AlertPriority.HIGH))
    assert "ALERT" in caplog.text
    assert "HIGH" in caplog.text


def test_console_sink_skips_when_no_alert(caplog):
    sink = ConsoleAlertSink(min_priority="low")
    with caplog.at_level("WARNING", logger="retail_monitor.services.alerts"):
        sink.emit(_make_result(AlertPriority.NONE, required=False))
    assert "ALERT" not in caplog.text


def test_serialize_result_roundtrip():
    text = serialize_result(_make_result(AlertPriority.HIGH))
    assert "HIGH".lower() in text.lower()
    assert "cleanliness" in text
