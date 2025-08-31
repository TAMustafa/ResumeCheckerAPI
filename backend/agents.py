import logfire
import asyncio
import hashlib
import json
from pathlib import Path
from pydantic import ValidationError
from pydantic_ai import Agent, BinaryContent
import os

from models import JobRequirements, CVAnalysis, MatchingScore
from prompts import job_requirements_prompt, cv_review_prompt, scoring_prompt
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
# Configure model settings with temperature=0.1 for focused, less random outputs
model_settings = {
    'temperature': 0.1,
    'max_tokens': 2000,
}

# Small in-process cache of Agent instances by (task, provider, model)
_AGENT_CACHE: dict[tuple[str, str, str], Agent] = {}

def _model_string(provider: str, model: str | None) -> str:
    p = (provider or 'openai').lower()
    if not model or not model.strip():
        # sensible defaults
        return 'openai:gpt-4o'
    return f"{p}:{model.strip()}"

def _get_agent(task: str, provider: str | None, model: str | None):
    key = (task, (provider or 'openai').lower(), (model or '').strip() or 'gpt-4o')
    if key in _AGENT_CACHE:
        return _AGENT_CACHE[key]
    model_id = _model_string(key[1], key[2])
    if task == 'job':
        agent = Agent(model_id, output_type=JobRequirements, system_prompt=job_requirements_prompt, model_settings=model_settings)
    elif task == 'cv':
        agent = Agent(model_id, output_type=CVAnalysis, system_prompt=cv_review_prompt, model_settings=model_settings)
    elif task == 'score':
        agent = Agent(model_id, output_type=MatchingScore, system_prompt=scoring_prompt, model_settings=model_settings)
    else:
        raise ValueError(f"Unknown task '{task}'")
    _AGENT_CACHE[key] = agent
    return agent

# --- Core Functions ---
async def analyze_job_vacancy(vacancy_text: str, api_key: str | None = None, provider: str | None = None, model: str | None = None) -> JobRequirements:
    """
    Extract requirements from job vacancy text
    """
    try:
        # Cache key based on vacancy text hash
        key = "vacancy:v1:" + hashlib.sha256(vacancy_text.encode("utf-8")).hexdigest()
        cached = await shared_cache.get(key)
        if cached is not None:
            return JobRequirements(**cached)

        async def _compute():
            async with _ApiKeyContext(api_key):
                agent = _get_agent('job', provider, model)
                result = await asyncio.wait_for(
                    agent.run(
                        f"Extract the job requirements and any other key information from the vacancy text: {vacancy_text}"
                    ),
                    timeout=60,
                )
            # store a plain dict in cache
            await shared_cache.set(key, result.output.model_dump())
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

async def analyze_cv(pdf_path: Path, api_key: str | None = None, provider: str | None = None, model: str | None = None) -> CVAnalysis:
    """
    Analyze CV and extract key information
    """
    try:
        data = pdf_path.read_bytes()
        key = "cv:v1:" + hashlib.sha256(data).hexdigest()
        cached = await shared_cache.get(key)
        if cached is not None:
            return CVAnalysis(**cached)

        async def _compute():
            async with _ApiKeyContext(api_key):
                agent = _get_agent('cv', provider, model)
                result = await asyncio.wait_for(
                    agent.run([
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
        key = "score:v1:" + hashlib.sha256(payload.encode("utf-8")).hexdigest()
        cached = await shared_cache.get(key)
        if cached is not None:
            return MatchingScore(**cached)

        async def _compute():
            async with _ApiKeyContext(api_key):
                agent = _get_agent('score', provider, model)
                result = await asyncio.wait_for(
                    agent.run(
                        "Provide a score between 0 and 100 based on how well the CV matches the job requirements based on common skills and requirements.\n\n"
                        f"CV Analysis JSON: {json.dumps(cv_analysis.model_dump(), sort_keys=True)}\n\n"
                        f"Job Requirements JSON: {json.dumps(job_requirements.model_dump(), sort_keys=True)}"
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