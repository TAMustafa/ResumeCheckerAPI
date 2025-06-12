import logfire
from pathlib import Path
from pydantic import ValidationError
from pydantic_ai import Agent, BinaryContent
from dotenv import load_dotenv

from models import JobRequirements, CVAnalysis, MatchingScore
from prompts import *

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
    'openai:gpt-4o-mini',
    output_type=JobRequirements,
    system_prompt=job_requirements_prompt,
    model_settings=model_settings
)

cv_review_agent = Agent(
    'openai:gpt-4o-mini',
    output_type=CVAnalysis,
    system_prompt=cv_review_prompt,
    model_settings=model_settings
)

scoring_agent = Agent(
    'openai:gpt-4o-mini',
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
        result = await job_requirements_agent.run(
            f"Extract the job requirements and any other relevant information from the vacancy text: {vacancy_text}"
        )
        return result.output
    except ValidationError as e:
        logfire.error(f"Validation error in analyze_job_vacancy: {e}")
        raise

async def analyze_cv(pdf_path: Path) -> CVAnalysis:
    """
    Analyze CV and extract key information
    """
    try:
        result = await cv_review_agent.run([
            f"Analyze the CV and provide a detailed breakdown of strengths, weaknesses, and improvement recommendations.",
            BinaryContent(data=pdf_path.read_bytes(), media_type='application/pdf'),
        ])
        return result.output
    except ValidationError as e:
        logfire.error(f"Validation error in analyze_cv: {e}")
        raise

async def score_cv_match(cv_analysis: CVAnalysis, job_requirements: JobRequirements) -> MatchingScore:
    """
    Score how well the CV matches the job requirements
    """
    try:
        result = await scoring_agent.run(
            f"Provide a score between 0 and 100 based on how well the CV matches the job requirements: {cv_analysis} {job_requirements}"
        )
        return result.output
    except ValidationError as e:
        logfire.error(f"Validation error in score_cv_match: {e}")
        raise