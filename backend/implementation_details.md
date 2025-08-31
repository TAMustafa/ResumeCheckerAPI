## Upload size enforcement

- `app.py` enforces a configurable max upload size via `MAX_UPLOAD_MB` (default 10MB).
- Checks both `Content-Length` (when provided) and on-disk file size after write; returns HTTP 413 if exceeded.

## Reverse proxy (Caddy) hardening

- `Caddyfile` uses `{$DOMAIN}` for automatic HTTPS certificates and adds security headers (HSTS, X-Content-Type-Options, X-Frame-Options, Referrer-Policy, Permissions-Policy).
- HTTP (:80) redirects to HTTPS for the configured domain.

## Gunicorn runtime settings

- `Dockerfile` exposes env-driven Gunicorn parameters: `GUNICORN_WORKERS`, `GUNICORN_THREADS`, `GUNICORN_TIMEOUT`, `GUNICORN_KEEPALIVE`, and `PORT`.
- Defaults: 2 workers, 1 thread, 60s timeout, 5s keepalive. Tune per CPU and expected latency.

# Implementation Details

## In-memory caching

- Added `cache_utils.py` providing `TTLCache` with LRU eviction and async locking.
- Shared instance: `shared_cache = TTLCache(maxsize=512, ttl_seconds=1200)`.
- Cache keys
  - `vacancy:v1:{sha256(vacancy_text)}` for `analyze_job_vacancy()`.
  - `cv:v1:{sha256(pdf_bytes)}` for `analyze_cv()`.
  - `score:v1:{sha256(sorted_json_payload)}` for `score_cv_match()`.
- Cached values are plain dicts from Pydantic models to keep serialization simple.
- TTL chosen (20 min) to balance freshness vs cost/latency. Adjust as needed.

## Timeouts

- Wrapped agent `.run()` calls with `asyncio.wait_for()` timeouts:
  - Vacancy: 60s
  - CV analysis: 90s
  - Scoring: 60s

## Prompt/Agent usage

- Replaced wildcard import from `prompts` with explicit imports for clarity.
- Scoring prompt now includes explicit JSON for both CV analysis and job requirements to ensure full context while caching uses a stable, sorted JSON payload.

## Non-invasive changes

- No schema changes to `models.py`.
- No API changes in `app.py` endpoints.
- Caching is additive and transparent to callers.

## Per-request OpenAI API key handling

- The backend supports a header `X-OpenAI-Key` to use a user's OpenAI key for a single request.
- Implementation: `_ApiKeyContext` (in `agents.py`) temporarily sets `OPENAI_API_KEY` in `os.environ` while holding a global `asyncio.Lock` to ensure concurrency safety across requests.
- Functions updated: `analyze_job_vacancy()`, `analyze_cv()`, `score_cv_match()` now accept `api_key: str | None` passed from `app.py` route handlers.
- Fallback: if header is missing, the environment `OPENAI_API_KEY` is used if present.

## CORS configuration

- `ALLOWED_ORIGINS` environment variable (comma-separated) controls allowed origins in `app.py`.
- Example: `ALLOWED_ORIGINS=https://api.example.com,chrome-extension://<extension-id>`
- Default for dev includes `http://localhost:8000` and `chrome-extension://*`.

## Health endpoint

- `GET /healthz` returns `{ "status": "ok" }` for load balancers and deployment checks.
