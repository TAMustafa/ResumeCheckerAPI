from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from pathlib import Path
from dotenv import load_dotenv

# Import models and agent logic
from models import JobRequirements, CVAnalysis, MatchingScore
from agents import analyze_job_vacancy, analyze_cv, score_cv_match

load_dotenv()

app = FastAPI()

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
        contents = await file.read()
        tmp_path = Path(f"/tmp/{file.filename}")
        tmp_path.write_bytes(contents)
        result = await analyze_cv(tmp_path)
        tmp_path.unlink(missing_ok=True)
        return result.model_dump()
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

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
