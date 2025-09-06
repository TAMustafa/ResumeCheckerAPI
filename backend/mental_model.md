# Mental Model

- Architecture
  - FastAPI app (`app.py`) exposes REST endpoints for analyzing job vacancies, uploading/analyzing CVs (PDF only), and scoring match.
  - Business logic for LLM interactions lives in `agents.py` using `pydantic-ai` Agents with strict Pydantic models from `models.py` and prompts in `prompts.py`.
  - `cache_utils.py` provides a per-process TTL LRU cache to reduce repeated LLM calls.
  - Reverse proxy/SSL termination via Caddy (`Caddyfile`) in front of the app service (`docker-compose.yml`).

- Data flow
  - Client -> Caddy (TLS) -> FastAPI endpoint.
  - For /analyze-cv: file is validated (PDF+size), saved to `uploaded_cvs/`, read for hashing, then analyzed by the CV agent.
  - For scoring: CV analysis JSON + job requirements JSON passed to the LLM scoring agent (`agents.score_cv_match`); responses strictly validated by Pydantic models.

- Security & ops
  - CORS controlled by `ALLOWED_ORIGINS` env; default is dev-friendly; must be restricted in prod.
  - HTTPS via Caddy with automatic certs for `{$DOMAIN}`; HTTP redirects to HTTPS.
  - Max upload size enforced by `MAX_UPLOAD_MB` with 413 on exceed.
  - Non-root container user; writable `uploaded_cvs/` volume.
  - Health endpoint `/healthz` for liveness checks.
  - Gunicorn managed with env-driven workers/threads/timeouts.

- Keys and auth
  - Preferred: per-request `X-OpenAI-Key` header set by the Chrome extension.
  - Fallback: server `OPENAI_API_KEY` if header missing.
  - Internally, an async lock temporarily sets `OPENAI_API_KEY` during each LLM call to support per-request keys.

- Limitations
  - In-memory cache is per-process; no cross-replica sharing.
  - Large PDFs are rejected by size; extremely long analyses may hit timeouts; tune `GUNICORN_*` and agent timeouts as needed.
