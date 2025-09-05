"""
Enhanced scoring engine with weighted scoring based on job requirement priorities.
Implements 2024 best practices for AI resume screening systems.
"""
from typing import Dict, List, Tuple
from dataclasses import dataclass
from enum import Enum

from models import JobRequirements, CVAnalysis, MatchingScore
from skill_matcher import enhanced_taxonomy

class Priority(Enum):
    """Job requirement priority levels."""
    CRITICAL = 1.0      # Must-have requirements
    HIGH = 0.8         # Very important
    MEDIUM = 0.6       # Preferred
    LOW = 0.3          # Nice to have

@dataclass
class WeightingProfile:
    """Defines how different aspects of a job should be weighted."""
    technical_skills_weight: float = 0.30
    soft_skills_weight: float = 0.15
    experience_weight: float = 0.25
    qualifications_weight: float = 0.15
    responsibilities_weight: float = 0.15
    
    def __post_init__(self):
        """Ensure weights sum to 1.0."""
        total = (self.technical_skills_weight + self.soft_skills_weight + 
                self.experience_weight + self.qualifications_weight + 
                self.responsibilities_weight)
        if abs(total - 1.0) > 0.01:
            raise ValueError(f"Weights must sum to 1.0, got {total}")

# Industry-specific weighting profiles
WEIGHTING_PROFILES = {
    "software_engineering": WeightingProfile(
        technical_skills_weight=0.40,
        soft_skills_weight=0.10,
        experience_weight=0.30,
        qualifications_weight=0.10,
        responsibilities_weight=0.10
    ),
    "data_science": WeightingProfile(
        technical_skills_weight=0.35,
        soft_skills_weight=0.15,
        experience_weight=0.25,
        qualifications_weight=0.15,
        responsibilities_weight=0.10
    ),
    "product_management": WeightingProfile(
        technical_skills_weight=0.15,
        soft_skills_weight=0.30,
        experience_weight=0.25,
        qualifications_weight=0.10,
        responsibilities_weight=0.20
    ),
    "sales": WeightingProfile(
        technical_skills_weight=0.05,
        soft_skills_weight=0.40,
        experience_weight=0.30,
        qualifications_weight=0.10,
        responsibilities_weight=0.15
    ),
    "marketing": WeightingProfile(
        technical_skills_weight=0.20,
        soft_skills_weight=0.25,
        experience_weight=0.25,
        qualifications_weight=0.10,
        responsibilities_weight=0.20
    ),
    "default": WeightingProfile()  # Balanced weights
}

