from fastapi import FastAPI, UploadFile, File, HTTPException, status, Header, Request
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pathlib import Path
from dotenv import load_dotenv
import shutil
import os
import logfire
from uuid import uuid4
import inspect

from models import JobRequirements, CVAnalysis, MatchingScore
import agents

load_dotenv()

app = FastAPI()

# Configuration
UPLOAD_DIR = Path("uploaded_cvs")
UPLOAD_DIR.mkdir(exist_ok=True)  # Create directory if it doesn't exist

# Max upload size (in MB). Defaults to 10MB. Applies to Content-Length and verified file size on disk.
try:
    MAX_UPLOAD_MB = int(os.getenv("MAX_UPLOAD_MB", "10"))
    if MAX_UPLOAD_MB <= 0:
        MAX_UPLOAD_MB = 10
except Exception:
    MAX_UPLOAD_MB = 10
MAX_UPLOAD_BYTES = MAX_UPLOAD_MB * 1024 * 1024

# Require per-user OpenAI API key by default (can be overridden via env)
REQUIRE_USER_API_KEY = os.getenv("REQUIRE_USER_API_KEY", "true").lower() in {"1", "true", "yes"}

# Data retention policy: do NOT retain uploaded CVs on the server.
# Files are processed and deleted immediately after analysis.
# This is hardcoded for Chrome Web Store compliance (no server storage of user CVs).
RETAIN_UPLOADED_CVS = False

# CORS configuration
# Prefer explicit ALLOWED_ORIGINS; otherwise build safe defaults.
# To allow your extension explicitly, set CHROME_EXTENSION_ID to include
# chrome-extension://<ID> instead of using any wildcard.
_allowed_env = os.getenv("ALLOWED_ORIGINS", "").strip()
if _allowed_env:
    ALLOWED_ORIGINS = [o.strip() for o in _allowed_env.split(",") if o.strip()]
else:
    ALLOWED_ORIGINS = [
        "http://cv.kroete.io",  # Server origin (HTTP for now)
        "http://localhost:8000",  # Dev local
    ]
    _ext_id = os.getenv("CHROME_EXTENSION_ID", "").strip()
    if _ext_id:
        ALLOWED_ORIGINS.append(f"chrome-extension://{_ext_id}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"]
)

# Correlation ID middleware for observability; adds X-Request-ID
@app.middleware("http")
async def add_request_id(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID") or str(uuid4())
    # attach to request state for downstream logs
    request.state.request_id = request_id
    try:
        response = await call_next(request)
    finally:
        # ensure header on response even if exception handlers run
        pass
    response.headers["X-Request-ID"] = request_id
    return response

@app.get("/", response_class=HTMLResponse)
async def root():
    return "<h2>Resume Checker API is running.</h2>"

class VacancyRequest(BaseModel):
    vacancy_text: str

@app.post("/analyze-job-vacancy")
async def api_analyze_job_vacancy(
    req: VacancyRequest,
    x_openai_key: str | None = Header(default=None, alias="X-OpenAI-Key"),
    x_llm_provider: str | None = Header(default=None, alias="X-LLM-Provider"),
    x_llm_model: str | None = Header(default=None, alias="X-LLM-Model"),
):
    try:
        logfire.info("/analyze-job-vacancy request", extra={
            "request_id": getattr(locals().get('req', None), 'request_id', None) or getattr(locals().get('request', None), 'state', None) and getattr(locals().get('request').state, 'request_id', None),
            "provider": (x_llm_provider or "openai").lower() if x_llm_provider is not None else "openai",
            "model": x_llm_model or "gpt-4o",
        })
        if REQUIRE_USER_API_KEY and not x_openai_key:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="X-OpenAI-Key is required")
        provider = (x_llm_provider or "openai").lower()
        if provider != "openai":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"LLM provider '{provider}' not supported yet")
        # Support both async and sync agent implementations (tests monkeypatch a sync fn)
        res = agents.analyze_job_vacancy(req.vacancy_text, api_key=x_openai_key, provider=provider, model=x_llm_model)
        result = await res if inspect.isawaitable(res) else res
        return result.model_dump()
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/analyze-cv")
async def api_analyze_cv(
    request: Request,
    file: UploadFile = File(...),
    x_openai_key: str | None = Header(default=None, alias="X-OpenAI-Key"),
    x_llm_provider: str | None = Header(default=None, alias="X-LLM-Provider"),
    x_llm_model: str | None = Header(default=None, alias="X-LLM-Model"),
):
    try:
        if REQUIRE_USER_API_KEY and not x_openai_key:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="X-OpenAI-Key is required")
        provider = (x_llm_provider or "openai").lower()
        if provider != "openai":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"LLM provider '{provider}' not supported yet")
        # Enforce Content-Length if provided
        content_length = request.headers.get("content-length")
        if content_length is not None:
            try:
                if int(content_length) > MAX_UPLOAD_BYTES:
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail=f"File too large. Max {MAX_UPLOAD_MB}MB",
                    )
            except ValueError:
                # ignore malformed header and continue with on-disk size validation
                pass
        # Ensure the file is a PDF
        if not file.filename.lower().endswith('.pdf'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only PDF files are accepted"
            )
        
        # Save the uploaded file
        file_path = UPLOAD_DIR / file.filename
        with file_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        # Verify size on disk
        try:
            if file_path.stat().st_size > MAX_UPLOAD_BYTES:
                file_path.unlink(missing_ok=True)
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail=f"File too large. Max {MAX_UPLOAD_MB}MB",
                )
        except FileNotFoundError:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Upload failed: file missing after write"
            )
        
        # Analyze the CV (support sync/async monkeypatches)
        res = agents.analyze_cv(file_path, api_key=x_openai_key, provider=provider, model=x_llm_model)
        result = await res if inspect.isawaitable(res) else res

        # Delete immediately unless retention is enabled
        if not RETAIN_UPLOADED_CVS:
            try:
                file_path.unlink(missing_ok=True)
            except Exception:
                # Best-effort deletion; do not fail the request
                pass

        return result.model_dump()
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing CV: {str(e)}"
        )
    finally:
        if 'file' in locals():
            await file.close()


