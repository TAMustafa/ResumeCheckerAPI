import logfire
import asyncio
import hashlib
import json
from pathlib import Path
from pydantic import ValidationError
from pydantic_ai import Agent, BinaryContent
from dotenv import load_dotenv

from models import JobRequirements, CVAnalysis, MatchingScore
from prompts import job_requirements_prompt, cv_review_prompt, scoring_prompt
from cache_utils import shared_cache

# Load environment variables
load_dotenv()

# Configure logfire logging
logfire.configure()
logfire.instrument_pydantic_ai()

# --- Agent Definitions ---
# Configure model settings with temperature=0.3 for more focused, deterministic outputs
model_settings = {
    'temperature': 0.1,   # Lower temperature for more focused, less random outputs
    'max_tokens': 2000    # Ensure we have enough tokens for detailed responses
}

# Define agents with their respective models and prompts
job_requirements_agent = Agent(
    'openai:gpt-4o',
    output_type=JobRequirements,
    system_prompt=job_requirements_prompt,
    model_settings=model_settings
)

cv_review_agent = Agent(
    'openai:gpt-4o',
    output_type=CVAnalysis,
    system_prompt=cv_review_prompt,
    model_settings=model_settings
)

scoring_agent = Agent(
    'openai:gpt-4o',
    output_type=MatchingScore,
    system_prompt=scoring_prompt,
    model_settings=model_settings
)

# --- Core Functions ---
async def analyze_job_vacancy(vacancy_text: str) -> JobRequirements:
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
            result = await asyncio.wait_for(
                job_requirements_agent.run(
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

async def analyze_cv(pdf_path: Path) -> CVAnalysis:
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
            result = await asyncio.wait_for(
                cv_review_agent.run([
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

async def score_cv_match(cv_analysis: CVAnalysis, job_requirements: JobRequirements) -> MatchingScore:
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
            result = await asyncio.wait_for(
                scoring_agent.run(
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