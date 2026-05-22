# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.3.0] - 2026-05-22

### Added
- **Local Qwen2.5-VL backend** (`provider: qwen`) as an alternative to
  Gemini. Uses Hugging Face Transformers and runs entirely offline.
  Lives behind the `[local]` optional install group so the default
  install stays light.
- New `local_device`, `local_dtype`, `load_in_4bit`, and
  `max_new_tokens` knobs in `LLMConfig` for the Qwen backend.
- Factory tests covering provider selection across stub / gemini /
  qwen / unknown.

### Changed
- Default cloud model bumped from `gemini-2.5-flash` to
  `gemini-3.5-flash` (GA May 19, 2026).

## [0.2.0] - 2026-05-22

### Added
- Modular package layout under `src/retail_monitor/`.
- RTSP streaming support with a threaded reader, automatic reconnect,
  and credential-safe logging.
- Open-vocabulary detection via **YOLO-Worldv2** (`yolov8s-worldv2.pt`),
  with automatic fallback to `yolov8m.pt`. Replaces the original
  generic `yolov8n` COCO detector.
- FastAPI HTTP service with `/analyze/image`, `/incidents`, `/healthz`.
- SQLite incident store for audit trails and dashboards.
- Alert sinks: console + Slack/webhook, with priority thresholds.
- Stub analyzer for offline tests / CI / demos without an API key.
- YAML-based config (`configs/default.yaml`) with env var overrides.
- `retail-monitor` CLI with `analyze-image`, `analyze-video`,
  `analyze-folder`, `stream`, and `serve` subcommands.
- Dockerfile and `docker-compose.yml` for API + RTSP worker deployment.
- GitHub Actions CI (lint, type-check, tests across Python 3.10–3.12).
- Test suite covering config, JSON parsing, pipeline, storage, alerts.

### Changed
- LLM prompts moved to `analyzers/prompts.py` for easier iteration.
- Robust JSON parsing centralized in `analyzers/json_utils.py`.

### Deprecated
- The top-level `retail_monitor.py` script has been removed because it
  collided with the `retail_monitor` package. A compatibility shim
  lives at `scripts/legacy_entry.py`. Use the `retail-monitor` console
  script installed via `pip install -e .`.

## [0.1.0] - 2025
- Initial single-file proof of concept.
