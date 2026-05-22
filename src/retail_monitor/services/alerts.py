"""Alert dispatchers (console + webhook)."""

from __future__ import annotations

import json
import logging
from dataclasses import asdict
from typing import Any, Protocol

from retail_monitor.models import AlertPriority, AnalysisResult

logger = logging.getLogger(__name__)


_PRIORITY_RANK = {
    AlertPriority.NONE: 0,
    AlertPriority.LOW: 1,
    AlertPriority.MEDIUM: 2,
    AlertPriority.HIGH: 3,
    AlertPriority.CRITICAL: 4,
}


def _meets_threshold(priority: AlertPriority, threshold: str) -> bool:
    try:
        threshold_priority = AlertPriority(threshold)
    except ValueError:
        threshold_priority = AlertPriority.MEDIUM
    return _PRIORITY_RANK[priority] >= _PRIORITY_RANK[threshold_priority]


def _result_to_payload(result: AnalysisResult) -> dict[str, Any]:
    """Convert an AnalysisResult to a JSON-safe dict."""
    payload: dict[str, Any] = {
        "timestamp": result.timestamp.isoformat(),
        "camera_id": result.camera_id,
        "frame_index": result.frame_index,
        "alert": {
            "required": result.alert_decision.alert_required,
            "priority": result.alert_decision.priority.value,
            "reasoning": result.alert_decision.reasoning,
            "recommended_action": result.alert_decision.recommended_action,
            "estimated_time_minutes": result.alert_decision.estimated_time_minutes,
            "confidence_level": result.alert_decision.confidence_level,
        },
    }
    if result.cleanliness_analysis is not None:
        payload["cleanliness"] = asdict(result.cleanliness_analysis)
    if result.merchandise_analysis is not None:
        payload["merchandise"] = asdict(result.merchandise_analysis)
    if result.spatial_analysis is not None:
        payload["spatial"] = asdict(result.spatial_analysis)
    payload["detections"] = [asdict(d) for d in result.raw_detections]
    return payload


class AlertSink(Protocol):
    def emit(self, result: AnalysisResult) -> None: ...


class ConsoleAlertSink:
    """Logs alerts to the configured logger."""

    def __init__(self, min_priority: str = "medium") -> None:
        self.min_priority = min_priority

    def emit(self, result: AnalysisResult) -> None:
        decision = result.alert_decision
        if not decision.alert_required:
            return
        if not _meets_threshold(decision.priority, self.min_priority):
            return
        logger.warning(
            "ALERT [%s] camera=%s priority=%s :: %s -> %s",
            result.timestamp.isoformat(timespec="seconds"),
            result.camera_id or "n/a",
            decision.priority.value.upper(),
            decision.reasoning,
            decision.recommended_action,
        )


class WebhookAlertSink:
    """POSTs alert JSON to a webhook URL."""

    def __init__(
        self,
        url: str,
        min_priority: str = "medium",
        timeout_seconds: float = 5.0,
    ) -> None:
        self.url = url
        self.min_priority = min_priority
        self.timeout = timeout_seconds

    def emit(self, result: AnalysisResult) -> None:
        if not result.alert_decision.alert_required:
            return
        if not _meets_threshold(result.alert_decision.priority, self.min_priority):
            return

        try:
            import requests
        except ImportError:
            logger.warning("requests not installed, skipping webhook")
            return

        payload = _result_to_payload(result)
        try:
            resp = requests.post(self.url, json=payload, timeout=self.timeout)
            resp.raise_for_status()
            logger.info("Webhook delivered (status=%s)", resp.status_code)
        except Exception as exc:
            logger.error("Webhook delivery failed: %s", exc)


class CompositeAlertSink:
    def __init__(self, sinks: list[AlertSink]) -> None:
        self.sinks = sinks

    def emit(self, result: AnalysisResult) -> None:
        for sink in self.sinks:
            try:
                sink.emit(result)
            except Exception as exc:
                logger.exception("Alert sink %s failed: %s", type(sink).__name__, exc)


def serialize_result(result: AnalysisResult) -> str:
    """JSON-serialize an analysis result."""
    return json.dumps(_result_to_payload(result), indent=2, default=str)
