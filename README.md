# AI Career Coach

An agentic system that takes a job description (text or PDF) and generates a 6-week
personalized learning roadmap: prioritized skills, a week-by-week plan, a Gantt chart,
learning resources, and mock-interview milestones.

Built entirely on free/open-source components — no paid services required beyond
whichever LLM API key you choose to use (Groq's free tier works out of the box).

## Architecture

Five agents run in a LangGraph pipeline with one conditional retry loop, followed by a
non-agent orchestration step:

```
Extractor -> Role Strategist -> Scheduler -> Enabler -> Validator
                                                  |
                              pass ---------------+--------------- fail (retries < 2)
                              |                                          |
                              v                                          v
                         Orchestrator                                Extractor (retry)
                     (report + save session)
```

- **Extractor** — 1 LLM call to pull skills from the JD, canonicalized against a ~60-skill
  taxonomy via local sentence-transformer embeddings (ChromaDB/FAISS).
- **Role Strategist** — deterministic keyword-based role detection, 1 LLM call to score
  skill importance and bucket into Foundation/Intermediate/Expert, deterministic
  readiness-score formula.
- **Scheduler** — 1 LLM call to distribute skills across 6 weeks; the Gantt chart itself
  is built deterministically (aligned to the next Monday, weekdays only).
- **Enabler** — 2 LLM calls: learning resources per skill, and exactly 3 mock-interview
  milestones (one per phase, 5 questions each, hardcoded pass thresholds).
- **Validator** — no LLM, 10 rule-based checks. Fails route back to the Extractor
  (capped at 2 retries); after that it force-passes with `partial_output: true`.
- **Orchestrator** — assembles the Markdown report and persists the session to
  `outputs/{session_id}.json`.

Full design rationale and file-by-file responsibilities are in [`plan.md`](plan.md).

## Prerequisites

- Python 3.10+ (developed against 3.14)
- Node.js 18+ and npm
- An API key for at least one LLM provider: [Groq](https://console.groq.com) (free tier),
  Gemini, or a local [Ollama](https://ollama.com) install
- Optional, only needed for scanned/image-only PDFs: the Tesseract binary
  (`brew install tesseract` on macOS)

## Backend setup

```bash
python3 -m venv .venv
source .venv/bin/activate        # .venv\Scripts\activate on Windows
pip install -r requirements.txt

cp .env.example .env
```

Edit `.env`:

```
LLM_PROVIDER=groq
GROQ_API_KEY=your_key_here
```

`LLM_PROVIDER` also accepts `gemini` or `ollama` — set the matching `*_API_KEY` /
`*_MODEL` / `OLLAMA_BASE_URL` vars for whichever you choose. Everything else in
`.env.example` has a sensible default (leave blank to use it).

Run the backend:

```bash
uvicorn api:app --reload --port 8000
```

Check it's up: `curl http://localhost:8000/health` → `{"status":"ok"}`

### Endpoints

| Method | Path              | Body                          | Returns                              |
|--------|-------------------|--------------------------------|---------------------------------------|
| POST   | `/roadmap/text`    | `{"jd_text": "..."}`          | `{session_id, report_markdown, state}` |
| POST   | `/roadmap/pdf`     | multipart file upload (`file`) | `{session_id, report_markdown, state}` |
| GET    | `/session/{id}`   | —                              | previously saved session              |

## Frontend setup

```bash
cd frontend
npm install
cp .env.example .env    # defaults to http://localhost:8000, matching the backend above
npm run dev
```

Open the printed URL (default `http://localhost:5173`). Paste a job description or
upload a PDF, then review the generated roadmap across the Report / Timeline / Agent
Logs / Gantt tabs.

## Deploying (Vercel frontend + Render backend)

The backend uses heavy local ML deps (`sentence-transformers`, `chromadb`, `faiss-cpu`),
a local SQLite checkpoint file, and optionally the Tesseract binary — none of which fit
Vercel's serverless model. Split the deploy instead: frontend on Vercel (static site),
backend on Render (a real long-running container with a persistent disk).

### Backend on Render

1. Push this repo to GitHub (already done if you're reading this from the repo).
2. In the Render dashboard: **New > Blueprint**, point it at this repo. Render reads
   [`render.yaml`](render.yaml) and creates a Docker-based web service that installs
   Tesseract, mounts a 1GB persistent disk at `/app/data` (so the Chroma index and
   SQLite checkpoints survive restarts), and health-checks `/health`.
   - Alternatively, without the blueprint: **New > Web Service**, runtime **Docker**,
     it'll pick up the repo's [`Dockerfile`](Dockerfile) automatically.
3. Set the env vars Render prompts for (marked `sync: false` in `render.yaml`):
   - `GROQ_API_KEY` (or switch `LLM_PROVIDER`/keys to Gemini instead)
   - `ALLOWED_ORIGINS` — leave blank until you have the Vercel URL from the next step,
     then come back and set it to `https://<your-vercel-app>.vercel.app` (comma-separate
     multiple origins if needed) and redeploy.
4. Pick at least the **Standard** plan (or similar ≥2GB RAM) — `sentence-transformers`
   + `chromadb` won't run reliably on a 512MB free instance.
5. Once live, confirm `https://<your-render-app>.onrender.com/health` returns
   `{"status":"ok"}`.

### Frontend on Vercel

1. In the Vercel dashboard: **Add New > Project**, import this repo.
2. Set **Root Directory** to `frontend` (this is a monorepo — the frontend isn't at the
   repo root). Vercel auto-detects the Vite framework preset from there.
3. Add an environment variable `VITE_API_BASE_URL` = `https://<your-render-app>.onrender.com`.
4. Deploy. Then go back to Render and set `ALLOWED_ORIGINS` to the resulting Vercel URL
   (step 3 above) so CORS allows it.

Render's free-tier instances spin down when idle and take ~30-60s to wake on the next
request — the frontend's staged loader will just sit on the first stage a while longer
on a cold start; that's expected, not a bug.

## Project structure

```
config.py                 central Settings (env vars)
schemas.py                shared AgentState + LLM I/O schemas (the cross-file contract)
taxonomy.py                ~60-skill canonical taxonomy
llm_client.py              provider-agnostic LLM wrapper (LLM_PROVIDER swap point)
embeddings.py               skill canonicalization via local embeddings
pdf_parser.py               PDF text extraction + Tesseract OCR fallback
agent_extractor.py          } 
agent_role_strategist.py    }
agent_scheduler.py          } the 5 pipeline agents
agent_enabler.py            }
agent_validator.py          }
graph.py                    LangGraph wiring + SqliteSaver checkpointing
orchestrator.py             report assembly + session persistence
api.py                      FastAPI app
frontend/                   React app (Vite)
plan.md                     full design doc
```

## Notes

- Swapping LLM providers is a single env var (`LLM_PROVIDER`) — no code changes.
- Provider model catalogs change over time; if you see a `model_not_found` error, check
  your provider's current model list and update `*_MODEL` in `.env` accordingly.
- `data/` (embeddings index, SQLite checkpoints) and `outputs/` (saved sessions) are
  gitignored and created automatically on first run.
