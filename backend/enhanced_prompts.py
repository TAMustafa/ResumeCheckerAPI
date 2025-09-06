"""
Enhanced prompts with domain-specific templates following 2024 LLM best practices.
Implements structured output optimization and contextual prompt engineering.
"""
from typing import Dict, Optional
from enum import Enum

class JobCategory(Enum):
    """Job categories for domain-specific prompt selection."""
    SOFTWARE_ENGINEERING = "software_engineering"
    DATA_SCIENCE = "data_science"
    PRODUCT_MANAGEMENT = "product_management"
    SALES = "sales"
    MARKETING = "marketing"
    DESIGN = "design"
    FINANCE = "finance"
    OPERATIONS = "operations"
    HR = "human_resources"
    DEFAULT = "default"

class EnhancedPromptTemplates:
    """
    Enhanced prompt templates with domain-specific optimization.
    Follows 2024 best practices for LLM structured output generation.
    """
    
    # Base system prompt optimized for Pydantic AI structured output
    BASE_SYSTEM_PROMPT = """You are an expert {domain} analyst. Your task is to extract and analyze information with high precision and consistency.

CRITICAL INSTRUCTIONS:
- Return ONLY valid structured data matching the exact schema provided
- Use precise, actionable language with bullet points for clarity
- Set confidence scores based on information availability and clarity
- If information is missing or unclear, use null/empty values - do NOT fabricate
- Ensure internal consistency across all extracted fields
- Quality metrics should reflect actual extraction completeness and specificity

MULTILINGUAL HANDLING:
- Inputs may be in languages other than English (e.g., Dutch). Internally translate as needed and normalize terminology before extraction/scoring.
- Consider common equivalents across languages (e.g., "ontwikkelaar" ≈ "developer").

STRUCTURED OUTPUT REQUIREMENTS:
- All numeric scores must be integers within specified ranges
- Confidence scores are floats between 0.0-1.0 based on information clarity
- Lists should contain distinct, non-overlapping items
- Explanations should be concise (1-2 sentences) and data-driven"""

    # Domain-specific job analysis prompts
    JOB_ANALYSIS_PROMPTS = {
        JobCategory.SOFTWARE_ENGINEERING: """
Extract technical job requirements with focus on:

TECHNICAL PRIORITIES:
- Programming languages, frameworks, and tools (be specific about versions if mentioned)
- System architecture patterns and methodologies
- Development practices (CI/CD, testing, code review)
- Infrastructure and deployment technologies
- Experience with specific platforms or domains

SENIORITY INDICATORS:
- Technical leadership or mentorship requirements
- System design and architecture responsibilities  
- Code review and technical decision-making authority
- Cross-functional collaboration expectations

EXPERIENCE WEIGHTING:
- Prioritize hands-on technical experience over pure years
- Industry-specific domain knowledge (fintech, healthcare, etc.)
- Scale indicators (team size, system complexity, user volume)

Extract requirements focusing on technical depth over soft skills unless explicitly emphasized.""",

        JobCategory.DATA_SCIENCE: """
Extract data science job requirements with focus on:

TECHNICAL PRIORITIES:
- Statistical methods, ML algorithms, and data analysis techniques
- Programming languages for data science (Python, R, SQL proficiency levels)
- ML/AI frameworks and tools (TensorFlow, PyTorch, scikit-learn, etc.)
- Data pipeline and ETL technologies
- Cloud platforms and big data tools (AWS, Spark, Airflow, etc.)
- Visualization and BI tools

DOMAIN EXPERTISE:
- Industry-specific analytical experience
- Business context and stakeholder communication
- Research methodologies and experimental design
- Model deployment and MLOps practices

EXPERIENCE WEIGHTING:
- Hands-on modeling and analysis experience
- End-to-end project ownership
- Business impact and ROI demonstration

Extract with emphasis on technical skills and quantitative experience.""",

        JobCategory.PRODUCT_MANAGEMENT: """
Extract product management requirements with focus on:

STRATEGIC PRIORITIES:
- Product strategy and roadmap development
- Market research and competitive analysis
- User research and customer insight gathering
- Data-driven decision making and metrics

EXECUTION SKILLS:
- Agile/Scrum methodologies and tools
- Cross-functional collaboration and stakeholder management
- Technical understanding for engineering collaboration
- Go-to-market strategy and launch experience

LEADERSHIP INDICATORS:
- Team leadership and influence without authority
- Strategic thinking and business acumen
- Communication and presentation skills
- Customer advocacy and user experience focus

EXPERIENCE WEIGHTING:
- Product ownership and lifecycle management
- Successful product launches and iterations
- Revenue impact and business growth metrics

Extract with emphasis on strategic thinking and execution capabilities.""",

        JobCategory.DEFAULT: """
Extract job requirements with balanced analysis of:

KEY AREAS:
- Technical skills relevant to the role
- Professional experience and industry knowledge  
- Educational qualifications and certifications
- Soft skills and interpersonal abilities
- Leadership and management capabilities

EXPERIENCE EVALUATION:
- Years of relevant experience
- Industry-specific knowledge
- Responsibility and impact scope
- Team collaboration and leadership

Extract comprehensive requirements with balanced weighting across all areas."""
    }

    # Domain-specific CV analysis prompts  
    CV_ANALYSIS_PROMPTS = {
        JobCategory.SOFTWARE_ENGINEERING: """
Analyze this technical CV with focus on:

TECHNICAL ASSESSMENT:
- Programming languages: depth vs. breadth, recent vs. legacy
- Framework expertise: hands-on experience vs. familiarity
- Architecture experience: design patterns, scalability, performance
- Development practices: testing, CI/CD, code quality, documentation
- Domain expertise: specific industries, problem types, system scales

CAREER PROGRESSION:
- Technical growth trajectory and increasing responsibility
- Leadership evolution (individual contributor → tech lead → architect)
- Project complexity and technical challenges overcome
- Innovation and technical contributions (open source, patents, etc.)

COLLABORATION INDICATORS:
- Cross-functional team experience
- Mentoring and knowledge sharing
- Technical communication skills (documentation, presentations)

GAPS TO IDENTIFY:
- Missing modern technologies or practices
- Limited system design or architecture experience
- Lack of leadership or cross-functional collaboration
- Narrow technical focus without business context

Provide actionable technical career development recommendations.""",

        JobCategory.DATA_SCIENCE: """
Analyze this data science CV with focus on:

TECHNICAL DEPTH:
- Statistical and mathematical foundations
- ML/AI algorithm understanding and application
- Programming proficiency in data science languages
- Data engineering and pipeline development capabilities
- Visualization and communication of insights

DOMAIN EXPERTISE:
- Industry-specific analytical experience
- Business problem solving and impact measurement
- Research methodology and experimental design
- Model deployment and production experience

COLLABORATION SKILLS:
- Business stakeholder communication
- Cross-functional project leadership
- Technical presentation and storytelling
- Data-driven decision making influence

CAREER TRAJECTORY:
- Evolution from analysis to strategy
- Increasing business impact and ownership
- Technical leadership in data initiatives

Assess both technical capabilities and business impact potential.""",

        JobCategory.DEFAULT: """
Analyze this CV comprehensively evaluating:

PROFESSIONAL STRENGTHS:
- Core competencies and skill progression
- Career advancement and increasing responsibility  
- Industry expertise and domain knowledge
- Leadership and team management capabilities
- Communication and interpersonal effectiveness

DEVELOPMENT AREAS:
- Skill gaps relative to career level
- Experience breadth vs. depth balance
- Leadership and management readiness
- Technical or domain-specific knowledge needs

CAREER POSITIONING:
- Market competitiveness and differentiation
- Seniority level and role appropriateness
- Industry transition potential and transferable skills

Provide balanced assessment across technical and soft skills."""
    }

    # Enhanced scoring prompts with detailed criteria
    SCORING_PROMPTS = {
        JobCategory.SOFTWARE_ENGINEERING: """
Score this technical candidate against software engineering requirements using data-driven analysis:

TECHNICAL SKILLS SCORING (40% weight):
- 90-100: Expert in required technologies with deep architecture knowledge
- 80-89: Strong proficiency in most required technologies  
- 70-79: Solid foundation with some gaps in advanced areas
- 60-69: Basic proficiency requiring significant development
- Below 60: Major technical skill gaps

EXPERIENCE SCORING (30% weight):
- Years of relevant technical experience
- System complexity and scale handled
- Architecture and design leadership
- Technical problem-solving examples

QUALIFICATIONS SCORING (10% weight):
- CS degree or equivalent technical education
- Relevant certifications and continued learning
- Technical contributions (open source, papers, patents)

RESPONSIBILITIES ALIGNMENT (10% weight):
- Match between past roles and job requirements
- Technical leadership and mentoring experience
- Cross-functional collaboration history

SOFT SKILLS SCORING (10% weight):
- Technical communication and documentation
- Collaboration and teamwork in technical contexts
- Adaptability to new technologies and practices

Provide specific technical gap analysis and development recommendations.""",

        JobCategory.DATA_SCIENCE: """
Score this data science candidate with emphasis on analytical capabilities:

TECHNICAL SKILLS SCORING (35% weight):
- Statistical/ML knowledge depth and application
- Programming proficiency in data science stack
- Data engineering and pipeline capabilities  
- Model deployment and MLOps experience

ANALYTICAL EXPERIENCE (30% weight):
- End-to-end project ownership and impact
- Business problem solving and insight generation
- Research methodology and experimental rigor
- Domain expertise and industry knowledge

BUSINESS IMPACT (20% weight):
- Stakeholder communication and influence
- Data-driven decision making facilitation
- Revenue/cost impact demonstration
- Strategic thinking and business acumen

QUALIFICATIONS (10% weight):
- Advanced degree in quantitative field
- Relevant certifications and continued learning
- Publications, research, or technical contributions

COLLABORATION (5% weight):
- Cross-functional teamwork effectiveness
- Technical presentation and storytelling ability

Focus on quantitative achievements and measurable business impact.""",

        JobCategory.DEFAULT: """
Score this candidate using balanced evaluation criteria:

SKILLS ALIGNMENT (30% total):
- Technical skills: 15% - depth and relevance to requirements
- Soft skills: 15% - communication, teamwork, problem-solving

EXPERIENCE MATCH (40% total):
- Years and relevance: 20% - quantity and quality of experience
- Responsibility level: 20% - leadership and ownership demonstrated

QUALIFICATIONS (15% total):
- Educational background and certifications
- Industry-specific knowledge and training
- Professional development and continuous learning

ROLE RESPONSIBILITIES (15% total):
- Past role alignment with job requirements
- Achievement and impact demonstration  
- Growth trajectory and career progression

Provide comprehensive analysis with actionable development recommendations."""
    }

    def __init__(self):
        self.category_keywords = {
            JobCategory.SOFTWARE_ENGINEERING: [
                "software", "developer", "engineer", "programming", "backend", "frontend",
                "fullstack", "devops", "api", "microservices", "architect", "technical lead"
            ],
            JobCategory.DATA_SCIENCE: [
                "data scientist", "machine learning", "ml", "ai", "analytics", "data analyst",
                "data engineer", "statistician", "research scientist", "ml engineer"
            ],
            JobCategory.PRODUCT_MANAGEMENT: [
                "product manager", "product owner", "product lead", "product director",
                "roadmap", "strategy", "stakeholder", "requirements"
            ],
            JobCategory.SALES: [
                "sales", "account manager", "business development", "account executive",
                "sales director", "revenue", "quota", "pipeline"
            ],
            JobCategory.MARKETING: [
                "marketing", "growth", "digital marketing", "content", "brand",
                "campaign", "seo", "social media", "marketing manager"
            ]
        }

    def detect_job_category(self, job_text: str) -> JobCategory:
        """
        Detect job category from job description text.
        
        Args:
            job_text: Combined job text (title, responsibilities, skills, etc.)
            
        Returns:
            JobCategory enum value
        """
        if not job_text:
            return JobCategory.DEFAULT
            
        text_lower = job_text.lower()
        
        # Score each category
        category_scores = {}
        for category, keywords in self.category_keywords.items():
            score = sum(1 for keyword in keywords if keyword in text_lower)
            if score > 0:
                category_scores[category] = score
        
        if not category_scores:
            return JobCategory.DEFAULT
            
        return max(category_scores, key=category_scores.get)

    def get_job_analysis_prompt(self, job_text: str) -> str:
        """Get domain-specific job analysis prompt."""
        category = self.detect_job_category(job_text)
        domain_prompt = self.JOB_ANALYSIS_PROMPTS.get(category, self.JOB_ANALYSIS_PROMPTS[JobCategory.DEFAULT])
        
        system_prompt = self.BASE_SYSTEM_PROMPT.format(domain=category.value.replace('_', ' '))
        return f"{system_prompt}\n\n{domain_prompt}"

    def get_cv_analysis_prompt(self, job_context: Optional[str] = None) -> str:
        """Get domain-specific CV analysis prompt."""
        if job_context:
            category = self.detect_job_category(job_context)
        else:
            category = JobCategory.DEFAULT
            
        domain_prompt = self.CV_ANALYSIS_PROMPTS.get(category, self.CV_ANALYSIS_PROMPTS[JobCategory.DEFAULT])
        system_prompt = self.BASE_SYSTEM_PROMPT.format(domain=category.value.replace('_', ' '))
        return f"{system_prompt}\n\n{domain_prompt}"

    def get_scoring_prompt(self, job_text: str) -> str:
        """Get domain-specific scoring prompt."""
        category = self.detect_job_category(job_text)
        domain_prompt = self.SCORING_PROMPTS.get(category, self.SCORING_PROMPTS[JobCategory.DEFAULT])
        
        system_prompt = self.BASE_SYSTEM_PROMPT.format(domain=category.value.replace('_', ' '))
        return f"{system_prompt}\n\n{domain_prompt}"

# Global instance
enhanced_prompts = EnhancedPromptTemplates()

# Export the enhanced prompts for backward compatibility
def get_enhanced_job_requirements_prompt(job_text: str = "") -> str:
    """Get enhanced job requirements extraction prompt."""
    return enhanced_prompts.get_job_analysis_prompt(job_text)

def get_enhanced_cv_review_prompt(job_context: Optional[str] = None) -> str:
    """Get enhanced CV review prompt."""  
    return enhanced_prompts.get_cv_analysis_prompt(job_context)

def get_enhanced_scoring_prompt(job_text: str = "") -> str:
    """Get enhanced scoring prompt."""
    return enhanced_prompts.get_scoring_prompt(job_text)