class ScoreRequest(BaseModel):
    cv_analysis: dict
    job_requirements: dict

@app.post("/score-cv-match")
async def api_score_cv_match(
    req: ScoreRequest,
    x_openai_key: str | None = Header(default=None, alias="X-OpenAI-Key"),
    x_llm_provider: str | None = Header(default=None, alias="X-LLM-Provider"),
    x_llm_model: str | None = Header(default=None, alias="X-LLM-Model"),
):
    try:
        # Align scoring to the same LLM pipeline and quality as CV/Job analysis
        if REQUIRE_USER_API_KEY and not x_openai_key:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="X-OpenAI-Key is required")
        provider = (x_llm_provider or "openai").lower()
        if provider != "openai":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"LLM provider '{provider}' not supported yet")
        def _sanitize_job(req_dict: dict) -> dict:
            # Only keep known keys; default nested structures where missing
            jr = req_dict or {}
            # Start with direct mappings
            req_skills = jr.get("required_skills") or {}
            tech = list(req_skills.get("technical", []) or [])
            soft = list(req_skills.get("soft", []) or [])

            # Heuristic mappings from alternative keys commonly returned by LLMs
            # e.g., flat 'skills' list or separate 'technical_skills'/'soft_skills'
            if not tech:
                tech = list(jr.get("technical_skills", []) or [])
            if not soft:
                soft = list(jr.get("soft_skills", []) or [])
            # If only a flat list of skills is provided, assume technical by default
            if not tech and not soft and isinstance(jr.get("skills"), list):
                tech = list(jr.get("skills") or [])

            # Responsibilities may be provided under different keys
            responsibilities = list(jr.get("responsibilities", []) or [])
            if not responsibilities and isinstance(jr.get("tasks"), list):
                responsibilities = list(jr.get("tasks") or [])
            # Some LLMs put bullet points under 'requirements' mixing skills and duties
            if not responsibilities and isinstance(jr.get("requirements"), list):
                responsibilities = list(jr.get("requirements") or [])

            qualifications = list(jr.get("qualifications", []) or [])
            # Map certifications/education into qualifications if qualifications is empty
            if not qualifications:
                qualifications = list(jr.get("certifications", []) or [])
            education = jr.get("education")
            if not qualifications and isinstance(education, list):
                qualifications = list(education)

            languages = list(jr.get("languages", []) or [])
            if not languages:
                # Sometimes under 'language_requirements'
                alt_lang = jr.get("language_requirements")
                if isinstance(alt_lang, list):
                    languages = list(alt_lang)

            out = {
                "required_skills": {
                    "technical": tech,
                    "soft": soft,
                },
                "experience": {
                    "minimum_years": (jr.get("experience") or {}).get("minimum_years"),
                    "industry": (jr.get("experience") or {}).get("industry"),
                    "type": (jr.get("experience") or {}).get("type"),
                    "leadership": (jr.get("experience") or {}).get("leadership"),
                },
                "qualifications": qualifications,
                "responsibilities": responsibilities,
                "languages": languages,
                "seniority_level": jr.get("seniority_level"),
            }
            return out

        def _sanitize_cv(cv_dict: dict) -> dict:
            cv = cv_dict or {}
            # recommendations may be object or array
            rec = cv.get("recommendations")
            if isinstance(rec, list):
                recommendations = {
                    "tailoring": list(rec),
                    "interview_focus": [],
                    "career_development": [],
                }
            elif isinstance(rec, dict):
                recommendations = {
                    "tailoring": list(rec.get("tailoring", []) or []),
                    "interview_focus": list(rec.get("interview_focus", []) or []),
                    "career_development": list(rec.get("career_development", []) or []),
                }
            else:
                recommendations = {"tailoring": [], "interview_focus": [], "career_development": []}

            key_info_in = cv.get("key_information") or {}
            candidate_in = cv.get("candidate_suitability") or {}
            # Heuristic enrichments for key_information if provided at top-level
            if not key_info_in:
                # Accept top-level fallbacks to avoid empty comparisons
                key_info_in = {
                    "experience_summary": cv.get("experience_summary") or "",
                    "technical_skills": list(cv.get("technical_skills", []) or []),
                    "soft_skills": list(cv.get("soft_skills", []) or []),
                    "certifications": list(cv.get("certifications", []) or []),
                    "languages": list(cv.get("languages", []) or []),
                    "responsibilities": list(cv.get("responsibilities", []) or []),
                }
            out = {
                "candidate_suitability": {
                    "overall_fit_score": candidate_in.get("overall_fit_score") or 5,
                    "justification": candidate_in.get("justification") or "",
                    "strengths": list(candidate_in.get("strengths", []) or []),
                    "gaps": list(candidate_in.get("gaps", []) or []),
                },
                "key_information": {
                    "experience_summary": key_info_in.get("experience_summary") or "",
                    "technical_skills": list(key_info_in.get("technical_skills", []) or []),
                    "soft_skills": list(key_info_in.get("soft_skills", []) or []),
                    "certifications": list(key_info_in.get("certifications", []) or []),
                    "languages": list(key_info_in.get("languages", []) or []),
                    "responsibilities": list(key_info_in.get("responsibilities", []) or []),
                },
                "recommendations": recommendations,
            }
            return out

        cv_obj = CVAnalysis(**_sanitize_cv(req.cv_analysis))
        job_obj = JobRequirements(**_sanitize_job(req.job_requirements))
        # Delegate scoring to agents (LLM-based) for better intersection-focused results
        res = agents.score_cv_match(cv_obj, job_obj, api_key=x_openai_key, provider=provider, model=x_llm_model)
        result = await res if inspect.isawaitable(res) else res
        data = result.model_dump()

        # --- Post-processing safeguards ---
        # 1) Prevent an overall 0% if components indicate non-zero match.
        try:
            comps = [
                int(data.get("technical_skills_score", 0) or 0),
                int(data.get("soft_skills_score", 0) or 0),
                int(data.get("experience_score", 0) or 0),
                int(data.get("qualifications_score", 0) or 0),
                int(data.get("key_responsibilities_score", 0) or 0),
            ]
            if data.get("overall_match_score", 0) == 0 and any(c > 0 for c in comps):
                avg = int(sum(comps) / max(1, len(comps)))
                data["overall_match_score"] = avg
                if not data.get("overall_explanation"):
                    data["overall_explanation"] = "Adjusted to average of component scores due to detected intersections."
        except Exception:
            pass

        # 2) Ensure strengths emphasize real intersections between CV and Job
        try:
            cv = cv_obj
            job = job_obj
            strengths = list(data.get("strengths") or [])

            # Build intersections across categories
            def _norm_set(items):
                return {str(x).strip().lower() for x in (items or []) if str(x).strip()}

            tech_overlap = sorted(_norm_set(cv.key_information.technical_skills) & _norm_set(job.required_skills.technical))
            soft_overlap = sorted(_norm_set(cv.key_information.soft_skills) & _norm_set(job.required_skills.soft))
            qual_overlap = sorted(_norm_set(cv.key_information.certifications) & _norm_set(job.qualifications))
            lang_overlap = sorted(_norm_set(cv.key_information.languages) & _norm_set(job.languages))
            resp_overlap = sorted(_norm_set(cv.key_information.responsibilities) & _norm_set(job.responsibilities))

            overlaps = []
            overlaps.extend([s.title() for s in tech_overlap])
            overlaps.extend([s.title() for s in soft_overlap])
            overlaps.extend([s.title() for s in qual_overlap])
            overlaps.extend([s.title() for s in lang_overlap])
            overlaps.extend([s for s in resp_overlap])

            # If provided strengths are empty or contain items not in overlaps, replace with overlaps (top 10)
            normalized_strengths = _norm_set(strengths)
            if not strengths or not normalized_strengths.issubset(_norm_set(overlaps)):
                data["strengths"] = overlaps[:10]
        except Exception:
            pass

        return data
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"scoring_error: {e}")


@app.get("/healthz")
async def healthz():
    return {"status": "ok"}
