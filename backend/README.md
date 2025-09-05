### Healthcheck

- `GET /healthz`: Returns `{ "status": "ok" }` for load balancers and deployment checks.

### Authentication / API key propagation

- The backend supports a per-request OpenAI API key via the header `X-OpenAI-Key`.
- The Chrome extension stores the user's key and includes it on every request.
- If the header is missing, the backend falls back to the server environment `OPENAI_API_KEY` (if set).

# Resume Checker API

FastAPI backend that analyzes resumes (PDF) and matches them against job descriptions using OpenAI via pydantic-ai agents. Provides structured JSON responses and scoring.

## Features

- **CV Analysis**: Upload and analyze PDF resumes to extract key skills, experience, and qualifications
- **Job Description Analysis**: Parse job descriptions to extract key requirements
- **Matching Score**: Get a detailed matching score between a CV and job description
- **Improvement Suggestions**: Receive actionable recommendations to improve your resume
- **Fast and Responsive**: In-process TTL cache with LRU keeps latency and cost low
- **Downloadable Results**: Download your analysis as JSON
- **Raw JSON Output**: Inspect the full structured analysis if desired

## Prerequisites

- Python 3.12 or higher
- pip (Python package installer)
- OpenAI API key (for AI-powered analysis) — per-user via Chrome extension or server-wide via environment

## Local Development

1. **Clone the repository**

   ```bash
   git clone https://github.com/yourusername/ResumeChecker.git
   cd ResumeChecker
   ```

2. **Create and activate a virtual environment** (recommended)

   ```bash
   # On macOS/Linux
   python3 -m venv venv
   source venv/bin/activate

   # On Windows
   python -m venv venv
   .\venv\Scripts\activate
   ```

3. **Install dependencies**

   ```bash
   pip install -e .
   ```

4. **Set up environment variables**
   You can run with a server-wide key (fallback) and configure allowed origins:
   ```bash
   # optional fallback if user does not provide a key from the extension
   OPENAI_API_KEY=sk-...
   # comma-separated list of allowed origins (API domain and extension origin)
   ALLOWED_ORIGINS=http://cv.kroete.io,chrome-extension://*
   ```

### Run the FastAPI server

```bash
uvicorn app:app --reload
```

The API will be available at `http://localhost:8000`.

In production, the API is accessible at `http://cv.kroete.io` (HTTP, no SSL currently).

## Usage

- Interact with the API using tools like [Swagger UI](http://localhost:8000/docs) or [Redoc](http://localhost:8000/redoc).
- You can also use `curl`, Postman, or integrate with your own frontend.

## API Endpoints

The backend provides the following RESTful endpoints:

- `POST /analyze-job-vacancy`: Analyze job description

  ```json
  {
    "vacancy_text": "Job description text here..."
  }
  ```

> Note: The backend does not store CVs on the server. Uploaded files are processed and deleted immediately after analysis; there are no endpoints to list, download, or delete server-stored CVs.

  **Returns:**  
  Structured job requirements as JSON, e.g.:

  ```json
  {
    "required_skills": {
      "technical": ["Python", "FastAPI"],
      "soft": ["Communication"]
    },
    "experience": {
      "minimum_years": 3,
      "industry": "Software",
      "type": "Full-time",
      "leadership": null
    },
    "qualifications": ["BSc Computer Science"],
    "responsibilities": ["Develop APIs"],
    "languages": ["English"],
    "seniority_level": "Mid"
  }
  ```

- `POST /analyze-cv`: Upload and analyze a CV (PDF)

  - Saves the uploaded CV to the `uploaded_cvs` directory
  - Only accepts PDF files
  - Returns the CV analysis
  
  **File Handling & Privacy:**  
  - CV PDFs are validated and processed in-memory/on-disk transiently
  - Files are deleted immediately after analysis (no server retention)
  - Only PDF files are accepted

  - Content-Type: multipart/form-data
  - File field: file (PDF)

  **Returns:**  
  Structured CV analysis as JSON, e.g.:

  ```json
  {
    "candidate_suitability": {
      "overall_fit_score": 8,
      "justification": "...",
      "strengths": ["..."],
      "gaps": ["..."]
    },
    "key_information": {
      "experience_summary": "...",
      "technical_skills": ["..."],
      "soft_skills": ["..."],
      "certifications": ["..."],
      "languages": ["..."],
      "responsibilities": ["..."]
    },
    "recommendations": {
      "tailoring": ["..."],
      "interview_focus": ["..."],
      "career_development": ["..."]
    }
  }
  ```

- `POST /score-cv-match`: Get matching score between CV and job requirements

  ```json
  {
    "cv_analysis": {
      /* CV analysis object */
    },
    "job_requirements": {
      /* Job requirements object */
    }
  }
  ```

  **Returns:**  
  Detailed match scoring as JSON, e.g.:

  ```json
  {
    "overall_match_score": 85,
    "overall_explanation": "...",
    "technical_skills_score": 90,
    "technical_skills_explanation": "...",
    "soft_skills_score": 80,
    "soft_skills_explanation": "...",
    "experience_score": 75,
    "experience_explanation": "...",
    "qualifications_score": 100,
    "qualifications_explanation": "...",
    "key_responsibilities_score": 70,
    "key_responsibilities_explanation": "...",
    "missing_requirements": ["..."],
    "improvement_suggestions": ["..."],
    "matched_skills": ["..."],
    "matched_qualifications": ["..."],
    "matched_languages": ["..."]
  }
  ```

## Project Structure

```
ResumeChecker/
├── .env                    # Environment variables
├── app.py                  # FastAPI backend and API endpoints
├── agents.py               # AI agent logic
├── models.py               # Pydantic models
├── prompts.py              # AI prompt templates
├── pyproject.toml          # Project dependencies
├── Dockerfile               # Production image
├── docker-compose.yml       # App + Caddy reverse proxy
├── Caddyfile                # TLS and reverse proxy config (set your domain)
├── uploaded_cvs/           # Directory for storing uploaded CVs
│   └── *.pdf              # Uploaded CV files
└── README.md               # This file
```

## Customization

- **Prompts:**  
  Prompts are designed for robust, structured JSON output compatible with Pydantic and FastAPI. You can further customize them in `prompts.py`.
  Note: The CV analysis prompt intentionally analyzes the CV on its own merits (without job requirements context). The comparison against job requirements happens later in the matching/score step.

- **Models:**  
  Models are now more granular and robust, supporting nested structures for skills, experience, and recommendations. See `models.py` for details.

## Troubleshooting

- **API Connection Errors:**  
  Ensure the FastAPI server is running and accessible at the correct URL.

- **CORS/Origin Errors:**  
  Set `ALLOWED_ORIGINS` (comma-separated) to include your API domain and Chrome extension origin (e.g., `chrome-extension://<extension-id>`). In dev, `chrome-extension://*` is acceptable.

- **Missing User Key:**  
  The extension must be configured with the user's OpenAI API key; otherwise the server fallback key will be used (if provided).

- **Missing Dependencies:**  
  Run `pip install -e .` to ensure all dependencies are installed.

- **PDF Parsing Issues:**  
  Ensure the uploaded file is a valid PDF.

## Production Deployment (Docker + Caddy)

This repo includes `docker-compose.yml` and a hardened `Caddyfile` for TLS termination and reverse proxy.

1) Set environment in `.env` or your secrets store:

