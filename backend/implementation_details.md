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
