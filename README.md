# AI Career Copilot

> **Status: Work in progress / paused.** This project is not feature-complete or production-ready. Core architecture, agent pipeline, and UI scaffolding are in place, but several pieces are unfinished or untested end-to-end. Sharing as-is to show the approach and design decisions.

A multi-agent AI platform for job search automation, ATS optimization, and interview preparation. Built with LangGraph, Ollama (local LLMs), Qdrant, FastAPI, and Next.js.

---

## Architecture

```
Resume Upload → Parse → Job Discovery → ATS Optimize → Validate → Application Readiness
    ↓                                                                        ↓
Candidate Profile                                             Human Approval (HITL)
                                                                             ↓
                                                         Interview Intel → Interview Coach
```

### Tech Stack

| Layer | Technology |
|-------|-----------|
| LLM | Ollama (llama3.2, local, no API cost) |
| Embeddings | Ollama nomic-embed-text (768-dim) + sentence-transformers fallback |
| Vector DB | Qdrant (self-hosted Docker) |
| Orchestration | LangGraph 0.2 with SQLite checkpointing |
| Backend | FastAPI + WebSocket streaming |
| Frontend | Next.js 14 App Router + Tailwind CSS |
| Job Data | JSearch RapidAPI + 8 built-in mock jobs |
| Containers | Docker Compose |

---

## Quick Start (Docker)

### Prerequisites
- Docker + Docker Compose
- 8 GB RAM (16 GB recommended for GPU)
- NVIDIA GPU optional but recommended for Ollama

### 1. Clone and configure

```bash
git clone <your-repo>
cd ai-career-copilot
cp .env.example .env
```

Edit `.env`:
```env
# Required for real job data (optional — mock jobs work out of the box)
JSEARCH_API_KEY=your_rapidapi_key_here

# Set to false to use real JSearch API
USE_MOCK_JOBS=true

# Generate a secret key
SECRET_KEY=your-secret-key-here
```

### 2. Start all services

```bash
docker-compose up -d
```

This starts:
- **Qdrant** vector DB on port 6333
- **Ollama** LLM server on port 11434 (pulls llama3.2 + nomic-embed-text automatically)
- **FastAPI backend** on port 8000
- **Next.js frontend** on port 3000

### 3. Open the app

Navigate to **http://localhost:3000**

> ⚠️ First startup: Ollama model pull takes 5–10 minutes (llama3.2 ~2 GB). Monitor with:
> ```bash
> docker-compose logs -f ollama-init
> ```

---

## Manual Setup (No Docker)

### Backend

```bash
# Requirements: Python 3.11+, Ollama installed locally

cd backend

# Install dependencies
pip install -r requirements.txt

# Pull Ollama models
ollama pull llama3.2
ollama pull nomic-embed-text

# Start Qdrant (Docker required for this)
docker run -d -p 6333:6333 qdrant/qdrant:v1.9.0

# Configure environment
cp ../.env.example .env
# Edit .env with your settings

# Run backend
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### Frontend

```bash
cd frontend

# Install dependencies
npm install

# Configure environment
echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > .env.local
echo "NEXT_PUBLIC_WS_URL=ws://localhost:8000" >> .env.local

# Run development server
npm run dev
```

Open **http://localhost:3000**

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama server URL |
| `OLLAMA_MODEL` | `llama3.2` | LLM model for reasoning |
| `OLLAMA_EMBED_MODEL` | `nomic-embed-text` | Embedding model |
| `QDRANT_URL` | `http://localhost:6333` | Qdrant vector DB URL |
| `QDRANT_API_KEY` | _(empty)_ | Qdrant API key (leave empty for local) |
| `JSEARCH_API_KEY` | _(empty)_ | RapidAPI key for JSearch |
| `JSEARCH_HOST` | `jsearch.p.rapidapi.com` | JSearch API host |
| `USE_MOCK_JOBS` | `true` | Use built-in mock jobs (no API key needed) |
| `DATABASE_URL` | `sqlite:///./career_copilot.db` | SQLite path for LangGraph checkpointing |
| `SECRET_KEY` | `dev-secret-key` | JWT signing key (change in production) |
| `ATS_MIN_MATCH_SCORE` | `40` | Minimum score to show a job (0–100) |
| `ATS_TARGET_SCORE_LOW` | `80` | Minimum score to mark as "apply-ready" |
| `ATS_TARGET_SCORE_HIGH` | `95` | Optimization ceiling target |
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` | Backend API URL (frontend) |
| `NEXT_PUBLIC_WS_URL` | `ws://localhost:8000` | WebSocket URL (frontend) |

