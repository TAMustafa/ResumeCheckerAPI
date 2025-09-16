import logfire
import asyncio
import hashlib
import json
from pathlib import Path
from pydantic import ValidationError
from pydantic_ai import Agent, BinaryContent
import os
from typing import Any

from models import JobRequirements, CVAnalysis, MatchingScore
from prompts import job_requirements_prompt, cv_review_prompt, scoring_prompt
from enhanced_prompts import enhanced_prompts
from cache_utils import shared_cache

# Configure logfire logging
logfire.configure()
logfire.instrument_pydantic_ai()

# Concurrency-safe API key swap lock
_key_lock = asyncio.Lock()

class _ApiKeyContext:
    """
    Async context manager to temporarily set OPENAI_API_KEY process env
    for the duration of a single LLM call. Uses a global asyncio.Lock to
    avoid races across concurrent requests.
    """
    def __init__(self, api_key: str | None):
        self.api_key = api_key
        self._old = None

    async def __aenter__(self):
        if not self.api_key:
            return
        await _key_lock.acquire()
        self._old = os.environ.get("OPENAI_API_KEY")
        os.environ["OPENAI_API_KEY"] = self.api_key

    async def __aexit__(self, exc_type, exc, tb):
        try:
            if self.api_key is not None:
                if self._old is None:
                    os.environ.pop("OPENAI_API_KEY", None)
                else:
                    os.environ["OPENAI_API_KEY"] = self._old
        finally:
            if _key_lock.locked():
                _key_lock.release()

# --- Agent Definitions ---
"""Agent and LLM configuration.

Notes:
- We introduce an AGENT_VERSION to safely invalidate caches when prompts/settings change.
- We use task-specific model settings to better fit token needs per task.
"""

# Bump this when changing prompts/model settings to invalidate caches safely
AGENT_VERSION = "v4"

# Base/default model settings used for all tasks
_DEFAULT_MODEL_SETTINGS = {
    'temperature': 0.1,
    'max_tokens': 4000,
}

# Small in-process cache of Agent instances, keyed with versioning to avoid collisions
_AGENT_CACHE: dict[tuple[str, str, str, str], Agent] = {}

def _model_string(provider: str, model: str | None) -> str:
    p = (provider or 'openai').lower()
    if not model or not model.strip():
        # sensible defaults
        return 'openai:gpt-4o'
    return f"{p}:{model.strip()}"

def _get_agent(task: str, provider: str | None, model: str | None):
    provider_norm = (provider or 'openai').lower()
    model_norm = (model or '').strip() or 'gpt-4o'
    settings = _DEFAULT_MODEL_SETTINGS
    # Include version in cache key to avoid stale agents when prompts/settings change
    key = (task, provider_norm, model_norm, AGENT_VERSION)
    if key in _AGENT_CACHE:
        return _AGENT_CACHE[key]
    model_id = _model_string(provider_norm, model_norm)
    # NOTE: If enabling enhanced prompts, select per-task prompt here based on env/inputs
    if task == 'job':
        agent = Agent(model_id, output_type=JobRequirements, system_prompt=job_requirements_prompt, model_settings=settings)
    elif task == 'cv':
        agent = Agent(model_id, output_type=CVAnalysis, system_prompt=cv_review_prompt, model_settings=settings)
    elif task == 'score':
        agent = Agent(model_id, output_type=MatchingScore, system_prompt=scoring_prompt, model_settings=settings)
    else:
        raise ValueError(f"Unknown task '{task}'")
    _AGENT_CACHE[key] = agent
    return agent

async def _run_with_retries(run_coro_factory, timeout: float, *, attempts: int = 3) -> Any:
    """Run an async LLM call with bounded retries and exponential backoff.

    Args:
        run_coro_factory: zero-arg callable returning the coroutine to await (fresh per attempt)
        timeout: per-attempt timeout in seconds
        attempts: total number of attempts
    """
    backoff = 0.5
    last_exc: Exception | None = None
    for i in range(1, attempts + 1):
        try:
            return await asyncio.wait_for(run_coro_factory(), timeout=timeout)
        except Exception as e:  # broad: includes timeouts/transient API errors
            last_exc = e
            if i >= attempts:
                break
            # jittered exponential backoff
            await asyncio.sleep(backoff + (0.1 * i))
            backoff *= 2
    # Exhausted attempts
    assert last_exc is not None
    raise last_exc

# --- Core Functions ---
async def analyze_job_vacancy(vacancy_text: str, api_key: str | None = None, provider: str | None = None, model: str | None = None) -> JobRequirements:
    """
    Extract requirements from job vacancy text with performance monitoring
    """
    import time
    start_time = time.time()
    
    try:
        # Cache key includes inputs + model/provider + version for correctness across config changes
        base = hashlib.sha256(vacancy_text.encode("utf-8")).hexdigest()
        provider_norm = (provider or 'openai').lower()
        model_norm = (model or '').strip() or 'gpt-4o'
        enh_flag = "enh1"  # always use enhanced prompts
        key = f"vacancy:{AGENT_VERSION}:{enh_flag}:{provider_norm}:{model_norm}:{base}"
        cached = await shared_cache.get(key)
        if cached is not None:
            duration = time.time() - start_time
            logfire.info("analyze_job_vacancy cache hit", extra={
                "key": key, "provider": provider_norm, "model": model_norm, 
                "duration_ms": round(duration * 1000, 2)
            })
            return JobRequirements(**cached)

        async def _compute():
            async with _ApiKeyContext(api_key):
                model_id = _model_string((provider or 'openai').lower(), (model or '').strip() or 'gpt-4o')
                # Always use enhanced system prompt for job analysis
                system_prompt = enhanced_prompts.get_job_analysis_prompt(vacancy_text)
                settings = _DEFAULT_MODEL_SETTINGS
                agent = Agent(model_id, output_type=JobRequirements, system_prompt=system_prompt, model_settings=settings)
                logfire.info("analyze_job_vacancy calling LLM", extra={"model_id": model_id, "task": "job"})
                result = await _run_with_retries(
                    lambda: agent.run(
                        f"Extract the job requirements and any other key information from the vacancy text: {vacancy_text}"
                    ),
                    timeout=60,
                )
            # store a plain dict in cache
            await shared_cache.set(key, result.output.model_dump())
            duration = time.time() - start_time
            logfire.info("analyze_job_vacancy completed", extra={
                "provider": provider_norm, "model": model_norm,
                "duration_ms": round(duration * 1000, 2),
                "text_length": len(vacancy_text)
            })
            return result.output

        return await _compute()
    except ValidationError as e:
        logfire.error(f"Validation error in analyze_job_vacancy: {e}")
        if hasattr(e, 'json'):
            logfire.error(f"Raw LLM output: {getattr(e, 'json', lambda: None)()}")
        raise
    except Exception as e:
        logfire.error(f"Unexpected error in analyze_job_vacancy: {e}")
        raise

