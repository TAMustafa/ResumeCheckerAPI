from fastapi import FastAPI, UploadFile, File, HTTPException, status, Header, Request
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pathlib import Path
from dotenv import load_dotenv
import shutil
from typing import List
from datetime import datetime
import os
import logfire
from uuid import uuid4

from models import JobRequirements, CVAnalysis, MatchingScore
from agents import analyze_job_vacancy, analyze_cv, score_cv_match

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

# Data retention: control whether uploaded CVs are retained on disk after analysis.
# Defaults to False (do not retain) for privacy. When False, the server deletes
# the uploaded file immediately after analysis, and listing/downloading is disabled.
RETAIN_UPLOADED_CVS = os.getenv("RETAIN_UPLOADED_CVS", "false").lower() in {"1", "true", "yes"}

# CORS configuration
# Prefer explicit ALLOWED_ORIGINS; otherwise build safe defaults.
# To allow your extension explicitly, set CHROME_EXTENSION_ID to include
# chrome-extension://<ID> instead of using any wildcard.
_allowed_env = os.getenv("ALLOWED_ORIGINS", "").strip()
if _allowed_env:
    ALLOWED_ORIGINS = [o.strip() for o in _allowed_env.split(",") if o.strip()]
else:
    ALLOWED_ORIGINS = [
        "http://91.98.122.7",  # Server origin (HTTP for now)
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
        result = await analyze_job_vacancy(req.vacancy_text, api_key=x_openai_key, provider=provider, model=x_llm_model)
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
        
        # Analyze the CV
        result = await analyze_cv(file_path, api_key=x_openai_key, provider=provider, model=x_llm_model)

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

class CVFile(BaseModel):
    filename: str
    originalname: str
    size: int
    uploaded_at: str

@app.get("/api/uploaded-cvs", response_model=List[CVFile])
async def list_uploaded_cvs():
    """
    List all previously uploaded CVs in the uploaded_cvs directory.
    Returns a list of CV files with their metadata.
    """
    try:
        if not RETAIN_UPLOADED_CVS:
            return []
        cv_files = []
        for file_path in UPLOAD_DIR.glob("*.pdf"):  # Only list PDF files
            if file_path.is_file():
                stat = file_path.stat()
                cv_files.append({
                    "filename": file_path.name,
                    "originalname": file_path.name,  # In a real app, you might store the original name separately
                    "size": stat.st_size,
                    "uploaded_at": datetime.fromtimestamp(stat.st_mtime).isoformat()
                })
        
        # Sort by upload time (newest first)
        cv_files.sort(key=lambda x: x["uploaded_at"], reverse=True)
        return cv_files
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error listing CVs: {str(e)}"
        )

@app.get("/uploaded_cvs/{filename}")
async def get_uploaded_cv(filename: str):
    """
    Serve an uploaded CV file.
    """
    try:
        if not RETAIN_UPLOADED_CVS:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File not found"
            )
        # Security: Only allow PDF files
        if not filename.lower().endswith('.pdf'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only PDF files are allowed"
            )
            
        file_path = UPLOAD_DIR / filename
        
        # Security: Prevent directory traversal
        try:
            file_path = file_path.resolve()
            if not file_path.is_relative_to(UPLOAD_DIR.resolve()) or not file_path.is_file():
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="File not found"
                )
        except (ValueError, RuntimeError):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid filename"
            )
            
        return FileResponse(
            str(file_path),
            media_type="application/pdf",
            filename=filename
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving CV: {str(e)}"
        )

@app.delete("/api/uploaded-cvs/{filename}", status_code=204)
async def delete_uploaded_cv(filename: str):
    """
    Delete an uploaded CV file. Only allows deletion of PDF files inside the
    configured upload directory. Returns 204 on success.
    """
    try:
        if not RETAIN_UPLOADED_CVS:
            # Nothing to delete / feature disabled
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File not found"
            )
        # Only allow PDF files
        if not filename.lower().endswith('.pdf'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only PDF files are allowed"
            )

        file_path = UPLOAD_DIR / filename

        # Prevent directory traversal and ensure file exists
        try:
            resolved = file_path.resolve()
            if not resolved.is_relative_to(UPLOAD_DIR.resolve()) or not resolved.is_file():
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="File not found"
                )
        except (ValueError, RuntimeError):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid filename"
            )

        # Perform deletion
        resolved.unlink(missing_ok=False)
        # 204 No Content
        return
    
    except HTTPException:
        raise
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting CV: {str(e)}"
        )

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
        if REQUIRE_USER_API_KEY and not x_openai_key:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="X-OpenAI-Key is required")
        provider = (x_llm_provider or "openai").lower()
        if provider != "openai":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"LLM provider '{provider}' not supported yet")
        cv_obj = CVAnalysis(**req.cv_analysis)
        job_obj = JobRequirements(**req.job_requirements)
        result = await score_cv_match(cv_obj, job_obj, api_key=x_openai_key, provider=provider, model=x_llm_model)
        return result.model_dump() if hasattr(result, 'model_dump') else result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/healthz")
async def healthz():
    return {"status": "ok"}
