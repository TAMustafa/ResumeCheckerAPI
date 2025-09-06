"""
Cross-validation and data consistency checks for extracted information.
Follows 2024 best practices for AI system validation and quality assurance.
"""
from typing import List, Dict, Tuple, Optional, Any
import re
from dataclasses import dataclass
from models import JobRequirements, CVAnalysis, MatchingScore

@dataclass
class ValidationIssue:
    """Represents a validation issue found during consistency checks."""
    field: str
    issue_type: str  # 'inconsistency', 'missing', 'invalid', 'suspicious'
    description: str
    severity: str  # 'low', 'medium', 'high', 'critical'
    suggested_fix: Optional[str] = None

@dataclass
class ValidationResult:
    """Result of validation process."""
    is_valid: bool
    confidence_score: float  # Overall confidence after validation
    issues: List[ValidationIssue]
    corrected_data: Optional[Dict[str, Any]] = None

class DataValidator:
    """
    Cross-validation and consistency checking for extracted data.
    Implements heuristic-based validation following industry best practices.
    """
    
    def __init__(self):
        # Experience level indicators
        self.seniority_patterns = {
            'junior': ['junior', 'entry', 'associate', '1-2', '0-2', 'graduate', 'trainee'],
            'mid': ['mid', 'intermediate', '3-5', '2-5', 'experienced', 'regular'],
            'senior': ['senior', 'sr', 'lead', '5+', '6+', '7+', 'principal', 'staff'],
            'principal': ['principal', 'architect', 'director', '10+', 'expert', 'head']
        }
        
        # Common soft skills
        self.common_soft_skills = {
            'communication', 'teamwork', 'leadership', 'problem-solving', 'analytical',
            'creative', 'adaptable', 'organized', 'detail-oriented', 'collaborative',
            'initiative', 'time management', 'critical thinking', 'interpersonal'
        }

    def validate_job_requirements(self, job_req: JobRequirements) -> ValidationResult:
        """
        Validate job requirements for internal consistency and completeness.
        
        Args:
            job_req: JobRequirements object to validate
            
        Returns:
            ValidationResult with issues and confidence assessment
        """
        issues = []
        
        # Check experience vs seniority consistency
        exp_issues = self._check_experience_seniority_consistency(job_req)
        issues.extend(exp_issues)
        
        # Check skill requirements
        skill_issues = self._check_skill_requirements(job_req)
        issues.extend(skill_issues)
        
        # Check completeness
        completeness_issues = self._check_job_completeness(job_req)
        issues.extend(completeness_issues)
        
        # Check confidence scores (optional field)
        confidence_issues = self._check_confidence_scores(getattr(job_req, 'confidences', {}) or {})
        issues.extend(confidence_issues)
        
        # Calculate overall validation confidence
        critical_issues = [i for i in issues if i.severity == 'critical']
        high_issues = [i for i in issues if i.severity == 'high']
        
        if critical_issues:
            confidence = 0.3
        elif len(high_issues) > 2:
            confidence = 0.5
        elif len(issues) > 5:
            confidence = 0.7
        else:
            confidence = 0.9 - (len(issues) * 0.05)
        
        return ValidationResult(
            is_valid=len(critical_issues) == 0,
            confidence_score=max(0.0, min(1.0, confidence)),
            issues=issues
        )
    
    def validate_cv_analysis(self, cv_analysis: CVAnalysis) -> ValidationResult:
        """
        Validate CV analysis for internal consistency and completeness.
        
        Args:
            cv_analysis: CVAnalysis object to validate
            
        Returns:
            ValidationResult with issues and confidence assessment
        """
        issues = []
        
        # Check score vs justification consistency
        score_issues = self._check_score_justification_consistency(cv_analysis)
        issues.extend(score_issues)
        
        # Check skills extraction quality
        skills_issues = self._check_cv_skills_quality(cv_analysis)
        issues.extend(skills_issues)
        
        # Check recommendations quality
        rec_issues = self._check_recommendations_quality(cv_analysis)
        issues.extend(rec_issues)
        
        # Calculate validation confidence
        critical_issues = [i for i in issues if i.severity == 'critical']
        confidence = 0.8 - (len(critical_issues) * 0.2) - (len(issues) * 0.03)
        
        return ValidationResult(
            is_valid=len(critical_issues) == 0,
            confidence_score=max(0.0, min(1.0, confidence)),
            issues=issues
        )
    
    def validate_matching_score(
        self, 
        score: MatchingScore, 
        cv_analysis: CVAnalysis, 
        job_requirements: JobRequirements
    ) -> ValidationResult:
        """
        Validate matching score against CV analysis and job requirements.
        
        Args:
            score: MatchingScore to validate
            cv_analysis: Original CV analysis
            job_requirements: Original job requirements
            
        Returns:
            ValidationResult with cross-validation issues
        """
        issues = []
        
        # Check component scores vs overall score consistency
        component_issues = self._check_component_score_consistency(score)
        issues.extend(component_issues)
        
        # Check matched skills vs available skills
        skill_match_issues = self._check_skill_matching_consistency(
            score, cv_analysis, job_requirements
        )
        issues.extend(skill_match_issues)
        
        # Check explanation quality
        explanation_issues = self._check_explanation_quality(score)
        issues.extend(explanation_issues)
        
        critical_issues = [i for i in issues if i.severity == 'critical']
        confidence = 0.85 - (len(critical_issues) * 0.15) - (len(issues) * 0.02)
        
        return ValidationResult(
            is_valid=len(critical_issues) == 0,
            confidence_score=max(0.0, min(1.0, confidence)),
            issues=issues
        )
    
    def _check_experience_seniority_consistency(self, job_req: JobRequirements) -> List[ValidationIssue]:
        """Check if experience requirements match seniority level."""
        issues = []
        
        if not job_req.seniority_level or not job_req.experience.minimum_years:
            return issues
        
        seniority = job_req.seniority_level.lower()
        min_years = job_req.experience.minimum_years
        
        # Define expected year ranges for seniority levels
        expected_ranges = {
            'junior': (0, 3),
            'mid': (2, 6), 
            'senior': (5, 10),
            'principal': (8, 20)
        }
        
        # Find matching seniority pattern
        detected_level = None
        for level, patterns in self.seniority_patterns.items():
            if any(pattern in seniority for pattern in patterns):
                detected_level = level
                break
        
        if detected_level and detected_level in expected_ranges:
            min_exp, max_exp = expected_ranges[detected_level]
            if not (min_exp <= min_years <= max_exp):
                issues.append(ValidationIssue(
                    field="experience.minimum_years",
                    issue_type="inconsistency",
                    description=f"Experience requirement ({min_years} years) inconsistent with seniority level ({seniority})",
                    severity="medium",
                    suggested_fix=f"Expected {min_exp}-{max_exp} years for {detected_level} level"
                ))
        
        return issues
    
    def _check_skill_requirements(self, job_req: JobRequirements) -> List[ValidationIssue]:
        """Check skill requirements for quality and consistency."""
        issues = []
        
        # Check if technical skills list is reasonable
        tech_skills = job_req.required_skills.technical
        if len(tech_skills) > 15:
            issues.append(ValidationIssue(
                field="required_skills.technical",
                issue_type="suspicious",
                description=f"Very long technical skills list ({len(tech_skills)} items) may indicate over-extraction",
                severity="low",
                suggested_fix="Review and consolidate skill requirements"
            ))
        
        # Check for duplicate or similar skills
        if tech_skills:
            normalized_skills = [skill.lower().strip() for skill in tech_skills]
            if len(set(normalized_skills)) < len(normalized_skills):
                issues.append(ValidationIssue(
                    field="required_skills.technical",
                    issue_type="invalid",
                    description="Duplicate technical skills detected",
                    severity="medium",
                    suggested_fix="Remove duplicate entries"
                ))
        
        # Check soft skills quality
        soft_skills = job_req.required_skills.soft
        if soft_skills:
            non_standard_soft = [s for s in soft_skills if s.lower() not in self.common_soft_skills]
            if len(non_standard_soft) > len(soft_skills) * 0.5:
                issues.append(ValidationIssue(
                    field="required_skills.soft",
                    issue_type="suspicious",
                    description=f"Many non-standard soft skills: {non_standard_soft[:3]}...",
                    severity="low"
                ))
        
        return issues
    
    def _check_job_completeness(self, job_req: JobRequirements) -> List[ValidationIssue]:
        """Check job requirements completeness."""
        issues = []
        
        # Check critical missing fields
        if not job_req.responsibilities:
            issues.append(ValidationIssue(
                field="responsibilities",
                issue_type="missing",
                description="No job responsibilities extracted",
                severity="high",
                suggested_fix="Review source text for responsibility information"
            ))
        
        if not job_req.required_skills.technical and not job_req.required_skills.soft:
            issues.append(ValidationIssue(
                field="required_skills",
                issue_type="missing", 
                description="No skills requirements extracted",
                severity="critical",
                suggested_fix="Review source text for skill requirements"
            ))
        
        return issues
    
    def _check_confidence_scores(self, confidences: Dict[str, float]) -> List[ValidationIssue]:
        """Check confidence scores for validity."""
        issues = []
        
        for field, conf in confidences.items():
            if not (0.0 <= conf <= 1.0):
                issues.append(ValidationIssue(
                    field=f"confidences.{field}",
                    issue_type="invalid",
                    description=f"Confidence score {conf} outside valid range [0, 1]",
                    severity="high",
                    suggested_fix="Clamp confidence to [0, 1] range"
                ))
        
        return issues
    
    def _check_score_justification_consistency(self, cv_analysis: CVAnalysis) -> List[ValidationIssue]:
        """Check if overall fit score matches justification."""
        issues = []
        
        score = cv_analysis.candidate_suitability.overall_fit_score
        justification = cv_analysis.candidate_suitability.justification.lower()
        
        # Check for inconsistent language
        positive_words = ['excellent', 'strong', 'good', 'perfect', 'ideal', 'outstanding']
        negative_words = ['poor', 'weak', 'limited', 'lacks', 'insufficient', 'gap']
        
        positive_count = sum(1 for word in positive_words if word in justification)
        negative_count = sum(1 for word in negative_words if word in justification)
        
        if score >= 8 and negative_count > positive_count:
            issues.append(ValidationIssue(
                field="candidate_suitability",
                issue_type="inconsistency",
                description=f"High fit score ({score}) but negative justification language",
                severity="medium"
            ))
        elif score <= 4 and positive_count > negative_count:
            issues.append(ValidationIssue(
                field="candidate_suitability", 
                issue_type="inconsistency",
                description=f"Low fit score ({score}) but positive justification language",
                severity="medium"
            ))
        
        return issues
    
    def _check_cv_skills_quality(self, cv_analysis: CVAnalysis) -> List[ValidationIssue]:
        """Check extracted CV skills for quality."""
        issues = []
        
        tech_skills = cv_analysis.key_information.technical_skills
        if len(tech_skills) > 20:
            issues.append(ValidationIssue(
                field="key_information.technical_skills",
                issue_type="suspicious",
                description=f"Unusually long technical skills list ({len(tech_skills)} items)",
                severity="low"
            ))
        
        return issues
    
    def _check_recommendations_quality(self, cv_analysis: CVAnalysis) -> List[ValidationIssue]:
        """Check recommendation quality."""
        issues = []
        
        rec = cv_analysis.recommendations
        
        # Check if recommendations are too generic
        all_recs = rec.tailoring + rec.interview_focus + rec.career_development
        if len(all_recs) < 3:
            issues.append(ValidationIssue(
                field="recommendations",
                issue_type="missing",
                description="Very few recommendations provided",
                severity="medium"
            ))
        
        return issues
    
    def _check_component_score_consistency(self, score: MatchingScore) -> List[ValidationIssue]:
        """Check if component scores are consistent with overall score."""
        issues = []
        
        # Calculate weighted average of component scores (simplified)
        components = [
            score.technical_skills_score,
            score.soft_skills_score, 
            score.experience_score,
            score.qualifications_score,
            score.key_responsibilities_score
        ]
        
        avg_component = sum(components) / len(components)
        overall = score.overall_match_score
        
        # Check for large discrepancies
        if abs(avg_component - overall) > 20:
            issues.append(ValidationIssue(
                field="overall_match_score",
                issue_type="inconsistency",
                description=f"Overall score ({overall}) differs significantly from component average ({avg_component:.1f})",
                severity="medium"
            ))
        
        return issues
    
    def _check_skill_matching_consistency(
        self, 
        score: MatchingScore, 
        cv_analysis: CVAnalysis, 
        job_requirements: JobRequirements
    ) -> List[ValidationIssue]:
        """Check if matched skills actually exist in CV and job requirements."""
        issues = []
        
        cv_tech_skills = {s.lower() for s in cv_analysis.key_information.technical_skills}
        job_tech_skills = {s.lower() for s in job_requirements.required_skills.technical}
        # Some scoring implementations may not include 'matched_skills'. Guard accordingly.
        matched_skills_attr = getattr(score, 'matched_skills', None)
        if isinstance(matched_skills_attr, list):
            matched_skills = {str(s).lower() for s in matched_skills_attr}
            # Check if matched skills exist in both CV and job
            for skill in matched_skills:
                if skill not in cv_tech_skills:
                    issues.append(ValidationIssue(
                        field="matched_skills",
                        issue_type="invalid",
                        description=f"Matched skill '{skill}' not found in CV",
                        severity="high"
                    ))
                if skill not in job_tech_skills:
                    issues.append(ValidationIssue(
                        field="matched_skills", 
                        issue_type="invalid",
                        description=f"Matched skill '{skill}' not found in job requirements",
                        severity="high"
                    ))
        
        return issues
    
    def _check_explanation_quality(self, score: MatchingScore) -> List[ValidationIssue]:
        """Check quality of explanations."""
        issues = []
        
        explanations = [
            score.overall_explanation,
            score.technical_skills_explanation,
            score.experience_explanation
        ]
        
        for i, explanation in enumerate(explanations):
            if len(explanation.strip()) < 10:
                field_names = ["overall_explanation", "technical_skills_explanation", "experience_explanation"]
                issues.append(ValidationIssue(
                    field=field_names[i],
                    issue_type="missing",
                    description="Very brief explanation provided",
                    severity="low"
                ))
        
        return issues

# Global validator instance
data_validator = DataValidator()