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

# CORS configuration
# Set ALLOWED_ORIGINS in env as a comma-separated list, e.g.:
#   ALLOWED_ORIGINS=https://yourdomain.tld,chrome-extension://<ext-id>
_allowed_env = os.getenv("ALLOWED_ORIGINS", "").strip()
if not _allowed_env:
    # Fallback defaults when env is unset or blank
    defaults = [
        "http://91.98.122.7",  # Hetzner public IP (HTTP via Caddy)
        "http://localhost:8000",
        "chrome-extension://*",
    ]
    ALLOWED_ORIGINS = defaults
else:
    ALLOWED_ORIGINS = [o.strip() for o in _allowed_env.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=[
        "*",
        "X-OpenAI-Key",
    ],
    expose_headers=["*"],
)

@app.get("/", response_class=HTMLResponse)
async def root():
    return "<h2>Resume Checker API is running.</h2>"

class VacancyRequest(BaseModel):
    vacancy_text: str

@app.post("/analyze-job-vacancy")
async def api_analyze_job_vacancy(req: VacancyRequest, x_openai_key: str | None = Header(default=None, alias="X-OpenAI-Key")):
    try:
        result = await analyze_job_vacancy(req.vacancy_text, api_key=x_openai_key)
        return result.model_dump()
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/analyze-cv")
async def api_analyze_cv(
    request: Request,
    file: UploadFile = File(...),
    x_openai_key: str | None = Header(default=None, alias="X-OpenAI-Key"),
):
    try:
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
        result = await analyze_cv(file_path, api_key=x_openai_key)
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
async def api_score_cv_match(req: ScoreRequest, x_openai_key: str | None = Header(default=None, alias="X-OpenAI-Key")):
    try:
        cv_obj = CVAnalysis(**req.cv_analysis)
        job_obj = JobRequirements(**req.job_requirements)
        result = await score_cv_match(cv_obj, job_obj, api_key=x_openai_key)
        return result.model_dump() if hasattr(result, 'model_dump') else result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/healthz")
async def healthz():
    return {"status": "ok"}
