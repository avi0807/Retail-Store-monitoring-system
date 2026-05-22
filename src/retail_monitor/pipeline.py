"""High-level orchestration: detector + analyzer + sinks + storage."""

from __future__ import annotations

import logging
from collections.abc import Iterable
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np

from retail_monitor.analyzers.base import VisionAnalyzer
from retail_monitor.detectors.base import ObjectDetector
from retail_monitor.io import RTSPStream, VideoFileSource
from retail_monitor.models import (
    AnalysisContext,
    AnalysisResult,
)
from retail_monitor.services.alerts import AlertSink
from retail_monitor.services.storage import IncidentStore

logger = logging.getLogger(__name__)


class MonitoringPipeline:
    """Coordinates detection, analysis, alerting, and persistence."""

    def __init__(
        self,
        detector: ObjectDetector,
        analyzer: VisionAnalyzer,
        alert_sink: AlertSink | None = None,
        store: IncidentStore | None = None,
    ) -> None:
        self.detector = detector
        self.analyzer = analyzer
        self.alert_sink = alert_sink
        self.store = store

    def analyze_frame(
        self,
        image: np.ndarray,
        context: AnalysisContext,
        mode: str = "cleanliness",
        frame_index: int | None = None,
    ) -> AnalysisResult:
        """Run one frame through the full pipeline."""
        detections, _, _ = self.detector.detect(image)
        logger.debug("Detector found %d objects", len(detections))

        cleanliness = spatial = merchandise = None
        if mode == "cleanliness":
            cleanliness, spatial = self.analyzer.analyze_cleanliness(image, detections, context)
        elif mode == "merchandise":
            merchandise = self.analyzer.analyze_merchandise(image, detections, context)
        else:
            raise ValueError(f"Unknown analysis mode: {mode}")

        decision = self.analyzer.make_alert_decision(
            cleanliness=cleanliness,
            spatial=spatial,
            merchandise=merchandise,
            context=context,
        )

        result = AnalysisResult(
            alert_decision=decision,
            raw_detections=detections,
            cleanliness_analysis=cleanliness,
            spatial_analysis=spatial,
            merchandise_analysis=merchandise,
            timestamp=datetime.utcnow(),
            camera_id=context.camera_id,
            frame_index=frame_index,
        )

        if self.store is not None:
            try:
                self.store.record(result)
            except Exception as exc:
                logger.exception("Failed to record incident: %s", exc)
        if self.alert_sink is not None:
            self.alert_sink.emit(result)

        return result

    def analyze_image_file(
        self,
        path: str | Path,
        context: AnalysisContext,
        mode: str = "cleanliness",
    ) -> AnalysisResult:
        image = cv2.imread(str(path))
        if image is None:
            raise FileNotFoundError(f"Cannot read image: {path}")
        return self.analyze_frame(image, context, mode=mode)

    def analyze_video_file(
        self,
        path: str | Path,
        context: AnalysisContext,
        mode: str = "cleanliness",
        frame_skip: int = 60,
    ) -> list[AnalysisResult]:
        results: list[AnalysisResult] = []
        for idx, frame in VideoFileSource(path, frame_skip=frame_skip).iter_frames():
            logger.info("Analyzing video frame %d (%s)", idx, Path(path).name)
            results.append(self.analyze_frame(frame, context, mode=mode, frame_index=idx))
        return results

    def stream_rtsp(
        self,
        url: str,
        context: AnalysisContext,
        mode: str = "cleanliness",
        sample_interval_seconds: float = 5.0,
        max_iterations: int | None = None,
    ) -> Iterable[AnalysisResult]:
        """Iterate analyses from an RTSP stream until interrupted."""
        import time

        with RTSPStream(url) as stream:
            i = 0
            # Wait briefly for the first frame to land.
            deadline = time.time() + 10.0
            while stream.read() is None and time.time() < deadline:
                time.sleep(0.2)

            while True:
                if max_iterations is not None and i >= max_iterations:
                    return
                frame, frame_id = stream.read_with_id()
                if frame is None:
                    logger.warning("No frame yet from RTSP, waiting...")
                    time.sleep(sample_interval_seconds)
                    continue
                logger.info("RTSP tick %d (frame_id=%d)", i, frame_id)
                yield self.analyze_frame(frame, context, mode=mode, frame_index=frame_id)
                i += 1
                time.sleep(sample_interval_seconds)
