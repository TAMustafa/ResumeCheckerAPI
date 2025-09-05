import io
import os
from typing import Iterator

import pytest
from fastapi.testclient import TestClient

# Import the app and modules to mock
from app import app
import agents
from models import (
    JobRequirements,
    SkillSet,
    ExperienceDetails,
    CVAnalysis,
    CandidateAssessment,
    CVKeyInfo,
    StrategicRecommendations,
    MatchingScore,
)


@pytest.fixture(autouse=True)
def ensure_api_key_not_required() -> Iterator[None]:
    """Ensure tests don't fail on missing X-OpenAI-Key by default.
    We still send the header in calls, but this makes tests resilient if env flips.
    """
    # Prefer to keep default behavior, but allow header to satisfy requirement.
    # Nothing to do here; kept for potential future env toggles.
    yield


@pytest.fixture()
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture()
def mock_agents(monkeypatch: pytest.MonkeyPatch):
    """Mock LLM agent functions to deterministic outputs."""
    def fake_analyze_job_vacancy(vacancy_text: str, api_key: str | None, provider: str, model: str | None):
        return JobRequirements(
            required_skills=SkillSet(technical=["Python"], soft=["Communication"]),
            experience=ExperienceDetails(minimum_years=2, industry="Software"),
            qualifications=["BSc"],
            responsibilities=["Build APIs"],
            languages=["English"],
            seniority_level="mid",
        )

    def fake_analyze_cv(file_path, api_key: str | None, provider: str, model: str | None):
        return CVAnalysis(
            candidate_suitability=CandidateAssessment(
                overall_fit_score=7,
                justification="Solid",
                strengths=["APIs"],
                gaps=["Kubernetes"],
            ),
            key_information=CVKeyInfo(
                experience_summary="3 years backend",
                technical_skills=["Python"],
                soft_skills=["Communication"],
                certifications=["AWS"],
                languages=["English"],
                responsibilities=["Built services"],
            ),
            recommendations=StrategicRecommendations(
                tailoring=["Emphasize Python"],
                interview_focus=["Scaling"],
                career_development=["Kubernetes"],
            ),
        )

    def fake_score_cv_match(cv_analysis: CVAnalysis, job_reqs: JobRequirements, api_key: str | None, provider: str, model: str | None):
        return MatchingScore(
            overall_match_score=75,
            overall_explanation="Good",
            technical_skills_score=80,
            technical_skills_explanation="Strong Python",
            soft_skills_score=70,
            soft_skills_explanation="Good communication",
            experience_score=65,
            experience_explanation="Enough years",
            qualifications_score=60,
            qualifications_explanation="BSc ok",
            key_responsibilities_score=55,
            key_responsibilities_explanation="Some overlap",
            missing_requirements=["Kubernetes"],
            improvement_suggestions=["Learn Kubernetes"],
            matched_skills=["Python"],
            matched_qualifications=["BSc"],
            matched_languages=["English"],
            strengths=["APIs"],
            gaps=["Kubernetes"],
        )

    monkeypatch.setattr(agents, "analyze_job_vacancy", fake_analyze_job_vacancy)
    monkeypatch.setattr(agents, "analyze_cv", fake_analyze_cv)
    # NOTE: score_cv_match is now deterministic via scoring_engine; do not monkeypatch.


def test_healthz(client: TestClient):
    r = client.get("/healthz")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_analyze_job_vacancy(client: TestClient, mock_agents):
    r = client.post(
        "/analyze-job-vacancy",
        json={"vacancy_text": "We need Python dev"},
        headers={"X-OpenAI-Key": "test"},
    )
    assert r.status_code == 200, r.text
    data = r.json()
    # Validate key fields from mocked response
    assert data["qualifications"] == ["BSc"]
    assert data["languages"] == ["English"]
    assert data["experience"]["minimum_years"] == 2


def test_analyze_cv_pdf_upload(client: TestClient, mock_agents):
    # Minimal valid PDF bytes
    pdf_bytes = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF\n"
    files = {"file": ("cv.pdf", io.BytesIO(pdf_bytes), "application/pdf")}
    r = client.post(
        "/analyze-cv",
        files=files,
        headers={"X-OpenAI-Key": "test"},
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["candidate_suitability"]["overall_fit_score"] == 7
    assert "recommendations" in data


def test_score_cv_match(client: TestClient, mock_agents):
    # Prepare payloads using shapes expected by the API
    cv_analysis = {
        "candidate_suitability": {
            "overall_fit_score": 7,
            "justification": "Solid",
            "strengths": ["APIs"],
            "gaps": ["Kubernetes"],
        },
        "key_information": {
            "experience_summary": "3 years backend",
            "technical_skills": ["Python"],
            "soft_skills": ["Communication"],
            "certifications": ["AWS"],
            "languages": ["English"],
            "responsibilities": ["Built services"],
        },
        "recommendations": {
            "tailoring": ["Emphasize Python"],
            "interview_focus": ["Scaling"],
            "career_development": ["Kubernetes"],
        },
    }
    job_requirements = {
        "required_skills": {"technical": ["Python"], "soft": ["Communication"]},
        "experience": {"minimum_years": 2, "industry": "Software"},
        "qualifications": ["BSc"],
        "responsibilities": ["Build APIs"],
        "languages": ["English"],
        "seniority_level": "mid",
    }
    r = client.post(
        "/score-cv-match",
        json={"cv_analysis": cv_analysis, "job_requirements": job_requirements},
        headers={"X-OpenAI-Key": "test"},
    )
    assert r.status_code == 200, r.text
    data = r.json()
    # Deterministic scoring should return required keys
    for key in [
        "overall_match_score",
        "overall_explanation",
        "technical_skills_score",
        "experience_score",
        "qualifications_score",
        "key_responsibilities_score",
        "improvement_suggestions",
    ]:
        assert key in data
    # No explicit per-category matches are required in the API response anymore

    # UI no longer depends on Matches & Misses; do not assert per-category comparison fields
