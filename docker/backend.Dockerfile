FROM python:3.13-slim

ENV PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg git curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml uv.lock README.md ./
COPY app ./app
COPY spotdl ./spotdl

RUN python -m pip install --upgrade pip \
    && python -m pip install -e . pytest pytest-asyncio "httpx>=0.24,<0.25"

EXPOSE 8800

CMD ["python", "-m", "uvicorn", "app.backend.main:app", "--host", "0.0.0.0", "--port", "8800", "--reload", "--reload-dir", "/app/app", "--reload-dir", "/app/spotdl"]
