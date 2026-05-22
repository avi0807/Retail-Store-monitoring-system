"""FastAPI HTTP service for the retail monitoring system.

Endpoints:
    POST /analyze/image  - upload an image and get analysis
    GET  /incidents      - list recent incidents
    GET  /healthz        - liveness probe
"""

from __future__ import annotations

import logging
from dataclasses import asdict

import cv2
import numpy as np

from retail_monitor.config import AppConfig, load_config
from retail_monitor.factory import build_pipeline
from retail_monitor.models import AnalysisContext, SpaceType, TrafficLevel

logger = logging.getLogger(__name__)


def create_app(config: AppConfig | None = None):
    """Build and return the FastAPI app."""
    from fastapi import FastAPI, File, Form, HTTPException, UploadFile
    from fastapi.middleware.cors import CORSMiddleware

    config = config or load_config()
    pipeline = build_pipeline(config)

    # Module-level singletons: avoids ruff B008 from inline File()/Form() calls.
    file_param = File(...)
    space_param = Form("aisle")
    traffic_param = Form("medium")
    tier_param = Form("standard")
    hours_param = Form(3.0)
    mode_param = Form("cleanliness")
    camera_param = Form(None)

    app = FastAPI(
        title="Retail Store Monitoring API",
        version="0.3.0",
        description="Vision-language powered retail monitoring service.",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.api.cors_origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/healthz")
    def healthz() -> dict:
        return {"status": "ok", "version": "0.3.0"}

    @app.post("/analyze/image")
    async def analyze_image(
        file: UploadFile = file_param,
        space: str = space_param,
        traffic: str = traffic_param,
        tier: str = tier_param,
        hours_cleaned: float = hours_param,
        mode: str = mode_param,
        camera_id: str | None = camera_param,
    ) -> dict:
        try:
            data = await file.read()
            arr = np.frombuffer(data, dtype=np.uint8)
            image = cv2.imdecode(arr, cv2.IMREAD_COLOR)
            if image is None:
                raise HTTPException(status_code=400, detail="Could not decode image.")

            ctx = AnalysisContext(
                space_type=SpaceType(space),
                traffic_level=TrafficLevel(traffic),
                store_tier=tier,
                hours_since_cleaned=hours_cleaned,
                camera_id=camera_id,
            )
            result = pipeline.analyze_frame(image, ctx, mode=mode)

            return {
                "alert": asdict(result.alert_decision),
                "cleanliness": asdict(result.cleanliness_analysis)
                if result.cleanliness_analysis
                else None,
                "merchandise": asdict(result.merchandise_analysis)
                if result.merchandise_analysis
                else None,
                "spatial": asdict(result.spatial_analysis) if result.spatial_analysis else None,
                "detections": [asdict(d) for d in result.raw_detections],
                "timestamp": result.timestamp.isoformat(),
            }
        except HTTPException:
            raise
        except Exception as exc:
            logger.exception("Analysis failed: %s", exc)
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    @app.get("/incidents")
    def list_incidents(limit: int = 50, only_alerts: bool = False) -> dict:
        if pipeline.store is None:
            return {"incidents": []}
        rows = pipeline.store.recent(limit=limit, only_alerts=only_alerts)
        return {"incidents": rows}

    return app


def run(config: AppConfig, host: str = "0.0.0.0", port: int = 8000) -> None:
    import uvicorn

    app = create_app(config)
    uvicorn.run(app, host=host, port=port)
