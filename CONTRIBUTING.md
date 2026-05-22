# Contributing

Thanks for your interest in improving the retail monitoring system.

## Development setup

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -e ".[dev,api]"
cp .env.example .env
```

## Running tests

```bash
pytest
```

These tests use the offline `StubVisionAnalyzer` and a fake detector,
so they run with no API key and no GPU.

## Code style

- `ruff check src tests`
- `black src tests`
- `mypy src` (advisory)

## Project layout

```
src/retail_monitor/
  analyzers/       # Vision LLM backends (Gemini, stub)
  detectors/       # YOLO-World detector
  io/              # RTSP reader, video/image sources
  models/          # Dataclasses and enums
  services/        # Storage and alert sinks
  api.py           # FastAPI service
  cli.py           # Command-line entry point
  config.py        # YAML + env config loader
  factory.py       # Wires components together
  pipeline.py      # Orchestrator
```

## Pull requests

1. Fork and create a feature branch.
2. Add tests for new behavior.
3. Run `ruff`, `black`, and `pytest` locally.
4. Open a PR with a clear description and screenshots if UI/output changes.
