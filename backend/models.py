from pydantic import BaseModel, Field
from typing import List, Optional

class SkillSet(BaseModel):
    technical: List[str] = Field(default_factory=list, description="Technical skills")
    soft: List[str] = Field(default_factory=list, description="Soft skills")

class ExperienceDetails(BaseModel):
    minimum_years: Optional[int] = Field(None, description="Minimum years of experience required")
    industry: Optional[str] = Field(None, description="Relevant industry experience")
    type: Optional[str] = Field(None, description="Type of experience (e.g., full-time, internship)")
    leadership: Optional[str] = Field(None, description="Leadership experience required")

class JobRequirements(BaseModel):
    """Structured job requirements extracted from a job posting."""
    required_skills: SkillSet = Field(default_factory=SkillSet)
    experience: ExperienceDetails = Field(default_factory=ExperienceDetails)
    qualifications: List[str] = Field(default_factory=list, description="Degrees or certifications required")
    responsibilities: List[str] = Field(default_factory=list, description="Key responsibilities")
    languages: List[str] = Field(default_factory=list, description="Languages required")
    seniority_level: Optional[str] = Field(None, description="Seniority level (e.g., junior, senior, lead)")
    model_config = {'strict': True}

class CVKeyInfo(BaseModel):
    experience_summary: str = Field(..., description="Summary of relevant experience")
    technical_skills: List[str] = Field(default_factory=list)
    soft_skills: List[str] = Field(default_factory=list)
    certifications: List[str] = Field(default_factory=list)
    languages: List[str] = Field(default_factory=list)
    responsibilities: List[str] = Field(default_factory=list)

class CandidateAssessment(BaseModel):
    overall_fit_score: int = Field(..., ge=1, le=10)
    justification: str
    strengths: List[str] = Field(default_factory=list)
    gaps: List[str] = Field(default_factory=list)

class StrategicRecommendations(BaseModel):
    tailoring: List[str] = Field(default_factory=list)
    interview_focus: List[str] = Field(default_factory=list)
    career_development: List[str] = Field(default_factory=list)

class CVAnalysis(BaseModel):
    """Detailed CV analysis."""
    candidate_suitability: CandidateAssessment
    key_information: CVKeyInfo
    recommendations: StrategicRecommendations
    model_config = {'strict': True}

class MatchingScore(BaseModel):
    """Detailed matching score between a CV and job requirements."""
    overall_match_score: int = Field(..., ge=0, le=100)
    overall_explanation: str
    technical_skills_score: int = Field(..., ge=0, le=100)
    technical_skills_explanation: str
    soft_skills_score: int = Field(..., ge=0, le=100)
    soft_skills_explanation: str
    experience_score: int = Field(..., ge=0, le=100)
    experience_explanation: str
    qualifications_score: int = Field(..., ge=0, le=100)
    qualifications_explanation: str
    key_responsibilities_score: int = Field(..., ge=0, le=100)
    key_responsibilities_explanation: str
    improvement_suggestions: List[str] = Field(default_factory=list)
    strengths: List[str] = Field(default_factory=list, description="Key strengths identified in the CV")
    gaps: List[str] = Field(default_factory=list, description="Key areas for improvement or missing requirements")
    model_config = {'strict': True}