async def analyze_cv(pdf_path: Path, api_key: str | None = None, provider: str | None = None, model: str | None = None, job_context: str | None = None) -> CVAnalysis:
    """
    Analyze CV and extract key information
    """
    try:
        data = pdf_path.read_bytes()
        provider_norm = (provider or 'openai').lower()
        model_norm = (model or '').strip() or 'gpt-4o'
        # Include job context in cache key for context-aware analysis
        context_hash = hashlib.sha256((job_context or "").encode("utf-8")).hexdigest()[:8]
        key = "cv:{}:{}:{}:{}:".format(
            AGENT_VERSION,
            provider_norm,
            model_norm,
            context_hash
        ) + hashlib.sha256(data).hexdigest()
        cached = await shared_cache.get(key)
        if cached is not None:
            logfire.info("analyze_cv cache hit", extra={"key": key, "provider": provider_norm, "model": model_norm})
            return CVAnalysis(**cached)

        async def _compute():
            async with _ApiKeyContext(api_key):
                model_id = _model_string((provider or 'openai').lower(), (model or '').strip() or 'gpt-4o')
                # Always use enhanced CV analysis prompt (with optional job_context)
                system_prompt = enhanced_prompts.get_cv_analysis_prompt(job_context)
                settings = _DEFAULT_MODEL_SETTINGS
                agent = Agent(model_id, output_type=CVAnalysis, system_prompt=system_prompt, model_settings=settings)
                logfire.info("analyze_cv calling LLM", extra={"model_id": model_id, "task": "cv"})
                result = await _run_with_retries(
                    lambda: agent.run([
                        "Analyze the CV and provide a bulletpoint summary of strengths, weaknesses, and improvement recommendations.",
                        BinaryContent(data=data, media_type='application/pdf'),
                    ]),
                    timeout=90,
                )
            await shared_cache.set(key, result.output.model_dump())
            return result.output

        return await _compute()
    except ValidationError as e:
        logfire.error(f"Validation error in analyze_cv: {e}")
        if hasattr(e, 'json'):
            logfire.error(f"Raw LLM output: {getattr(e, 'json', lambda: None)()}")
        raise
    except Exception as e:
        logfire.error(f"Unexpected error in analyze_cv: {e}")
        raise

async def score_cv_match(cv_analysis: CVAnalysis, job_requirements: JobRequirements, api_key: str | None = None, provider: str | None = None, model: str | None = None) -> MatchingScore:
    """
    Score how well the CV matches the job requirements
    """
    try:
        payload = json.dumps(
            {
                "cv": cv_analysis.model_dump(),
                "job": job_requirements.model_dump(),
            },
            sort_keys=True,
        )
        provider_norm = (provider or 'openai').lower()
        model_norm = (model or '').strip() or 'gpt-4o'
        key = f"score:{AGENT_VERSION}:{provider_norm}:{model_norm}:" + hashlib.sha256(payload.encode("utf-8")).hexdigest()
        cached = await shared_cache.get(key)
        if cached is not None:
            logfire.info("score_cv_match cache hit", extra={"key": key, "provider": provider_norm, "model": model_norm})
            return MatchingScore(**cached)

        async def _compute():
            async with _ApiKeyContext(api_key):
                model_id = _model_string((provider or 'openai').lower(), (model or '').strip() or 'gpt-4o')
                # Always use enhanced scoring prompt (derive category from job content)
                job_text_for_prompt = json.dumps(job_requirements.model_dump(), sort_keys=True)
                system_prompt = enhanced_prompts.get_scoring_prompt(job_text_for_prompt)
                settings = _DEFAULT_MODEL_SETTINGS
                agent = Agent(model_id, output_type=MatchingScore, system_prompt=system_prompt, model_settings=settings)
                logfire.info("score_cv_match calling LLM", extra={"model_id": model_id, "task": "score"})
                result = await _run_with_retries(
                    lambda: agent.run(
                        (
                            f"CV Analysis JSON: {json.dumps(cv_analysis.model_dump(), sort_keys=True)}\n\n"
                            f"Job Requirements JSON: {json.dumps(job_requirements.model_dump(), sort_keys=True)}"
                        )
                    ),
                    timeout=60,
                )
            await shared_cache.set(key, result.output.model_dump())
            return result.output

        return await _compute()
    except ValidationError as e:
        logfire.error(f"Validation error in score_cv_match: {e}")
        if hasattr(e, 'json'):
            logfire.error(f"Raw LLM output: {getattr(e, 'json', lambda: None)()}")
        raise
    except Exception as e:
        logfire.error(f"Unexpected error in score_cv_match: {e}")
        raise