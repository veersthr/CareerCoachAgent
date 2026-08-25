"""FastAPI backend — wraps graph.py + orchestrator.py + pdf_parser.py.

Endpoints:
  POST /roadmap/text  — JD as raw text -> runs the pipeline -> report + state
  POST /roadmap/pdf   — JD as PDF upload -> pdf_parser.py -> pipeline -> report + state
  GET  /session/{id}  — re-fetch a previously saved session by id (no rerun)

CORS is enabled for the React frontend (frontend/) to call this directly.
"""

import uuid

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from config import settings
from graph import graph
from orchestrator import load_session, run_orchestrator
from pdf_parser import PDFParseError, extract_text_from_pdf

app = FastAPI(title="AI Career Coach", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # React dev server; tighten to a specific origin in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class JDTextRequest(BaseModel):
    jd_text: str


class RoadmapResponse(BaseModel):
    session_id: str
    report_markdown: str
    state: dict


def _run_pipeline(jd_text: str) -> RoadmapResponse:
    if not jd_text or not jd_text.strip():
        raise HTTPException(status_code=400, detail="jd_text must not be empty")

    thread_id = uuid.uuid4().hex
    invoke_config = {"configurable": {"thread_id": thread_id}}
    try:
        final_state = graph.invoke(
            {"raw_jd_text": jd_text, "agent_logs": [], "retry_count": 0},
            config=invoke_config,
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"pipeline failed: {exc}") from exc

    result = run_orchestrator(final_state)
    return RoadmapResponse(**result)


@app.post("/roadmap/text", response_model=RoadmapResponse)
def roadmap_from_text(payload: JDTextRequest) -> RoadmapResponse:
    return _run_pipeline(payload.jd_text)


@app.post("/roadmap/pdf", response_model=RoadmapResponse)
async def roadmap_from_pdf(file: UploadFile = File(...)) -> RoadmapResponse:
    pdf_bytes = await file.read()
    try:
        jd_text = extract_text_from_pdf(pdf_bytes)
    except PDFParseError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _run_pipeline(jd_text)


@app.get("/session/{session_id}")
def get_session(session_id: str) -> dict:
    session = load_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="session not found")
    return session


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=settings.api_host, port=settings.api_port)
