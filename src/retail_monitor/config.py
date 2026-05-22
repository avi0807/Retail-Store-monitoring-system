"""Application configuration loaded from YAML and environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

DEFAULT_CONFIG_PATH = Path("configs/default.yaml")


@dataclass
class DetectorConfig:
    model: str = "yolov8s-worldv2.pt"
    fallback_model: str = "yolov8m.pt"
    confidence: float = 0.25
    iou_threshold: float = 0.45
    device: str = "auto"
    classes: list[str] = field(
        default_factory=lambda: [
            "person",
            "shopping cart",
            "trash",
            "spill",
            "cardboard box",
            "bottle",
            "bag",
            "fallen product",
            "wet floor sign",
            "shelf",
        ]
    )


@dataclass
class LLMConfig:
    provider: str = "gemini"
    model: str = "gemini-3.5-flash"
    temperature: float = 0.1
    max_retries: int = 2
    timeout_seconds: int = 30
    local_device: str = "auto"
    local_dtype: str = "auto"
    load_in_4bit: bool = False
    max_new_tokens: int = 1024


@dataclass
class StreamConfig:
    sample_interval_seconds: float = 5.0
    video_frame_skip: int = 60
    reconnect_delay_seconds: float = 3.0
    reader_buffer_frames: int = 1


@dataclass
class StorageConfig:
    database_url: str = "sqlite:///./retail_monitor.db"
    snapshot_dir: str = "./snapshots"
    keep_snapshot_days: int = 14


@dataclass
class AlertConfig:
    webhook_url: str | None = None
    min_priority: str = "medium"
    log_alerts: bool = True


@dataclass
class APIConfig:
    host: str = "0.0.0.0"
    port: int = 8000
    cors_origins: list[str] = field(default_factory=lambda: ["*"])


@dataclass
class AppConfig:
    detector: DetectorConfig = field(default_factory=DetectorConfig)
    llm: LLMConfig = field(default_factory=LLMConfig)
    stream: StreamConfig = field(default_factory=StreamConfig)
    storage: StorageConfig = field(default_factory=StorageConfig)
    alerts: AlertConfig = field(default_factory=AlertConfig)
    api: APIConfig = field(default_factory=APIConfig)
    log_level: str = "INFO"

    gemini_api_key: str | None = None
    openai_api_key: str | None = None


def _from_dict(cls, data: dict[str, Any]):
    """Build a dataclass from a (possibly partial) dict, ignoring extras."""
    if not data:
        return cls()
    field_names = {f.name for f in cls.__dataclass_fields__.values()}
    filtered = {k: v for k, v in data.items() if k in field_names}
    return cls(**filtered)


def load_config(path: Path | None = None) -> AppConfig:
    """Load config from YAML and overlay environment variables.

    Resolution order:
    1. Explicit ``path`` argument.
    2. ``RETAIL_MONITOR_CONFIG`` env var.
    3. ``configs/default.yaml`` if present.
    4. Pure dataclass defaults.
    """
    load_dotenv()

    config_path: Path | None
    if path is not None:
        config_path = Path(path)
    elif os.getenv("RETAIL_MONITOR_CONFIG"):
        config_path = Path(os.environ["RETAIL_MONITOR_CONFIG"])
    elif DEFAULT_CONFIG_PATH.exists():
        config_path = DEFAULT_CONFIG_PATH
    else:
        config_path = None

    raw: dict[str, Any] = {}
    if config_path and config_path.exists():
        with config_path.open("r", encoding="utf-8") as f:
            raw = yaml.safe_load(f) or {}

    cfg = AppConfig(
        detector=_from_dict(DetectorConfig, raw.get("detector", {})),
        llm=_from_dict(LLMConfig, raw.get("llm", {})),
        stream=_from_dict(StreamConfig, raw.get("stream", {})),
        storage=_from_dict(StorageConfig, raw.get("storage", {})),
        alerts=_from_dict(AlertConfig, raw.get("alerts", {})),
        api=_from_dict(APIConfig, raw.get("api", {})),
        log_level=raw.get("log_level", "INFO"),
    )

    cfg.gemini_api_key = os.getenv("GEMINI_API_KEY")
    cfg.openai_api_key = os.getenv("OPENAI_API_KEY")

    if os.getenv("RETAIL_MONITOR_LOG_LEVEL"):
        cfg.log_level = os.environ["RETAIL_MONITOR_LOG_LEVEL"]
    if os.getenv("RETAIL_MONITOR_WEBHOOK_URL"):
        cfg.alerts.webhook_url = os.environ["RETAIL_MONITOR_WEBHOOK_URL"]
    if os.getenv("RETAIL_MONITOR_DEVICE"):
        cfg.detector.device = os.environ["RETAIL_MONITOR_DEVICE"]

    return cfg
