"""Video file and image folder sources."""

from __future__ import annotations

import logging
from collections.abc import Iterator
from pathlib import Path

import cv2
import numpy as np

logger = logging.getLogger(__name__)

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
VIDEO_EXTS = {".mp4", ".avi", ".mov", ".mkv", ".webm"}


def iter_image_files(folder: Path) -> list[Path]:
    """Return a sorted list of image files in *folder* (non-recursive)."""
    folder = Path(folder)
    if not folder.exists():
        return []
    return sorted(p for p in folder.iterdir() if p.suffix.lower() in IMAGE_EXTS)


class VideoFileSource:
    """Iterate frames from a video file with optional frame skipping."""

    def __init__(self, path: str | Path, frame_skip: int = 60) -> None:
        self.path = str(path)
        self.frame_skip = max(1, int(frame_skip))

    def iter_frames(self) -> Iterator[tuple[int, np.ndarray]]:
        cap = cv2.VideoCapture(self.path)
        if not cap.isOpened():
            raise FileNotFoundError(f"Cannot open video: {self.path}")
        try:
            idx = 0
            while True:
                ok, frame = cap.read()
                if not ok:
                    break
                if idx % self.frame_skip == 0:
                    yield idx, frame
                idx += 1
        finally:
            cap.release()
