FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1
ENV PYTHONPATH=/app/src

WORKDIR /app

COPY pyproject.toml ./
COPY src ./src

RUN python -m pip install --upgrade pip && \
    python -m pip install .

COPY data ./data
COPY scripts ./scripts

RUN mkdir -p /app/.qdrant /app/.sentinel

EXPOSE 8000

CMD ["sh", "-c", "python scripts/ingest.py && exec uvicorn app.api.main:app --host 0.0.0.0 --port 8000"]
