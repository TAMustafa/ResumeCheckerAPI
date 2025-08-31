# Gotchas

- CORS is controlled via `ALLOWED_ORIGINS` in `app.py`. Include your production API domain and Chrome extension origin, otherwise requests will fail.
- Max upload size is enforced via `MAX_UPLOAD_MB` (default 10MB). Requests exceeding the limit return 413. Clients should show a clear error.
- `analyze_cv()` reads the PDF bytes to hash; very large PDFs are blocked by the upload limit, but consider user guidance for typical sizes (<5MB recommended).
- Cache is per-process in-memory. It does not share across replicas and will clear on process restart. TTL default 20 minutes.
- LLM calls have timeouts (60–90s). Tune with care; too high may tie up workers.
- Per-user API key is applied by temporarily setting `OPENAI_API_KEY` under a global async lock. This serializes key swaps and can limit throughput if many distinct keys are used concurrently.
- `uploaded_cvs/` must be on a persistent volume in production; consider quota and retention policies.
- Caddy uses `{$DOMAIN}` for automatic HTTPS; ensure DNS A/AAAA records point to the server and port 80/443 are open.
- Gunicorn settings are env-driven; tune `GUNICORN_WORKERS/THREADS/TIMEOUT` based on CPU and expected model latencies.

## API Keys & Providers
- When `REQUIRE_USER_API_KEY=true`, all LLM endpoints require `X-OpenAI-Key` and return 401 if missing.
- The extension stores keys per provider but the backend currently supports only `openai`. If `X-LLM-Provider` is not `openai`, endpoints return 400 (by design) until DeepSeek/Anthropic are implemented.
- Health endpoint `/healthz` never requires a key.
