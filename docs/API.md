# HTTP API

Start the service:

```bash
retail-monitor serve --host 0.0.0.0 --port 8000
```

Interactive docs are available at `http://localhost:8000/docs`.

## Endpoints

### `GET /healthz`

Liveness probe.

```json
{ "status": "ok", "version": "0.2.0" }
```

### `POST /analyze/image`

Multipart form upload.

| Field          | Type   | Default      |
|----------------|--------|--------------|
| `file`         | file   | required     |
| `space`        | enum   | `aisle`      |
| `traffic`      | enum   | `medium`     |
| `tier`         | string | `standard`   |
| `hours_cleaned`| float  | `3.0`        |
| `mode`         | enum   | `cleanliness`|
| `camera_id`    | string | `null`       |

```bash
curl -F "file=@aisle.jpg" \
     -F "space=aisle" \
     -F "traffic=high" \
     http://localhost:8000/analyze/image
```

Response (abridged):

```json
{
  "alert": {
    "alert_required": true,
    "priority": "high",
    "reasoning": "Spill detected near checkout",
    "recommended_action": "Clean immediately, place wet floor sign",
    "estimated_time_minutes": 10,
    "confidence_level": 0.9
  },
  "cleanliness": { "overall_cleanliness_score": 3.5, "...": "..." },
  "detections": [{ "class_name": "spill", "confidence": 0.87, "bbox": [10, 20, 80, 110] }],
  "timestamp": "2026-05-22T14:20:11.123456"
}
```

### `GET /incidents`

| Query param   | Type | Default |
|---------------|------|---------|
| `limit`       | int  | 50      |
| `only_alerts` | bool | false   |

Returns recent incidents stored in SQLite.