class EnhancedScoringEngine:
    """
    Enhanced scoring engine that implements weighted scoring based on
    job requirements priority and industry-specific profiles.
    """
    
    def __init__(self):
        self.taxonomy = enhanced_taxonomy
    
    def infer_industry(self, job_requirements: JobRequirements) -> str:
        """
        Infer industry from job requirements using keyword analysis.
        
        Args:
            job_requirements: Job requirements to analyze
            
        Returns:
            Industry identifier for weighting profile selection
        """
        # Combine text fields for analysis
        text_fields = []
        if job_requirements.responsibilities:
            text_fields.extend(job_requirements.responsibilities)
        if job_requirements.required_skills.technical:
            text_fields.extend(job_requirements.required_skills.technical)
        if job_requirements.seniority_level:
            text_fields.append(job_requirements.seniority_level)
        
        combined_text = " ".join(text_fields).lower()
        
        # Industry keyword patterns
        industry_patterns = {
            "software_engineering": [
                "software", "developer", "programming", "engineer", "backend", "frontend",
                "fullstack", "devops", "api", "microservices", "architect"
            ],
            "data_science": [
                "data scientist", "machine learning", "ml", "ai", "analytics", 
                "statistics", "modeling", "data engineer", "big data", "etl"
            ],
            "product_management": [
                "product manager", "product owner", "roadmap", "stakeholder",
                "agile", "scrum", "user stories", "requirements", "strategy"
            ],
            "sales": [
                "sales", "account manager", "business development", "revenue",
                "quota", "pipeline", "crm", "client", "prospect"
            ],
            "marketing": [
                "marketing", "campaign", "brand", "content", "social media",
                "seo", "sem", "growth", "acquisition", "engagement"
            ]
        }
        
        # Score each industry
        industry_scores = {}
        for industry, keywords in industry_patterns.items():
            score = sum(1 for keyword in keywords if keyword in combined_text)
            if score > 0:
                industry_scores[industry] = score
        
        # Return industry with highest score, or default
        if industry_scores:
            return max(industry_scores, key=industry_scores.get)
        return "default"
    
    def calculate_technical_skills_score(
        self, 
        cv_skills: List[str], 
        job_skills: List[str],
        job_confidences: Dict[str, float]
    ) -> Tuple[int, str, List[str]]:
        """
        Calculate technical skills match score with enhanced matching.
        
        Returns:
            Tuple of (score, explanation, matched_skills)
        """
        if not job_skills:
            return 85, "No specific technical skills required", []
        
        # Validate and match CV skills
        cv_matches, _ = self.taxonomy.validate_and_match_skills(cv_skills)
        cv_normalized = {match.normalized for match in cv_matches}
        
        # Validate and match job skills
        job_matches, _ = self.taxonomy.validate_and_match_skills(job_skills)
        job_normalized = {match.normalized for match in job_matches}
        
        if not job_normalized:
            return 75, "Unable to parse required technical skills", []
        
        # Calculate matches
        direct_matches = cv_normalized.intersection(job_normalized)
        match_count = len(direct_matches)
        total_required = len(job_normalized)
        
        # Check for related skills in same categories
        related_bonus = 0
        for job_skill in job_normalized:
            if job_skill not in direct_matches:
                related = set(self.taxonomy.get_related_skills(job_skill))
                if cv_normalized.intersection(related):
                    related_bonus += 0.3  # 30% credit for related skills
        
        # Calculate base score
        base_score = (match_count + related_bonus) / total_required
        
        # Apply confidence weighting
        confidence = job_confidences.get("required_skills", 0.8)
        weighted_score = base_score * confidence + (1 - confidence) * 0.7  # Neutral score for low confidence
        
        # Convert to 0-100 scale
        final_score = min(100, int(weighted_score * 100))
        
        explanation = f"{match_count}/{total_required} required skills matched"
        if related_bonus > 0:
            explanation += f" (+{related_bonus:.1f} related skills bonus)"
        
        return final_score, explanation, list(direct_matches)
    
    def calculate_experience_score(
        self,
        cv_analysis: CVAnalysis,
        job_requirements: JobRequirements,
        job_confidences: Dict[str, float]
    ) -> Tuple[int, str]:
        """Calculate experience match score."""
        if not job_requirements.experience.minimum_years:
            return 80, "No specific experience requirement"
        
        # Extract years from CV summary (simple heuristic)
        experience_text = cv_analysis.key_information.experience_summary.lower()
        
        # Look for year patterns
        import re
        year_patterns = [
            r'(\d+)\+?\s*years?\s*(?:of\s*)?experience',
            r'(\d+)\+?\s*years?\s*in',
            r'over\s*(\d+)\s*years?',
            r'more\s*than\s*(\d+)\s*years?'
        ]
        
        cv_years = 0
        for pattern in year_patterns:
            matches = re.findall(pattern, experience_text)
            if matches:
                cv_years = max(cv_years, max(int(year) for year in matches))
        
        required_years = job_requirements.experience.minimum_years
        
        if cv_years >= required_years:
            score = min(100, 80 + (cv_years - required_years) * 5)  # Bonus for extra experience
            explanation = f"{cv_years} years experience (≥{required_years} required)"
        elif cv_years >= required_years * 0.8:  # Within 20% of requirement
            score = 70 + int((cv_years / required_years) * 10)
            explanation = f"{cv_years} years experience (close to {required_years} required)"
        else:
            score = max(30, int((cv_years / required_years) * 60))
            explanation = f"{cv_years} years experience (<{required_years} required)"
        
        # Apply confidence weighting
        confidence = job_confidences.get("experience", 0.8)
        weighted_score = score * confidence + (1 - confidence) * 70
        
        return int(weighted_score), explanation
    
    def calculate_soft_skills_score(
        self,
        cv_soft_skills: List[str],
        job_soft_skills: List[str],
        job_confidences: Dict[str, float]
    ) -> Tuple[int, str]:
        """Calculate soft skills match score."""
        if not job_soft_skills:
            return 75, "No specific soft skills specified"
        
        # Normalize soft skills for comparison
        cv_normalized = {skill.lower().strip() for skill in cv_soft_skills}
        job_normalized = {skill.lower().strip() for skill in job_soft_skills}
        
        # Direct matches
        matches = cv_normalized.intersection(job_normalized)
        match_ratio = len(matches) / len(job_normalized) if job_normalized else 0
        
        # Soft skills are often described differently, so be more lenient
        base_score = 60 + (match_ratio * 40)  # Base 60, up to 100
        
        confidence = job_confidences.get("required_skills", 0.7)
        weighted_score = base_score * confidence + (1 - confidence) * 70
        
        explanation = f"{len(matches)}/{len(job_normalized)} soft skills matched"
        
        return int(weighted_score), explanation
    
    def calculate_weighted_score(
        self,
        cv_analysis: CVAnalysis,
        job_requirements: JobRequirements
    ) -> MatchingScore:
        """
        Calculate comprehensive weighted matching score.
        
        Args:
            cv_analysis: Analyzed CV data
            job_requirements: Job requirements
            
        Returns:
            Enhanced MatchingScore with weighted calculations
        """
        # Infer industry and get appropriate weighting profile
        industry = self.infer_industry(job_requirements)
        profile = WEIGHTING_PROFILES.get(industry, WEIGHTING_PROFILES["default"])
        
        # Provide safe default confidences if the field is absent on JobRequirements
        job_confidences = getattr(job_requirements, 'confidences', {}) or {}

        # Calculate component scores
        tech_score, tech_exp, matched_tech = self.calculate_technical_skills_score(
            cv_analysis.key_information.technical_skills,
            job_requirements.required_skills.technical,
            job_confidences
        )
        
        soft_score, soft_exp = self.calculate_soft_skills_score(
            cv_analysis.key_information.soft_skills,
            job_requirements.required_skills.soft,
            job_confidences
        )
        
        exp_score, exp_exp = self.calculate_experience_score(
            cv_analysis, job_requirements, job_confidences
        )
        
        # Simple scoring for qualifications and responsibilities
        qual_score = 75  # Default - could be enhanced further
        qual_exp = "Qualifications assessment needs enhancement"
        
        resp_score = 70  # Default - could be enhanced further  
        resp_exp = "Responsibilities matching needs enhancement"
        
        # Calculate weighted overall score
        overall_score = int(
            tech_score * profile.technical_skills_weight +
            soft_score * profile.soft_skills_weight +
            exp_score * profile.experience_weight +
            qual_score * profile.qualifications_weight +
            resp_score * profile.responsibilities_weight
        )
        
        # Build explanation
        overall_exp = f"Weighted score using {industry} profile. Tech: {tech_score} ({profile.technical_skills_weight:.0%}), Experience: {exp_score} ({profile.experience_weight:.0%})"

        # Compute matched entities for strengths first
        # Soft skills
        cv_soft_norm = {s.lower().strip() for s in cv_analysis.key_information.soft_skills}
        job_soft_norm = {s.lower().strip() for s in job_requirements.required_skills.soft}
        matched_soft = sorted({s for s in cv_soft_norm.intersection(job_soft_norm) if s})
        matched_soft_display = [s.title() for s in matched_soft]

        # Qualifications (with alias normalization)
        def _norm_cert(s: str) -> str:
            if not s:
                return ""
            x = s.lower().strip()
            aliases = {
                "aws ccp": "aws cloud practitioner",
                "aws cloud practitioner": "aws cloud practitioner",
                "aws certified cloud practitioner": "aws cloud practitioner",
                "pmp": "project management professional",
                "project management professional": "project management professional",
                "prince2": "prince2 practitioner",
                "prince2 practitioner": "prince2 practitioner",
                "scrum master": "scrum master",
                "psm": "scrum master",
                "psm i": "scrum master",
                "az-900": "microsoft azure fundamentals",
                "azure fundamentals": "microsoft azure fundamentals",
                "microsoft azure fundamentals": "microsoft azure fundamentals",
            }
            return aliases.get(x, x)

        cv_quals_norm = { _norm_cert(q) for q in cv_analysis.key_information.certifications }
        job_quals_norm = { _norm_cert(q) for q in job_requirements.qualifications }
        matched_qualifications = sorted({q for q in cv_quals_norm.intersection(job_quals_norm) if q})
        matched_qualifications_display = [q.title() for q in matched_qualifications]

        # Languages
        matched_languages_list = sorted(
            {l.strip().lower() for l in cv_analysis.key_information.languages}
            .intersection({l.strip().lower() for l in job_requirements.languages})
        )

        # Responsibilities
        cv_resps_norm = {r.strip().lower() for r in cv_analysis.key_information.responsibilities}
        job_resps_norm = {r.strip().lower() for r in job_requirements.responsibilities}
        matched_responsibilities = sorted({r for r in cv_resps_norm.intersection(job_resps_norm) if r})

        # Determine gaps
        gaps: list[str] = []
        if tech_score < 60:
            gaps.append("Technical skills gap")
        if exp_score < 60:
            gaps.append("Experience below requirements")
        if soft_score < 60:
            gaps.append("Soft skills development needed")
        # Preserve order and uniqueness
        strengths_items: list[str] = []
        def _extend_unique(seq):
            for x in seq:
                if x and x not in strengths_items:
                    strengths_items.append(x)
        _extend_unique(matched_tech)
        _extend_unique(matched_soft_display)
        _extend_unique(matched_qualifications_display)
        _extend_unique(matched_languages_list)
        _extend_unique(matched_responsibilities)
        strengths = strengths_items[:10]
        
        # Missing requirements are no longer returned; keep per-category deltas only for suggestions

        # Missing by category
        missing_tech_skills = sorted(set(job_requirements.required_skills.technical) - set(matched_tech))
        missing_soft_skills = sorted({s for s in job_requirements.required_skills.soft if s.lower().strip() not in job_soft_norm})
        missing_qualifications = sorted(list(job_quals_norm - cv_quals_norm))
        missing_languages = sorted(
            {l.strip().lower() for l in job_requirements.languages} - {l.strip().lower() for l in cv_analysis.key_information.languages}
        )
        missing_responsibilities = sorted(list(job_resps_norm - cv_resps_norm))

        # Compose concise improvement suggestions based on key misses
        top_missing: list[str] = []
        top_missing.extend(missing_tech_skills[:3])
        top_missing.extend([s.title() for s in missing_soft_skills[:2]])
        if exp_score < 70 and job_requirements.experience.minimum_years:
            top_missing.append(f"{job_requirements.experience.minimum_years}+ years experience")
        top_missing.extend([q.title() for q in missing_qualifications[:2]])
        top_missing.extend([l.title() for l in missing_languages[:2]])
        top_missing.extend([r for r in missing_responsibilities[:2]])

        # Prepare matched lists (no longer returned; used for strengths composition only)

        return MatchingScore(
            overall_match_score=overall_score,
            overall_explanation=overall_exp,
            technical_skills_score=tech_score,
            technical_skills_explanation=tech_exp,
            soft_skills_score=soft_score,
            soft_skills_explanation=soft_exp,
            experience_score=exp_score,
            experience_explanation=exp_exp,
            qualifications_score=qual_score,
            qualifications_explanation=qual_exp,
            key_responsibilities_score=resp_score,
            key_responsibilities_explanation=resp_exp,
            improvement_suggestions=[f"Consider developing skills in: {', '.join(top_missing[:3])}" if top_missing else "Strong overall profile"],
            strengths=strengths,
            gaps=gaps
        )

# Global instance
enhanced_scoring = EnhancedScoringEngine()