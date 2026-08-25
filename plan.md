# Career Coach Multi-Agent System — Implementation Plan

## Context

The user is building an agentic AI Career Coach: a multi-agent LangGraph pipeline that
takes a Job Description and produces a 6-week learning roadmap with a Gantt chart,
resources, and mock-interview milestones. The repo is currently empty (greenfield).
The user explicitly wants this built **file-by-file, one file per prompt**, so this
plan's job is to lock down the file list, shared contracts, and build order *before*
any code is written, so that later single-file prompts don't drift or redefine shared
state inconsistently. This plan.md itself is the deliverable for this turn — no code
is written now.

Stack: LangGraph (orchestration + SqliteSaver checkpointing), swappable LLM provider
(Groq/Gemini/Ollama via `LLM_PROVIDER` env var), sentence-transformers + ChromaDB/FAISS
(local skill-taxonomy embeddings), PyMuPDF/pdfplumber + Tesseract OCR (PDF/JD ingestion),
SQLite (cache/checkpoints), FastAPI (backend), React (frontend).

Pipeline: `Extractor → Role Strategist → Scheduler → Enabler → Validator →`
`(pass → Orchestrator/END) / (fail, retries<2 → Extractor)`, retry cap 2.

---

## 1. File List + Responsibilities

### Core config & types
- `config.py` — loads env vars (`LLM_PROVIDER`, API keys, model names, thresholds, paths); central `Settings` object.
- `schemas.py` — all shared Pydantic/TypedDict models: `AgentState`, per-agent LLM I/O schemas, enums (domain, difficulty, resource type, phase). The single cross-file contract.
- `taxonomy.py` — the ~60-skill canonical taxonomy list/dict (skill name, domain, aliases) used by Extractor's canonicalization step.

### LLM & retrieval infra
- `llm_client.py` — provider-agnostic wrapper (`get_llm_client()` reads `LLM_PROVIDER`); exposes one function `call_llm_json(prompt, schema) -> dict` that forces strict JSON and wraps calls in `tenacity` retry.
- `embeddings.py` — sentence-transformers model loader + cosine-similarity skill-matching against `taxonomy.py`; wraps ChromaDB/FAISS local index build/query.
- `pdf_parser.py` — JD ingestion: PyMuPDF/pdfplumber text extraction with Tesseract OCR fallback for scanned PDFs; returns raw JD text.

### Agents (one file each, LangGraph node functions)
- `agent_extractor.py` — 1 LLM call: extract skills (skill/domain/frequency/difficulty) from JD text; canonicalizes each via `embeddings.py` (threshold 0.75, fallback to raw string). Writes `state.extracted_skills`, `state.raw_jd_text`.
- `agent_role_strategist.py` — deterministic keyword-based role detection (no LLM); 1 LLM call for `importance_score` (0–1) + phase bucket (Foundation/Intermediate/Expert) per skill; deterministic `readiness_score` formula in plain Python. Writes `state.detected_role`, `state.skills_with_importance`, `state.readiness_score`.
- `agent_scheduler.py` — 1 LLM call: 6-week plan content (weeks 1–2/3–4/5–6 mapped to phases); deterministic Gantt (Mermaid syntax) built in plain Python — aligns to next Monday, weekdays only. Writes `state.weekly_plan`, `state.gantt_mermaid`.
- `agent_enabler.py` — 2 LLM calls: (1) resource type (fixed enum) + topic + week per skill, (2) exactly 3 mock-interview milestones (1/phase, 5 questions each, hardcoded thresholds 30/50/65%). Writes `state.resources`, `state.milestones`.
- `agent_validator.py` — no LLM; ~9–10 rule-based checks; sets `state.validation_passed`, `state.validation_errors`, increments `state.retry_count`; forces `partial_output=True` after 2 failed retries.

### Orchestration
- `graph.py` — builds the LangGraph `StateGraph`: registers the 5 agent nodes, wires the conditional edge (Validator → Orchestrator/END on pass; Validator → Extractor on fail+retries<2), attaches `SqliteSaver` checkpointing, compiles the graph.
- `orchestrator.py` — post-graph step (not a graph node): assembles final Markdown report from `AgentState`, saves JSON state to disk under `outputs/{session_id}.json` (session_id generated per run), invoked by the API layer after `graph.invoke()` returns. `GET /session/{id}` reads this same file back.

### Interfaces
- `api.py` — FastAPI app, CORS-enabled for the React dev server. Endpoints:
  - `POST /roadmap/text` — accepts raw JD text (JSON body) → runs graph → returns final report + state.
  - `POST /roadmap/pdf` — accepts JD as PDF upload (multipart) → `pdf_parser.py` → runs graph → returns final report + state.
  - `GET /session/{id}` — fetches a previously-run session's stored result (report, state, `agent_logs`) by session id, for re-viewing without rerunning the graph.
- `frontend/` — React app (JD input via text/PDF upload; tabbed views for roadmap report, weekly timeline, agent logs, and Mermaid Gantt chart), talks to `api.py` over REST. Internal structure:
  - `frontend/package.json` — deps: React, a bundler/dev server (Vite), `mermaid` (client-side Gantt rendering), a small fetch/axios wrapper.
  - `frontend/src/api/client.js` — REST client: `submitJdText()`, `submitJdPdf()`, `getSession(id)` — thin wrappers around the three FastAPI endpoints above.
  - `frontend/src/components/JdInput.jsx` — text/PDF upload form, calls the API client, holds `session_id` once a run completes.
  - `frontend/src/components/RoadmapTabs.jsx` — tab container switching between Report / Timeline / Agent Logs / Gantt views.
  - `frontend/src/components/GanttChart.jsx` — renders `gantt_mermaid` from state via `mermaid.js`.
  - `frontend/src/components/AgentLogs.jsx` — renders `agent_logs` list.
  - `frontend/src/App.jsx` — top-level layout wiring `JdInput` + `RoadmapTabs`.

