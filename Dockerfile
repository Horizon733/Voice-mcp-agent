# syntax=docker/dockerfile:1
# Cross-platform CPU image (Windows / Mac / Linux Docker Desktop).
FROM python:3.11-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    HF_HOME=/data/hf \
    TORCH_HOME=/data/torch \
    XDG_CACHE_HOME=/data/cache \
    TTS_DEVICE=cpu \
    STT_DEVICE=cpu \
    TTS_BACKEND=turbo

RUN apt-get update && apt-get install -y --no-install-recommends \
        ffmpeg \
        git \
        build-essential \
        libsndfile1 \
        libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .

RUN python -m pip install --upgrade pip wheel \
    && pip install "setuptools>=70,<81" \
    && pip install torch==2.6.0 torchaudio==2.6.0 \
        --index-url https://download.pytorch.org/whl/cpu \
    && pip install -r requirements.txt

COPY apps ./apps
COPY api ./api
COPY scripts ./scripts
COPY mcp_servers ./mcp_servers
COPY voices/README.md ./voices/README.md

RUN mkdir -p /data/hf /data/torch /data/cache /app/voices /app/data

EXPOSE 8000

CMD ["uvicorn", "apps.gateway.main:app", "--host", "0.0.0.0", "--port", "8000"]