```
OPENAI_API_KEY=sk-...                 # Optional server fallback
LOGFIRE_API_KEY=lfk_...               # Optional observability
LOGFIRE_PROJECT=your-project          # Optional
ALLOWED_ORIGINS=http://cv.kroete.io,chrome-extension://<id>
DOMAIN=cv.kroete.io                   # When enabling HTTPS via Caddy later
MAX_UPLOAD_MB=10                      # Max PDF size in MB (default 10)
GUNICORN_WORKERS=2                    # Optional tuning
GUNICORN_THREADS=1                    # Optional tuning
GUNICORN_TIMEOUT=60                   # Optional tuning
GUNICORN_KEEPALIVE=5                  # Optional tuning
```

2) Start:

```bash
docker compose up -d --build
```

- Caddy serves HTTPS at `https://$DOMAIN` and proxies to the app at `app:8000`.
- Healthchecks: app `/healthz`, Caddy HTTP 80.

Notes:
- Set `ALLOWED_ORIGINS` to include your prod domain and the Chrome extension origin.
- `uploaded_cvs/` is mounted as a volume to persist files across restarts.

If you are not using Caddy/HTTPS yet, you can serve directly over HTTP at `http://cv.kroete.io` and set `ALLOWED_ORIGINS` accordingly.

## SSL Migration (HTTP -> HTTPS)

When you're ready to enable HTTPS for `cv.kroete.io`, follow these steps:

1) Backend CORS
- File: `backend/app.py`
- Change default allowed origins to use HTTPS:
  - From `http://cv.kroete.io` to `https://cv.kroete.io`
- Or set env var at runtime:
  - `ALLOWED_ORIGINS=https://cv.kroete.io,chrome-extension://<extension-id>`

2) Chrome Extension
- File: `chrome-extension/js/api.js`
  - Update default base URL: `let API_BASE_URL = 'https://cv.kroete.io'`
- File: `chrome-extension/js/options.js`
  - Update default base URL fallback in Options
- File: `chrome-extension/manifest.json`
  - In `content_security_policy.extension_pages.connect-src`, replace `http://cv.kroete.io` with `https://cv.kroete.io`
  - In `host_permissions`, replace `http://cv.kroete.io/*` with `https://cv.kroete.io/*`
- Reload the extension from `chrome://extensions` after changes

3) Reverse Proxy (Caddy)
- File: `backend/Caddyfile`
  - Set `DOMAIN=cv.kroete.io` (env) and ensure ports 80/443 are open
  - Caddy will obtain certificates automatically and redirect HTTP->HTTPS

4) Testing
- Verify: `curl -I https://cv.kroete.io/healthz`
- Run e2e tests (they mock network calls, no change required)

5) Security headers (optional but recommended)
- Keep Caddy’s security headers (HSTS, etc.) enabled once HTTPS is live

## Contributing

Contributions are welcome! Please fork the repository and submit a pull request with your changes.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Built with [FastAPI](https://fastapi.tiangolo.com/)
- Powered by OpenAI's GPT models
- Icons by [Material Design Icons](https://material.io/resources/icons/)
