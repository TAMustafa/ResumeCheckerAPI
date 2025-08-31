# Quick Reference

- Base URL: https://$DOMAIN
- Health: GET /healthz -> {"status":"ok"}

Env vars
- OPENAI_API_KEY: optional server fallback key
- X-OpenAI-Key: per-request header for user key (preferred)
- ALLOWED_ORIGINS: comma-separated list of allowed origins (e.g., https://api.example.com,chrome-extension://<id>)
- DOMAIN: domain served by Caddy (required for HTTPS)
- MAX_UPLOAD_MB: max upload size in MB (default 10)
- GUNICORN_WORKERS: default 2
- GUNICORN_THREADS: default 1
- GUNICORN_TIMEOUT: default 60
- GUNICORN_KEEPALIVE: default 5

Key endpoints
- POST /analyze-job-vacancy { vacancy_text }
- POST /analyze-cv (multipart file=PDF)
- POST /score-cv-match { cv_analysis, job_requirements }
- GET /api/uploaded-cvs
- DELETE /api/uploaded-cvs/{filename}
- GET /uploaded_cvs/{filename}

Docker/compose
- Build+run: docker compose up -d --build
- Volumes: uploaded_cvs persisted
- Healthchecks: app (/healthz), caddy (port 80)

CORS
- Controlled by ALLOWED_ORIGINS env in backend/app.py

Logging/observability
- logfire auto-configured; set LOGFIRE_API_KEY and LOGFIRE_PROJECT to send telemetry.
