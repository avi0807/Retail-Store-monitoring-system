"""Command-line entry point.

Examples:
    retail-monitor analyze-image media/aisle.jpg --space aisle
    retail-monitor analyze-video media/walkthrough.mp4 --frame-skip 90
    retail-monitor analyze-folder media/ --mode cleanliness
    retail-monitor stream rtsp://user:pass@cam.local/Streaming/Channels/101 \
        --camera-id store-3-aisle-1 --interval 5
    retail-monitor serve --host 0.0.0.0 --port 8000
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

from retail_monitor.config import AppConfig, load_config
from retail_monitor.factory import build_pipeline
from retail_monitor.io import iter_image_files
from retail_monitor.logging_setup import configure_logging
from retail_monitor.models import AnalysisContext, SpaceType, TrafficLevel
from retail_monitor.services.alerts import serialize_result

logger = logging.getLogger(__name__)


def _build_context(args: argparse.Namespace) -> AnalysisContext:
    return AnalysisContext(
        space_type=SpaceType(args.space),
        traffic_level=TrafficLevel(args.traffic),
        store_tier=args.tier,
        hours_since_cleaned=args.hours_cleaned,
        expected_shelf_fullness=args.expected_fullness,
        camera_id=args.camera_id,
        location=args.location,
    )


def _add_common_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--space", default="aisle", choices=[s.value for s in SpaceType])
    p.add_argument("--traffic", default="medium", choices=[t.value for t in TrafficLevel])
    p.add_argument("--tier", default="standard", help="Store tier (standard/premium/budget).")
    p.add_argument("--hours-cleaned", type=float, default=3.0, dest="hours_cleaned")
    p.add_argument("--expected-fullness", type=float, default=80.0, dest="expected_fullness")
    p.add_argument("--camera-id", default=None, dest="camera_id")
    p.add_argument("--location", default=None)
    p.add_argument(
        "--mode",
        default="cleanliness",
        choices=["cleanliness", "merchandise"],
        help="Analysis mode.",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="retail-monitor",
        description="AI-powered retail store monitoring system.",
    )
    parser.add_argument("--config", type=Path, default=None, help="Path to YAML config.")
    parser.add_argument("--log-level", default=None, help="Override log level.")

    sub = parser.add_subparsers(dest="command", required=True)

    img = sub.add_parser("analyze-image", help="Analyze a single image.")
    img.add_argument("path", type=Path)
    _add_common_args(img)

    vid = sub.add_parser("analyze-video", help="Analyze a video file.")
    vid.add_argument("path", type=Path)
    vid.add_argument("--frame-skip", type=int, default=60, dest="frame_skip")
    _add_common_args(vid)

    folder = sub.add_parser("analyze-folder", help="Analyze every image in a folder.")
    folder.add_argument("path", type=Path)
    _add_common_args(folder)

    stream = sub.add_parser("stream", help="Continuously analyze an RTSP camera feed.")
    stream.add_argument("url", help="RTSP URL, e.g. rtsp://user:pass@host/stream")
    stream.add_argument(
        "--interval",
        type=float,
        default=None,
        help="Seconds between samples (overrides config).",
    )
    stream.add_argument(
        "--max-iterations",
        type=int,
        default=None,
        dest="max_iterations",
        help="Stop after N samples (useful for tests).",
    )
    _add_common_args(stream)

    serve = sub.add_parser("serve", help="Run the FastAPI HTTP service.")
    serve.add_argument("--host", default=None)
    serve.add_argument("--port", type=int, default=None)

    return parser


def _print_result(result, label: str) -> None:
    logger.info("=== %s ===", label)
    logger.info(serialize_result(result))


def cmd_analyze_image(args: argparse.Namespace, config: AppConfig) -> int:
    pipeline = build_pipeline(config)
    result = pipeline.analyze_image_file(args.path, _build_context(args), mode=args.mode)
    _print_result(result, str(args.path))
    return 0


def cmd_analyze_video(args: argparse.Namespace, config: AppConfig) -> int:
    pipeline = build_pipeline(config)
    results = pipeline.analyze_video_file(
        args.path,
        _build_context(args),
        mode=args.mode,
        frame_skip=args.frame_skip,
    )
    alerts = [r for r in results if r.alert_decision.alert_required]
    logger.info("Video analysis complete: %d frames, %d alerts.", len(results), len(alerts))
    return 0


def cmd_analyze_folder(args: argparse.Namespace, config: AppConfig) -> int:
    pipeline = build_pipeline(config)
    images = iter_image_files(args.path)
    if not images:
        logger.warning("No images in %s", args.path)
        return 1
    for img in images:
        result = pipeline.analyze_image_file(img, _build_context(args), mode=args.mode)
        _print_result(result, img.name)
    return 0


def cmd_stream(args: argparse.Namespace, config: AppConfig) -> int:
    pipeline = build_pipeline(config)
    interval = args.interval if args.interval is not None else config.stream.sample_interval_seconds
    try:
        for result in pipeline.stream_rtsp(
            args.url,
            _build_context(args),
            mode=args.mode,
            sample_interval_seconds=interval,
            max_iterations=args.max_iterations,
        ):
            if result.alert_decision.alert_required:
                logger.warning(
                    "RTSP alert (priority=%s): %s",
                    result.alert_decision.priority.value,
                    result.alert_decision.reasoning,
                )
    except KeyboardInterrupt:
        logger.info("Stream stopped by user.")
    return 0


def cmd_serve(args: argparse.Namespace, config: AppConfig) -> int:
    from retail_monitor.api import run as run_api

    host = args.host or config.api.host
    port = args.port or config.api.port
    run_api(config, host=host, port=port)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    config = load_config(args.config)
    log_level = args.log_level or config.log_level
    configure_logging(log_level)

    dispatch = {
        "analyze-image": cmd_analyze_image,
        "analyze-video": cmd_analyze_video,
        "analyze-folder": cmd_analyze_folder,
        "stream": cmd_stream,
        "serve": cmd_serve,
    }
    handler = dispatch[args.command]
    return handler(args, config)


if __name__ == "__main__":
    raise SystemExit(main())