---

## How to Use

### Step 1 — Upload Resume
Go to `/upload`, drag and drop your PDF/DOCX/TXT resume. Enter job keywords (e.g. "Senior Software Engineer") and optionally a location. Click **Start AI Career Analysis**.

### Step 2 — Job Matches (`/jobs`)
The pipeline discovers, scores, and ranks jobs by ATS compatibility. Once the Application Readiness agent completes, a **Human Approval** banner appears — select the jobs you want to pursue and click **Approve**.

### Step 3 — ATS Optimization (`/optimize`)
View AI-rewritten summaries, bullet points, and cover letters for each job. The optimizer rewrites your resume to target 85–95 ATS score without fabricating experience. Click **Re-optimize** to run again.

### Step 4 — Validation (`/validate`)
Review keyword coverage, formatting checks, missing skills, and recommendations per job.

### Step 5 — Interview Prep (`/interview`)
For approved jobs, get 20 AI-generated interview questions with model answers (STAR format), company research, salary tips, and questions to ask the interviewer.

### Step 6 — Mock Interview (`/coach`)
Practice a live mock interview. The AI asks questions, evaluates your answers, gives feedback, and scores: Clarity, Technical Depth, Communication.

### Step 7 — Analytics (`/analytics`)
Dashboard showing jobs discovered, avg ATS score, application readiness, score distribution, and top missing keywords.

---

## API Reference

Base URL: `http://localhost:8000`

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/session/create` | Create a new pipeline session |
| `POST` | `/resume/upload?session_id=` | Upload and parse a resume |
| `POST` | `/pipeline/start?session_id=` | Start the multi-agent pipeline |
| `GET` | `/session/{id}/status` | Get full pipeline state |
| `POST` | `/pipeline/approve?session_id=` | Approve jobs for interview prep |
| `POST` | `/resume/reoptimize?session_id=&job_id=` | Re-run ATS optimizer |
| `GET` | `/interview/prep/{job_id}?session_id=` | Get interview prep for a job |
| `POST` | `/interview/start?session_id=&job_id=` | Start a mock interview |
| `POST` | `/interview/answer?session_id=&job_id=` | Submit an interview answer |
| `GET` | `/analytics/{session_id}` | Get analytics dashboard data |
| `GET` | `/health` | Health check (Ollama + Qdrant status) |
| `WS` | `/ws/{session_id}` | WebSocket for real-time agent events |

---

## Project Structure

```
ai-career-copilot/
├── docker-compose.yml
├── .env.example
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── main.py                    # FastAPI app + WebSocket + REST endpoints
│   ├── core/
│   │   ├── config.py              # Pydantic settings
│   │   ├── state.py               # LangGraph TypedDict state
│   │   ├── llm.py                 # Ollama LLM + system prompts
│   │   ├── vectorstore.py         # Qdrant client + collections
│   │   └── embeddings.py          # Ollama embeddings + fallback
│   ├── agents/
│   │   ├── orchestrator.py        # StateGraph + routing + human-in-the-loop
│   │   ├── resume_parser.py       # Agent 1: Parse resume → CandidateProfile
│   │   ├── job_discovery.py       # Agent 2: Discover + score jobs
│   │   ├── ats_optimizer.py       # Agent 3: Rewrite resume for ATS
│   │   ├── resume_validator.py    # Agent 4: Validate optimized resume
│   │   ├── application_agent.py   # Agent 5: Apply/Improve/Skip decisions
│   │   ├── interview_intel.py     # Agent 6: Generate 20 questions via RAG
│   │   └── interview_coach.py     # Agent 7: STAR evaluation + scoring
│   └── services/
│       ├── resume_service.py      # PDF/DOCX/TXT text extraction
│       ├── ats_service.py         # ATS scoring engine (no LLM)
│       └── job_service.py         # JSearch API + mock jobs
└── frontend/
    ├── Dockerfile
    ├── package.json
    ├── next.config.ts
    ├── tailwind.config.ts
    ├── app/
    │   ├── layout.tsx             # Root layout + providers
    │   ├── page.tsx               # Redirect → /upload
    │   └── (dashboard)/
    │       ├── layout.tsx         # Sidebar layout
    │       ├── upload/page.tsx    # Step 1: Resume upload
    │       ├── jobs/page.tsx      # Step 2: Job matches + approval
    │       ├── optimize/page.tsx  # Step 3: ATS optimization
    │       ├── validate/page.tsx  # Step 4: Validation
    │       ├── interview/page.tsx # Step 5: Interview questions
    │       ├── coach/page.tsx     # Step 6: Mock interview
    │       └── analytics/page.tsx # Step 7: Dashboard
    ├── components/
    │   ├── SessionContext.tsx     # Global session state + WebSocket
    │   ├── Sidebar.tsx            # Navigation sidebar
    │   ├── ATSScoreGauge.tsx      # SVG score ring + bar
    │   ├── JobCard.tsx            # Job listing card
    │   └── AgentLog.tsx           # Live agent message feed
    └── lib/
        ├── types.ts               # TypeScript interfaces
        ├── api.ts                 # API client functions
        └── utils.ts               # Formatting helpers
