# Architecture

```
                ┌────────────────────────────────────────────────┐
                │                  Frame source                  │
                │  image file • video file • folder • RTSP cam   │
                └────────────────────────┬───────────────────────┘
                                         │ BGR np.ndarray
                                         ▼
                ┌────────────────────────────────────────────────┐
                │           ObjectDetector (YOLO-World)          │
                │   open-vocabulary: spill, trash, fallen, ...   │
                └────────────────────────┬───────────────────────┘
                                         │ List[YOLODetection]
                                         ▼
                ┌────────────────────────────────────────────────┐
                │         VisionAnalyzer (Gemini / Stub)         │
                │  cleanliness • spatial • merchandise • alert   │
                └─────────┬──────────────────────────┬───────────┘
                          │                          │
                          ▼                          ▼
                ┌──────────────────┐        ┌────────────────────┐
                │  IncidentStore   │        │     AlertSinks     │
                │  (SQLite)        │        │  console, webhook  │
                └──────────────────┘        └────────────────────┘
```

## Why this shape

- **Clear seams** between IO, detection, reasoning, and side effects so
  each piece can be swapped or tested independently.
- **Open-vocabulary detector** (YOLO-World) instead of a fixed COCO
  vocabulary. Retail-relevant classes such as `spill`, `trash`, or
  `fallen product` need to be detected by name, not approximated.
- **VisionAnalyzer protocol** means the LLM is replaceable: Gemini
  today, Llava / Moondream / OpenAI tomorrow, all without changing the
  pipeline.
- **AlertSink protocol** lets you wire up Slack, PagerDuty, email, or a
  store dashboard with a tiny adapter.
- **SQLite store** gives an audit trail for free; swap to Postgres by
  replacing one class.

## RTSP

The `RTSPStream` class runs a dedicated reader thread that always
exposes the most recent frame. This avoids OpenCV's classic problem
of reading stale frames from the network buffer when analysis is
slower than the camera FPS, and it auto-reconnects when the stream
drops (common with consumer NVRs).

## Configuration

`configs/default.yaml` is the source of truth for defaults. Secrets
are pulled from the environment (`.env` is read automatically). The
config can be pointed at via `--config` or `RETAIL_MONITOR_CONFIG`.
