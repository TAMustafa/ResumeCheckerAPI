# syntax=docker/dockerfile:1
FROM python:3.12-slim as base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    VENV_PATH=/opt/venv \
    DEBIAN_FRONTEND=noninteractive \
    LOGFIRE_API_KEY= \
    LOGFIRE_PROJECT= \
    LOGFIRE_DISABLED=1 \
    ALLOWED_ORIGINS= \
    DOMAIN=

WORKDIR /app

# Minimal system deps (add curl for healthchecks). Use noninteractive debconf to avoid TTY warnings.
RUN apt-get update && apt-get install -yq --no-install-recommends ca-certificates curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user and prepare ownership for venv directory and /app
RUN useradd -m appuser \
    && mkdir -p "$VENV_PATH" \
    && chown -R appuser:appuser "$VENV_PATH" \
    && chown -R appuser:appuser /app

# Switch to non-root and create venv as appuser
USER appuser
RUN python -m venv "$VENV_PATH"
ENV PATH="$VENV_PATH/bin:$PATH"

# Install dependencies from requirements.txt as non-root
COPY --chown=appuser:appuser requirements.txt /app/
RUN pip install -r requirements.txt

# Copy source as non-root
COPY --chown=appuser:appuser . /app

# Create upload dir with correct ownership
RUN mkdir -p /app/uploaded_cvs
RUN chmod +x /app/entrypoint.sh

# Env (configurable Gunicorn)
ENV PORT=8000 \
    HOST=0.0.0.0 \
    GUNICORN_WORKERS=2 \
    GUNICORN_THREADS=1 \
    GUNICORN_TIMEOUT=60 \
    GUNICORN_KEEPALIVE=5

# Expose port
EXPOSE 8000

# Entrypoint handles volume permissions then starts the app with env-driven settings
ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["sh", "-lc", "${VENV_PATH}/bin/gunicorn -w ${GUNICORN_WORKERS} --threads ${GUNICORN_THREADS} -k uvicorn.workers.UvicornWorker app:app --bind 0.0.0.0:${PORT} --timeout ${GUNICORN_TIMEOUT} --keep-alive ${GUNICORN_KEEPALIVE} --access-logfile - --log-level info"]