```

---

## ATS Scoring Algorithm

The ATS engine (`backend/services/ats_service.py`) scores resumes without LLM calls for speed:

| Component | Weight | Method |
|-----------|--------|--------|
| Keyword Match | 40% | TF-IDF extraction + regex matching; required keywords 2× weight |
| Skills Coverage | 20% | Intersection of 200+ tech/soft skill patterns |
| Experience Alignment | 20% | Years-of-experience extraction + delta scoring |
| Education Match | 10% | Degree hierarchy (PhD=4, Master=3, Bachelor=2) |
| Formatting | 10% | Word count, section presence, contact info |

**Job Match Score** = 60% semantic similarity (Qdrant cosine) + 40% keyword overlap

---

## Key Design Decisions

**Why Ollama?** Zero API cost, runs on local hardware, full privacy. Models are quantized (Q4) so a 4-bit llama3.2 runs on 8 GB RAM.

**Why LangGraph?** Provides stateful agent orchestration with built-in checkpointing (SQLite), human-in-the-loop via `interrupt_before`, and conditional routing between agents.

**Why separate ATS service?** Job scoring (filtering 100s of jobs) runs before LLM calls to avoid unnecessary inference. Only the top 10 jobs trigger LLM-based optimization.

**Human-in-the-loop:** The pipeline pauses at the `human_approval` node. The user selects which jobs to proceed with via the UI. LangGraph resumes from the checkpoint when `/pipeline/approve` is called.

---

## Troubleshooting

**Ollama model not found:**
```bash
docker-compose exec ollama ollama pull llama3.2
docker-compose exec ollama ollama pull nomic-embed-text
```

**Qdrant connection refused:**
```bash
docker-compose restart qdrant
curl http://localhost:6333/health
```

**Pipeline stuck on "running":**
```bash
# Check backend logs
docker-compose logs -f backend
# Reset session via UI "New Session" button or:
curl -X POST http://localhost:8000/session/create
```

**Frontend can't connect to backend:**
Ensure `NEXT_PUBLIC_API_URL` in `frontend/.env.local` matches your backend URL. For Docker, the default `http://localhost:8000` works.

---

## License

MIT
