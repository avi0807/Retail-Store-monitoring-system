FROM python:3.11-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# OpenCV + ffmpeg need libGL and codecs for image decoding and RTSP.
RUN apt-get update && apt-get install -y --no-install-recommends \
        ffmpeg \
        libgl1 \
        libglib2.0-0 \
        libsm6 \
        libxext6 \
        libxrender1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml ./
COPY src ./src
COPY configs ./configs

RUN pip install --upgrade pip && pip install ".[api]"

EXPOSE 8000

# Default to the HTTP API. Override CMD for CLI / RTSP runs.
CMD ["retail-monitor", "serve", "--host", "0.0.0.0", "--port", "8000"]
