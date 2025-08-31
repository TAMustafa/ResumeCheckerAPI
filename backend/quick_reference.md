# Quick Reference

- Base URL: http://$IP (Caddy on :80) until DOMAIN is configured
- Health: GET /healthz -> {"status":"ok"}

Env vars
- REQUIRE_USER_API_KEY: enforce per-request key header (default true)
- OPENAI_API_KEY: optional server fallback key (avoid setting when REQUIRE_USER_API_KEY=true)
- ALLOWED_ORIGINS: comma-separated list of allowed origins (e.g., http://$IP,chrome-extension://<id>)
- DOMAIN: domain served by Caddy (required for HTTPS)
- MAX_UPLOAD_MB: max upload size in MB (default 10)
- GUNICORN_WORKERS: default 2
- GUNICORN_THREADS: default 1
- GUNICORN_TIMEOUT: default 60
- GUNICORN_KEEPALIVE: default 5

Request headers
- X-OpenAI-Key: per-request user key (required when REQUIRE_USER_API_KEY=true)
- X-LLM-Provider: optional; current supported value: "openai" (others return 400)
- X-LLM-Model: optional; model name for the selected provider
  - Examples: OpenAI "gpt-4o" (default), "gpt-4.1-mini"
  - If omitted, defaults to a sensible model per provider (OpenAI defaults to gpt-4o)

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
