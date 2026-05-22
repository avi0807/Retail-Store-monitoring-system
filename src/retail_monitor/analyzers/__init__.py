"""LLM-backed analyzers."""

from retail_monitor.analyzers.base import VisionAnalyzer
from retail_monitor.analyzers.gemini_analyzer import GeminiVisionAnalyzer
from retail_monitor.analyzers.stub_analyzer import StubVisionAnalyzer

__all__ = [
    "VisionAnalyzer",
    "GeminiVisionAnalyzer",
    "StubVisionAnalyzer",
    "get_qwen_analyzer",
]


def get_qwen_analyzer():
    """Lazy accessor: imports torch + transformers only on demand."""
    from retail_monitor.analyzers.qwen_analyzer import QwenVisionAnalyzer

    return QwenVisionAnalyzer
