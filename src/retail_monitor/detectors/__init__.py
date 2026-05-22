"""Object detection backends."""

from retail_monitor.detectors.base import ObjectDetector
from retail_monitor.detectors.yolo_world import YOLOWorldDetector

__all__ = ["ObjectDetector", "YOLOWorldDetector"]
