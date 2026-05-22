"""Threaded RTSP frame reader.

A background thread reads frames continuously and stores only the
latest one. Consumers always get a fresh frame; older frames are
silently dropped. This avoids OpenCV's stale-buffer problem when the
analyzer is slower than the camera FPS.
"""

from __future__ import annotations

import logging
import threading
import time

import cv2
import numpy as np

logger = logging.getLogger(__name__)


class RTSPStream:
    """Background-threaded RTSP reader that always exposes the freshest frame."""

    def __init__(
        self,
        url: str,
        reconnect_delay_seconds: float = 3.0,
        use_ffmpeg: bool = True,
    ) -> None:
        self.url = url
        self.reconnect_delay = reconnect_delay_seconds
        self.use_ffmpeg = use_ffmpeg

        self._cap: cv2.VideoCapture | None = None
        self._frame: np.ndarray | None = None
        self._frame_id: int = 0
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> RTSPStream:
        if self._thread and self._thread.is_alive():
            return self
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, name="rtsp-reader", daemon=True)
        self._thread.start()
        logger.info("RTSP reader started for %s", self._safe_url())
        return self

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=5.0)
        if self._cap is not None:
            self._cap.release()
            self._cap = None
        logger.info("RTSP reader stopped")

    def __enter__(self) -> RTSPStream:
        return self.start()

    def __exit__(self, exc_type, exc, tb) -> None:
        self.stop()

    def read(self) -> np.ndarray | None:
        """Return the latest frame as a copy, or None if not yet available."""
        with self._lock:
            if self._frame is None:
                return None
            return self._frame.copy()

    def read_with_id(self) -> tuple[np.ndarray | None, int]:
        with self._lock:
            if self._frame is None:
                return None, self._frame_id
            return self._frame.copy(), self._frame_id

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def _open(self) -> bool:
        backend = cv2.CAP_FFMPEG if self.use_ffmpeg else cv2.CAP_ANY
        cap = cv2.VideoCapture(self.url, backend)
        # Keep the OS-side buffer minimal so we don't pile up stale frames.
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        if not cap.isOpened():
            logger.warning("Could not open RTSP stream: %s", self._safe_url())
            cap.release()
            return False
        self._cap = cap
        return True

    def _run(self) -> None:
        while not self._stop_event.is_set():
            if self._cap is None and not self._open():
                if self._stop_event.wait(self.reconnect_delay):
                    return
                continue

            assert self._cap is not None
            ok, frame = self._cap.read()
            if not ok or frame is None:
                logger.warning("RTSP read failed for %s, reconnecting...", self._safe_url())
                self._cap.release()
                self._cap = None
                if self._stop_event.wait(self.reconnect_delay):
                    return
                continue

            with self._lock:
                self._frame = frame
                self._frame_id += 1

            time.sleep(0.001)

    def _safe_url(self) -> str:
        """Return the URL with credentials masked, for log lines."""
        if "@" in self.url and "://" in self.url:
            scheme, rest = self.url.split("://", 1)
            if "@" in rest:
                _, host = rest.split("@", 1)
                return f"{scheme}://***@{host}"
        return self.url
