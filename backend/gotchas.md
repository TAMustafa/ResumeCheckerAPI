# Gotchas

- API docs mention a Streamlit UI, but the repository only contains a FastAPI backend; Streamlit is listed as a dependency but unused. Consider removing or adding the UI to avoid confusion.
- CORS is wide open (`allow_origins=["*"]`) in `app.py` for development. Restrict in production.
- Both `app.py` and `agents.py` call `load_dotenv()`. This is harmless but redundant; keeping it is acceptable, or centralize once.
- Large PDFs will be fully read into memory in `analyze_cv()`. For very large files, consider size limits or streaming validation before hashing.
- Cache is per-process in-memory. It does not share across replicas and will clear on process restart. TTL default 20 minutes.
- LLM calls have timeouts (60–90s). Tune if you see timeouts on complex inputs.
