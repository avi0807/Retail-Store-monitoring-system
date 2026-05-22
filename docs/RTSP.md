# Connecting RTSP cameras

The `retail-monitor stream` command connects to an RTSP feed, samples
frames at a fixed cadence, and runs them through the analysis pipeline.

## Quick start

```bash
retail-monitor stream "rtsp://user:pass@192.168.1.50:554/Streaming/Channels/101" \
    --camera-id store-3-aisle-1 \
    --space aisle \
    --traffic high \
    --interval 5
```

## URL formats by vendor

| Vendor      | Example URL                                               |
|-------------|-----------------------------------------------------------|
| Hikvision   | `rtsp://user:pass@host:554/Streaming/Channels/101`        |
| Dahua       | `rtsp://user:pass@host:554/cam/realmonitor?channel=1&subtype=0` |
| Axis        | `rtsp://user:pass@host/axis-media/media.amp`              |
| Reolink     | `rtsp://user:pass@host:554/h264Preview_01_main`           |
| Generic ONVIF | `rtsp://user:pass@host:554/onvif1`                      |

Use the **substream** (lower resolution) when possible: it is enough
for vision models and keeps bandwidth and decode cost low.

## Tuning

In `configs/default.yaml`:

```yaml
stream:
  sample_interval_seconds: 5.0    # How often to analyze.
  reconnect_delay_seconds: 3.0    # Wait between reconnect attempts.
```

- `sample_interval_seconds` is the dominant cost knob. With Gemini
  Flash, 1 sample / 5 s per camera ~= 720 calls/hour.
- The threaded reader always serves the freshest frame, so you can
  raise this to 30+ seconds for slower-changing scenes (backrooms).

## Multiple cameras

Run one process per camera, each with its own `--camera-id`. Compose
example:

```yaml
services:
  cam-aisle-1:
    image: retail-monitor:latest
    command: ["retail-monitor", "stream", "rtsp://...", "--camera-id=aisle-1"]
  cam-checkout:
    image: retail-monitor:latest
    command: ["retail-monitor", "stream", "rtsp://...", "--camera-id=checkout"]
```

Each writes to the shared SQLite store and shared webhook.

## Security

- Never commit RTSP URLs containing credentials. Put them in `.env`.
- The reader masks credentials in log output (`rtsp://***@host`).
- Place cameras on an isolated VLAN; expose only the analyzer host
  to the internet, never the camera directly.
