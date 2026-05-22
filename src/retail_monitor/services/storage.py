"""SQLite-backed incident store."""

from __future__ import annotations

import json
import logging
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

from retail_monitor.models import AnalysisResult

logger = logging.getLogger(__name__)


_SCHEMA = """
CREATE TABLE IF NOT EXISTS incidents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    camera_id TEXT,
    frame_index INTEGER,
    alert_required INTEGER NOT NULL,
    priority TEXT NOT NULL,
    cleanliness_score REAL,
    shelf_fullness_score REAL,
    payload TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_incidents_timestamp ON incidents(timestamp);
CREATE INDEX IF NOT EXISTS idx_incidents_camera ON incidents(camera_id);
CREATE INDEX IF NOT EXISTS idx_incidents_priority ON incidents(priority);
"""


def _path_from_url(database_url: str) -> Path:
    """Convert ``sqlite:///path/to.db`` into a Path."""
    if database_url.startswith("sqlite:///"):
        return Path(database_url[len("sqlite:///") :])
    if database_url.startswith("sqlite://"):
        return Path(database_url[len("sqlite://") :])
    return Path(database_url)


class IncidentStore:
    def __init__(self, database_url: str = "sqlite:///./retail_monitor.db") -> None:
        self.db_path = _path_from_url(database_url)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.executescript(_SCHEMA)
            conn.commit()
        logger.info("Incident store ready at %s", self.db_path)

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def record(self, result: AnalysisResult) -> int:
        """Persist an analysis result. Returns the row id."""
        payload = {
            "alert": asdict(result.alert_decision),
            "cleanliness": asdict(result.cleanliness_analysis) if result.cleanliness_analysis else None,
            "merchandise": asdict(result.merchandise_analysis) if result.merchandise_analysis else None,
            "spatial": asdict(result.spatial_analysis) if result.spatial_analysis else None,
            "detections": [asdict(d) for d in result.raw_detections],
        }
        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO incidents (
                    timestamp, camera_id, frame_index,
                    alert_required, priority,
                    cleanliness_score, shelf_fullness_score, payload
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    result.timestamp.isoformat(),
                    result.camera_id,
                    result.frame_index,
                    int(result.alert_decision.alert_required),
                    result.alert_decision.priority.value,
                    result.cleanliness_analysis.overall_cleanliness_score
                    if result.cleanliness_analysis
                    else None,
                    result.merchandise_analysis.shelf_fullness_score
                    if result.merchandise_analysis
                    else None,
                    json.dumps(payload, default=str),
                ),
            )
            conn.commit()
            return cursor.lastrowid or 0

    def recent(self, limit: int = 50, only_alerts: bool = False) -> list[dict]:
        sql = "SELECT * FROM incidents"
        params: tuple = ()
        if only_alerts:
            sql += " WHERE alert_required = 1"
        sql += " ORDER BY id DESC LIMIT ?"
        params = (*params, limit)
        with self._connect() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [dict(row) for row in rows]

    def purge_older_than(self, before: datetime) -> int:
        with self._connect() as conn:
            cursor = conn.execute(
                "DELETE FROM incidents WHERE timestamp < ?",
                (before.isoformat(),),
            )
            conn.commit()
            return cursor.rowcount
