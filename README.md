# Retail Store Monitoring System

[![CI](https://github.com/avi/Retail-Store-monitoring-system/actions/workflows/ci.yml/badge.svg)](https://github.com/avi/Retail-Store-monitoring-system/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

Vision-language powered monitoring for retail stores. Connects to
RTSP cameras (or processes images, video files, and folders), detects
retail-relevant events with **YOLO-Worldv2** (open-vocabulary), and
uses a vision LLM (Gemini by default) to produce structured
cleanliness, merchandise, and alert decisions with explainable
reasoning.

## Why this exists

Generic COCO-trained detectors like `yolov8n` only know 80 classes,
none of which are "spill", "trash on floor", or "fallen product".
This system swaps in **YOLO-World**, an open-vocabulary detector that
accepts a retail-specific class list at runtime, then hands the
detections plus the image to a vision LLM for spatial reasoning and
prioritized alerting.

## Features

- **Open-vocabulary detection** with YOLO-Worldv2 (`yolov8s-worldv2.pt`),
  with automatic fallback to YOLOv8m.
- **RTSP support** with a threaded reader, automatic reconnect, and
  credential-safe logging.
- **Pluggable analyzers** behind a single `VisionAnalyzer` protocol:
  - `gemini` — Google Gemini 3.5 Flash (cloud, default).
  - `qwen` — Qwen2.5-VL-7B-Instruct via Hugging Face Transformers
    (local, fully offline; install with `pip install '.[local]'`).
  - `stub` — deterministic offline analyzer for tests, CI, and demos
    without an API key.
- **HTTP API** built on FastAPI, plus a CLI.
- **SQLite incident store** for audit trails.
- **Alert dispatch** to console + webhook (Slack, PagerDuty, etc.)
  with priority thresholds.
- **Containerized** with Dockerfile + Compose for API and per-camera
  RTSP workers.
- **Tested**: pytest suite that runs offline (no API key required).

## Architecture

```
RTSP / image / video → YOLO-World detector → Vision LLM analyzer
                                ↓                       ↓
                           detections          cleanliness / merchandise
                                                    / alert decision
                                ↓                       ↓
                          SQLite store          alert sinks (log, webhook)
```

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for the full picture.

## Install

```bash
git clone https://github.com/avi/Retail-Store-monitoring-system.git
cd Retail-Store-monitoring-system
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -e ".[api]"
cp .env.example .env                # then add your GEMINI_API_KEY
```

For the local Qwen2.5-VL backend (no cloud calls):

```bash
pip install -e ".[api,local]"
# then in configs/default.yaml:
#   llm:
#     provider: qwen
#     model: Qwen/Qwen2.5-VL-7B-Instruct
```

## Quick start

### Single image

```bash
retail-monitor analyze-image media/aisle.jpg --space aisle --traffic high
```

### Folder of images

```bash
retail-monitor analyze-folder media/ --mode cleanliness
```

### Video file

```bash
retail-monitor analyze-video media/walkthrough.mp4 --frame-skip 90
```

### Live RTSP camera

```bash
retail-monitor stream "rtsp://user:pass@192.168.1.50:554/Streaming/Channels/101" \
    --camera-id store-3-aisle-1 \
    --space aisle \
    --traffic high \
    --interval 5
```

The reader runs in a background thread and always serves the most
recent frame, so analysis never falls behind. See
[`docs/RTSP.md`](docs/RTSP.md) for vendor-specific URL formats and
tuning tips.

### HTTP API

```bash
retail-monitor serve --host 0.0.0.0 --port 8000
# Then visit http://localhost:8000/docs for interactive Swagger UI.

curl -F "file=@media/aisle.jpg" http://localhost:8000/analyze/image
```

See [`docs/API.md`](docs/API.md) for the full endpoint reference.

### Docker

```bash
cp .env.example .env                   # add GEMINI_API_KEY and RTSP_URL
docker compose -f docker/docker-compose.yml up --build api
docker compose -f docker/docker-compose.yml --profile rtsp up rtsp-worker
```

## Configuration

Defaults live in `configs/default.yaml`. Override with `--config
path/to.yaml` or `RETAIL_MONITOR_CONFIG=...`. Secrets come from `.env`.

```yaml
detector:
  model: yolov8s-worldv2.pt
  classes: [person, trash, spill, fallen product, cardboard box, ...]
llm:
  provider: gemini      # gemini | qwen | stub
  model: gemini-3.5-flash
stream:
  sample_interval_seconds: 5.0
alerts:
  webhook_url: null
  min_priority: medium
```

## Running tests

```bash
pip install -e ".[dev]"
pytest
```

The test suite uses the offline `StubVisionAnalyzer` and a fake
detector, so it runs with no network, no API key, and no GPU.

## Project layout

```
src/retail_monitor/
  analyzers/    # Gemini + stub VisionAnalyzer implementations
  detectors/    # YOLO-World wrapper
  io/           # RTSP, video file, image folder sources
  models/       # Dataclasses and enums
  services/     # SQLite store + alert sinks
  api.py        # FastAPI service
  cli.py        # `retail-monitor` entry point
  config.py     # YAML + env config
  factory.py    # Wires components together
  pipeline.py   # Detector + analyzer + sinks orchestrator
configs/        # Default YAML config
docker/         # Dockerfile + compose
docs/           # ARCHITECTURE, API, RTSP guides
scripts/        # smoke_rtsp.py and other utilities
tests/          # Offline pytest suite
```