### Project scaffolding
- `requirements.txt` — pinned free/OSS Python deps (backend).
- `.env.example` — documents `LLM_PROVIDER`, provider keys, model names, thresholds.
- `README.md` — setup/run instructions (only if user asks later; not built proactively).

---

## 2. Shared Interfaces / Types / Schemas (`schemas.py`)

This is the contract every agent file must import and respect — **one field, one writer**.

```python
class Skill(TypedDict):
    name: str                      # canonicalized (or raw fallback) skill name
    domain: str                    # e.g. "backend", "ml", "cloud"
    frequency: int                 # mentions in JD
    difficulty: float              # 0-1, from Extractor
    canonical: bool                # True if matched taxonomy >=0.75 cosine
    importance_score: float | None # 0-1, ONLY Role Strategist writes this
    phase: str | None              # "Foundation"|"Intermediate"|"Expert", ONLY Role Strategist writes

class Resource(TypedDict):
    skill: str
    resource_type: str  # enum: official_docs|video_course|practice_platform|book_chapter|project_idea
    topic: str
    week: int            # 1-6

class Milestone(TypedDict):
    phase: str            # Foundation|Intermediate|Expert
    questions: list[str]  # exactly 5
    pass_threshold: float # hardcoded 0.30/0.50/0.65 by phase

class AgentState(TypedDict):
    # input
    raw_jd_text: str
    # Extractor-owned
    extracted_skills: list[Skill]
    # Role Strategist-owned
    detected_role: str
    skills_with_importance: list[Skill]   # supersedes extracted_skills downstream
    readiness_score: float                # 0-100
    # Scheduler-owned
    weekly_plan: dict[int, list[str]]     # week -> skill names
    gantt_mermaid: str
    # Enabler-owned
    resources: list[Resource]
    milestones: list[Milestone]           # exactly 3
    # Validator-owned
    validation_passed: bool
    validation_errors: list[str]
    retry_count: int
    partial_output: bool
    # cross-cutting
    agent_logs: list[str]                 # every agent appends one line
```

LLM-call I/O schemas (also in `schemas.py`, one per LLM call, used to validate `json.loads()` output before it's written into `AgentState`):
`ExtractorLLMOutput`, `RoleStrategistLLMOutput`, `SchedulerLLMOutput`, `EnablerResourceLLMOutput`, `EnablerMilestoneLLMOutput`.

Enums (also here): `Domain`, `Phase` (Foundation/Intermediate/Expert), `ResourceType` (5-value fixed enum).

**Rule enforced across all agent files:** each node function only reads upstream fields and writes its own — no agent mutates a field it doesn't own. `agent_logs.append(...)` is the one exception every agent does.

---

## 3. Build Order (dependencies)

```
1. config.py              (no deps)
2. schemas.py              (no deps)
3. taxonomy.py             (no deps)
4. llm_client.py            → config.py, schemas.py
5. embeddings.py            → config.py, taxonomy.py, schemas.py
6. pdf_parser.py            → config.py
7. agent_extractor.py       → schemas.py, llm_client.py, embeddings.py
8. agent_role_strategist.py → schemas.py, llm_client.py
9. agent_scheduler.py       → schemas.py, llm_client.py
10. agent_enabler.py        → schemas.py, llm_client.py
11. agent_validator.py      → schemas.py  (no LLM)
12. graph.py                → schemas.py + all agent_*.py (registers nodes, conditional edges, SqliteSaver)
13. orchestrator.py         → schemas.py, graph.py (consumes final AgentState)
14. api.py                  → graph.py, orchestrator.py, pdf_parser.py
15. frontend/               → api.py (REST calls only; no Python import)
16. requirements.txt / .env.example — written alongside step 1, refined as later files reveal deps
```

Rationale: `schemas.py` is written second (right after `config.py`) and frozen early
because every other file imports from it — changing it later would ripple through
every agent file. `llm_client.py` and `embeddings.py` are infra used by multiple
agents and must exist before any agent file. Agents are built in pipeline order
(Extractor → Validator) so each can be sanity-checked against the previous one's
output shape. `graph.py` is the first file that touches all 5 agents, so it must come
after all of them. `orchestrator.py` depends on the compiled graph's final state shape.
`api.py` is built once the graph is stable, since its 3 endpoints just wrap
`graph.invoke()` + `orchestrator.py`. `frontend/` is last — it only talks to `api.py`
over REST, no shared Python types, so it's decoupled from everything upstream and can
be built/iterated independently once the 3 endpoints are stable.

---

## Verification (per file, once code starts)

- After `schemas.py`: `python -c "import schemas"` — confirms no syntax/type errors.
- After each `agent_*.py`: unit-test the node function with a hand-built partial `AgentState`, assert it only sets its owned fields and appends to `agent_logs`.
- After `graph.py`: run the full graph on one sample JD text, confirm the retry loop triggers when a validator check is deliberately broken, confirm it exits after 2 retries with `partial_output=True`.
- After `api.py`: hit `/roadmap/text`, `/roadmap/pdf`, `/session/{id}` with a real JD and confirm responses match `AgentState`/report shape.
- After `frontend/`: manual end-to-end run in the browser — paste/upload a real JD, confirm the Report/Timeline/Agent Logs/Gantt tabs all render correctly from the API response.
