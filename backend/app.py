from fastapi import FastAPI, UploadFile, File, HTTPException, status
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pathlib import Path
from dotenv import load_dotenv
import shutil
from typing import List
from datetime import datetime

from models import JobRequirements, CVAnalysis, MatchingScore
from agents import analyze_job_vacancy, analyze_cv, score_cv_match

load_dotenv()

app = FastAPI()

# Configuration
UPLOAD_DIR = Path("uploaded_cvs")
UPLOAD_DIR.mkdir(exist_ok=True)  # Create directory if it doesn't exist

# Allow CORS for local development (Chrome extension)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For production, restrict this!
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/", response_class=HTMLResponse)
async def root():
    return "<h2>Resume Checker API is running.</h2>"

class VacancyRequest(BaseModel):
    vacancy_text: str

@app.post("/analyze-job-vacancy")
async def api_analyze_job_vacancy(req: VacancyRequest):
    try:
        result = await analyze_job_vacancy(req.vacancy_text)
        return result.model_dump()
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/analyze-cv")
async def api_analyze_cv(file: UploadFile = File(...)):
    try:
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
            
        # Analyze the CV
        result = await analyze_cv(file_path)
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

class ScoreRequest(BaseModel):
    cv_analysis: dict
    job_requirements: dict

@app.post("/score-cv-match")
async def api_score_cv_match(req: ScoreRequest):
    try:
        cv_obj = CVAnalysis(**req.cv_analysis)
        job_obj = JobRequirements(**req.job_requirements)
        result = await score_cv_match(cv_obj, job_obj)
        return result.model_dump() if hasattr(result, 'model_dump') else result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
