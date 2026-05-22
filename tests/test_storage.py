"""Storage tests."""

from datetime import datetime, timedelta
from pathlib import Path

from retail_monitor.models import (
    AlertDecision,
    AlertPriority,
    AnalysisResult,
    CleanlinessAnalysis,
)
from retail_monitor.services.storage import IncidentStore


def _result(score: float, required: bool, priority: AlertPriority) -> AnalysisResult:
    return AnalysisResult(
        alert_decision=AlertDecision(
            alert_required=required,
            priority=priority,
            reasoning="r",
            recommended_action="a",
        ),
        raw_detections=[],
        cleanliness_analysis=CleanlinessAnalysis(
            overall_cleanliness_score=score,
            floor_condition="clean",
        ),
        camera_id="cam",
    )


def test_record_and_recent(tmp_path: Path):
    store = IncidentStore(database_url=f"sqlite:///{tmp_path / 'x.db'}")
    rid = store.record(_result(8.0, True, AlertPriority.HIGH))
    assert rid > 0
    rows = store.recent(limit=5)
    assert len(rows) == 1
    assert rows[0]["priority"] == "high"


def test_only_alerts_filter(tmp_path: Path):
    store = IncidentStore(database_url=f"sqlite:///{tmp_path / 'x.db'}")
    store.record(_result(2.0, False, AlertPriority.NONE))
    store.record(_result(9.0, True, AlertPriority.HIGH))
    assert len(store.recent(only_alerts=False)) == 2
    assert len(store.recent(only_alerts=True)) == 1


def test_purge_older_than(tmp_path: Path):
    store = IncidentStore(database_url=f"sqlite:///{tmp_path / 'x.db'}")
    store.record(_result(8.0, True, AlertPriority.HIGH))
    purged = store.purge_older_than(datetime.utcnow() + timedelta(days=1))
    assert purged == 1
    assert store.recent() == []
