# Resume Checker Application

A powerful AI-driven application that analyzes resumes and matches them against job descriptions. The application provides detailed insights into how well a candidate's qualifications match job requirements and offers improvement suggestions.

## Features

- **CV Analysis**: Upload and analyze PDF resumes to extract key skills, experience, and qualifications
- **Job Description Analysis**: Parse job descriptions to extract key requirements
- **Matching Score**: Get a detailed matching score between a CV and job description
- **Improvement Suggestions**: Receive actionable recommendations to improve your resume
- **User-Friendly Interface**: Intuitive web interface built with Streamlit
- **Fast and Responsive**: Caching and optimized feedback for fast user experience
- **Downloadable Results**: Download your analysis as JSON
- **Raw JSON Output**: Inspect the full structured analysis if desired

## Prerequisites

- Python 3.12 or higher
- pip (Python package installer)
- OpenAI API key (for AI-powered analysis)

## Installation

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
   Create a `.env` file in the project root and add your OpenAI API key:
   ```
   OPENAI_API_KEY=your_openai_api_key_here
   ```

## Running the Application

The application consists of a FastAPI backend:

### Backend API (FastAPI)

Run the FastAPI server in a terminal window:

```bash
uvicorn app:app --reload
```

The API will be available at `http://localhost:8000`

## Usage Guide

- Interact with the API using tools like [Swagger UI](http://localhost:8000/docs) or [Redoc](http://localhost:8000/redoc).
- You can also use `curl`, Postman, or integrate with your own frontend.

## API Endpoints

The backend provides the following RESTful endpoints:

- `GET /api/uploaded-cvs`: List all previously uploaded CVs

  **Returns:**  
  List of CV files with metadata:

  ```json
  [
    {
      "filename": "resume.pdf",
      "originalname": "resume.pdf",
      "size": 12345,
      "uploaded_at": "2025-06-15T10:30:00"
    }
  ]
  ```

- `POST /analyze-job-vacancy`: Analyze job description

  ```json
  {
    "vacancy_text": "Job description text here..."
  }
  ```

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
  
  **File Management:**  
  - Files are stored in the `uploaded_cvs` directory
  - Filenames are preserved from the uploaded file
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
├── uploaded_cvs/           # Directory for storing uploaded CVs
│   └── *.pdf              # Uploaded CV files
└── README.md               # This file
```

## Customization

- **Prompts:**  
  Prompts are designed for robust, structured JSON output compatible with Pydantic and FastAPI. You can further customize them in `prompts.py`.

- **Models:**  
  Models are now more granular and robust, supporting nested structures for skills, experience, and recommendations. See `models.py` for details.

## Troubleshooting

- **API Connection Errors:**  
  Ensure the FastAPI server is running and accessible at the correct URL.

- **Missing Dependencies:**  
  Run `pip install -e .` to ensure all dependencies are installed.

- **PDF Parsing Issues:**  
  Ensure the uploaded file is a valid PDF.

## Contributing

Contributions are welcome! Please fork the repository and submit a pull request with your changes.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Built with [FastAPI](https://fastapi.tiangolo.com/) and [Streamlit](https://streamlit.io/)
- Powered by OpenAI's GPT models
- Icons by [Material Design Icons](https://material.io/resources/icons/)
