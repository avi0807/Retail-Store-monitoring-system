"""Tests for the analyzer factory provider selection."""

from __future__ import annotations

import pytest

from retail_monitor.analyzers import StubVisionAnalyzer
from retail_monitor.config import AppConfig
from retail_monitor.factory import build_analyzer


def test_stub_provider_returns_stub():
    cfg = AppConfig()
    cfg.llm.provider = "stub"
    assert isinstance(build_analyzer(cfg), StubVisionAnalyzer)


def test_gemini_without_key_falls_back_to_stub(caplog):
    cfg = AppConfig()
    cfg.llm.provider = "gemini"
    cfg.gemini_api_key = None
    with caplog.at_level("WARNING"):
        analyzer = build_analyzer(cfg)
    assert isinstance(analyzer, StubVisionAnalyzer)
    assert "GEMINI_API_KEY" in caplog.text


def test_unknown_provider_raises():
    cfg = AppConfig()
    cfg.llm.provider = "definitely-not-real"
    with pytest.raises(ValueError, match="Unsupported LLM provider"):
        build_analyzer(cfg)


def test_qwen_provider_constructs_via_factory(monkeypatch):
    """The qwen branch should hand off to the Qwen analyzer.

    Patching ``get_qwen_analyzer`` lets this run without torch/transformers.
    """
    constructed = {}

    class FakeQwen:
        def __init__(self, **kwargs):
            constructed.update(kwargs)

    import retail_monitor.analyzers as analyzers_pkg

    monkeypatch.setattr(analyzers_pkg, "get_qwen_analyzer", lambda: FakeQwen)

    cfg = AppConfig()
    cfg.llm.provider = "qwen"
    cfg.llm.model = "Qwen/Qwen2.5-VL-7B-Instruct"
    cfg.llm.local_device = "cpu"
    cfg.llm.local_dtype = "auto"
    cfg.llm.max_new_tokens = 256
    cfg.llm.load_in_4bit = False

    analyzer = build_analyzer(cfg)
    assert isinstance(analyzer, FakeQwen)
    assert constructed["model_id"] == "Qwen/Qwen2.5-VL-7B-Instruct"
    assert constructed["device"] == "cpu"
    assert constructed["max_new_tokens"] == 256
    assert constructed["load_in_4bit"] is False
