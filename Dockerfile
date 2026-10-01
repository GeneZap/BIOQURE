# BIOQURE locked inference service
FROM python:3.13-slim-bookworm

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    MALLOC_ARENA_MAX=2

WORKDIR /app

# Install only the pinned locked inference runtime.
COPY backend/requirements-runtime.txt /app/backend/requirements-runtime.txt
RUN pip install --no-cache-dir -r /app/backend/requirements-runtime.txt

# Application, runtime artifacts, and public demo pool.
COPY backend /app/backend

ENV HOST=0.0.0.0 \
    PORT=8000 \
    BIOQURE_CORS_ORIGINS="" \
    PYTHONPATH=/app

EXPOSE 8000

CMD ["sh", "-c", "python -m backend.inference_service.server \"${PORT:-8000}\""]
