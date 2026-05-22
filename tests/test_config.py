"""Tests for the configuration loader."""

from pathlib import Path

from retail_monitor.config import load_config


def test_defaults_load_when_no_file(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("RETAIL_MONITOR_CONFIG", raising=False)
    cfg = load_config()
    assert cfg.detector.model.endswith(".pt")
    assert cfg.llm.provider in {"gemini", "stub"}
    assert cfg.api.port == 8000


def test_yaml_overrides(monkeypatch, tmp_path: Path):
    cfg_file = tmp_path / "cfg.yaml"
    cfg_file.write_text(
        """
log_level: DEBUG
detector:
  model: yolov8m.pt
  confidence: 0.4
llm:
  provider: stub
api:
  port: 9001
""",
        encoding="utf-8",
    )
    cfg = load_config(cfg_file)
    assert cfg.log_level == "DEBUG"
    assert cfg.detector.model == "yolov8m.pt"
    assert cfg.detector.confidence == 0.4
    assert cfg.llm.provider == "stub"
    assert cfg.api.port == 9001


def test_env_override_log_level(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("RETAIL_MONITOR_LOG_LEVEL", "ERROR")
    cfg = load_config()
    assert cfg.log_level == "ERROR"
