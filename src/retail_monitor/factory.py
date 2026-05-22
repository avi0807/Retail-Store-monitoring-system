"""Factory helpers that wire config to a MonitoringPipeline."""

from __future__ import annotations

import logging

from retail_monitor.analyzers import GeminiVisionAnalyzer, StubVisionAnalyzer
from retail_monitor.analyzers.base import VisionAnalyzer
from retail_monitor.config import AppConfig
from retail_monitor.detectors import YOLOWorldDetector
from retail_monitor.detectors.base import ObjectDetector
from retail_monitor.pipeline import MonitoringPipeline
from retail_monitor.services.alerts import (
    AlertSink,
    CompositeAlertSink,
    ConsoleAlertSink,
    WebhookAlertSink,
)
from retail_monitor.services.storage import IncidentStore

logger = logging.getLogger(__name__)


def build_detector(config: AppConfig) -> ObjectDetector:
    return YOLOWorldDetector(
        model=config.detector.model,
        fallback_model=config.detector.fallback_model,
        confidence=config.detector.confidence,
        iou_threshold=config.detector.iou_threshold,
        device=config.detector.device,
        classes=config.detector.classes,
    )


def build_analyzer(config: AppConfig) -> VisionAnalyzer:
    provider = config.llm.provider.lower()
    if provider == "stub":
        logger.info("Using stub analyzer (offline mode).")
        return StubVisionAnalyzer()
    if provider == "gemini":
        if not config.gemini_api_key:
            logger.warning("GEMINI_API_KEY not set, falling back to stub analyzer.")
            return StubVisionAnalyzer()
        return GeminiVisionAnalyzer(
            api_key=config.gemini_api_key,
            model=config.llm.model,
            temperature=config.llm.temperature,
        )
    if provider == "qwen":
        from retail_monitor.analyzers import get_qwen_analyzer

        QwenVisionAnalyzer = get_qwen_analyzer()
        return QwenVisionAnalyzer(
            model_id=config.llm.model or "Qwen/Qwen2.5-VL-7B-Instruct",
            device=config.llm.local_device,
            dtype=config.llm.local_dtype,
            max_new_tokens=config.llm.max_new_tokens,
            load_in_4bit=config.llm.load_in_4bit,
        )
    raise ValueError(f"Unsupported LLM provider: {config.llm.provider}")


def build_alert_sink(config: AppConfig) -> AlertSink | None:
    sinks: list[AlertSink] = []
    if config.alerts.log_alerts:
        sinks.append(ConsoleAlertSink(min_priority=config.alerts.min_priority))
    if config.alerts.webhook_url:
        sinks.append(
            WebhookAlertSink(
                url=config.alerts.webhook_url,
                min_priority=config.alerts.min_priority,
            )
        )
    if not sinks:
        return None
    if len(sinks) == 1:
        return sinks[0]
    return CompositeAlertSink(sinks)


def build_store(config: AppConfig) -> IncidentStore | None:
    if not config.storage.database_url:
        return None
    return IncidentStore(database_url=config.storage.database_url)


def build_pipeline(config: AppConfig) -> MonitoringPipeline:
    return MonitoringPipeline(
        detector=build_detector(config),
        analyzer=build_analyzer(config),
        alert_sink=build_alert_sink(config),
        store=build_store(config),
    )
