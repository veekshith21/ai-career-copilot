"""
AI Career Copilot — FastAPI Backend

Endpoints:
  POST   /api/sessions                      → create session
  POST   /api/sessions/{id}/resume          → upload resume (PDF/DOCX/TXT)
  POST   /api/sessions/{id}/run             → start full agent pipeline
  GET    /api/sessions/{id}/status          → poll pipeline state
  POST   /api/sessions/{id}/approve         → human-in-the-loop approval
  GET    /api/sessions/{id}/jobs            → get discovered + scored jobs
  GET    /api/sessions/{id}/optimize/{jid}  → get ATS optimization for a job
  GET    /api/sessions/{id}/applications    → get application statuses
  POST   /api/sessions/{id}/interview/{jid}/start    → start mock interview
  POST   /api/sessions/{id}/interview/{jid}/answer   → submit answer, get feedback
  GET    /api/sessions/{id}/analytics       → get analytics dashboard data
  WS     /ws/{session_id}                   → real-time agent progress stream
"""
from __future__ import annotations
import asyncio
import json
import os
import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Any

import aiofiles
import structlog
from fastapi import (
    FastAPI, File, Form, HTTPException, UploadFile, WebSocket,
    WebSocketDisconnect, BackgroundTasks,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from core.config import get_settings
from core.vectorstore import init_collections
from core.state import CareerCopilotState
from services.resume_service import extract_text_from_file, validate_resume_text
from agents.orchestrator import compile_graph
from agents.interview_coach import (
    start_interview, evaluate_answer, compute_session_score
)

logger = structlog.get_logger()
settings = get_settings()

# In-memory session store (use Redis in production)
_sessions: dict[str, CareerCopilotState] = {}
_ws_clients: dict[str, list[WebSocket]] = {}


# ─── Startup / Shutdown ───────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("startup.begin")
    Path("./uploads").mkdir(exist_ok=True)
    Path("./data").mkdir(exist_ok=True)
    try:
        init_collections()
        logger.info("startup.qdrant_ready")
    except Exception as e:
        logger.warning("startup.qdrant_failed", error=str(e))
    yield
    logger.info("shutdown.complete")


app = FastAPI(
    title="AI Career Copilot",
    description="Multi-agent job search and resume optimization platform",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Shared Graph Instance ────────────────────────────────────────────────────
# MUST be a singleton so run_pipeline and _resume_after_approval share the same
# MemorySaver — otherwise resume creates an empty checkpointer and restarts
# the whole graph from scratch instead of continuing from human_approval.
_graph = compile_graph()


# ─── Pydantic Request / Response Models ──────────────────────────────────────

class CreateSessionRequest(BaseModel):
    search_query: str = ""
    search_location: str = "United States"
    target_roles: list[str] = []
    linkedin_url: str | None = None


class ApproveRequest(BaseModel):
    approved_job_ids: list[str]


class InterviewAnswerRequest(BaseModel):
    question: str
    answer: str
    question_idx: int


# ─── WebSocket Manager ────────────────────────────────────────────────────────

async def broadcast(session_id: str, message: dict) -> None:
    """Send a message to all WebSocket clients for a session."""
    clients = _ws_clients.get(session_id, [])
    dead = []
    for ws in clients:
        try:
            await ws.send_json(message)
        except Exception:
            dead.append(ws)
    for ws in dead:
        clients.remove(ws)


# ─── Agent Pipeline Runner ────────────────────────────────────────────────────

async def run_pipeline(session_id: str, initial_state: CareerCopilotState) -> None:
    """Run the full LangGraph agent pipeline in the background."""
    graph = _graph  # Use shared singleton so checkpoints persist for resume
    config = {"configurable": {"thread_id": session_id}}

    await broadcast(session_id, {"type": "pipeline_start", "session_id": session_id})

    try:
        async for event in graph.astream(initial_state, config=config, stream_mode="values"):
            messages = event.get("agent_messages", [])
            current_agent = event.get("current_agent", "")

            for msg in messages[-1:]:  # Only send latest message
                await broadcast(session_id, {
                    "type": "agent_update",
                    "agent": msg.get("agent", current_agent),
                    "message": msg.get("message", ""),
                    "level": msg.get("level", "info"),
                    "timestamp": msg.get("timestamp", ""),
                })

            # Update session state
            _sessions[session_id] = event

            # Check for human approval pause
            if event.get("pending_approval"):
                await broadcast(session_id, {
                    "type": "awaiting_approval",
                    "jobs": [
                        {"job_id": jid, "status": s["decision"], "score": s["ats_score"]}
                        for jid, s in event.get("application_statuses", {}).items()
                        if s["decision"] == "apply"
                    ],
                })
                break

        await broadcast(session_id, {
            "type": "pipeline_complete",
            "analytics": _build_analytics(session_id),
        })

    except Exception as e:
        logger.error("pipeline.error", session=session_id, error=str(e))
        await broadcast(session_id, {"type": "pipeline_error", "error": str(e)})


# ─── Routes ───────────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}


@app.post("/api/sessions")
async def create_session(req: CreateSessionRequest):
    session_id = str(uuid.uuid4())
    _sessions[session_id] = CareerCopilotState(
        session_id=session_id,
        user_id=None,
        resume_raw_text="",
        resume_file_path="",
        linkedin_url=req.linkedin_url,
        candidate_profile=None,
        resume_embedding_id=None,
        search_query=req.search_query,
        search_location=req.search_location,
        target_roles=req.target_roles,
        discovered_jobs=[],
        filtered_jobs=[],
        ats_scores={},
        optimized_resumes={},
        validation_results={},
        application_statuses={},
        interview_preps={},
        mock_sessions={},
        current_agent="",
        active_job_id=None,
        agent_messages=[],
        error=None,
        pending_approval=False,
        approved_job_ids=[],
        jobs_discovered_count=0,
        jobs_above_threshold=0,
        optimizations_run=0,
        applications_ready=0,
        interviews_completed=0,
    )
    logger.info("session.created", session_id=session_id)
    return {"session_id": session_id}


@app.post("/api/sessions/{session_id}/resume")
async def upload_resume(
    session_id: str,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    auto_run: bool = Form(False),
):
    if session_id not in _sessions:
        raise HTTPException(404, "Session not found")

    # Validate file type
    allowed = {".pdf", ".docx", ".doc", ".txt"}
    suffix = Path(file.filename or "resume.pdf").suffix.lower()
    if suffix not in allowed:
        raise HTTPException(400, f"File type {suffix} not supported. Use PDF, DOCX, or TXT.")

    # Check size
    max_bytes = settings.max_upload_size_mb * 1024 * 1024
    content = await file.read()
    if len(content) > max_bytes:
        raise HTTPException(413, f"File too large. Max {settings.max_upload_size_mb}MB.")

    # Save to disk
    file_path = f"./uploads/{session_id}{suffix}"
    async with aiofiles.open(file_path, "wb") as f:
        await f.write(content)

    # Extract text
    try:
        raw_text = extract_text_from_file(file_path)
    except Exception as e:
        raise HTTPException(422, f"Failed to extract text from resume: {e}")

    valid, msg = validate_resume_text(raw_text)
    if not valid:
        raise HTTPException(422, msg)

    _sessions[session_id]["resume_raw_text"] = raw_text
    _sessions[session_id]["resume_file_path"] = file_path

    result = {
        "message": "Resume uploaded and text extracted successfully.",
        "word_count": len(raw_text.split()),
        "file_path": file_path,
    }

    # Optionally trigger the full pipeline immediately
    if auto_run:
        background_tasks.add_task(run_pipeline, session_id, _sessions[session_id].copy())
        result["pipeline_started"] = True

    return result


@app.post("/api/sessions/{session_id}/run")
async def run_session(session_id: str, background_tasks: BackgroundTasks):
    """Start the full agent pipeline for a session."""
    if session_id not in _sessions:
        raise HTTPException(404, "Session not found")
    state = _sessions[session_id]
    if not state.get("resume_raw_text"):
        raise HTTPException(400, "Upload a resume before running the pipeline.")

    background_tasks.add_task(run_pipeline, session_id, state.copy())
    return {"message": "Pipeline started.", "session_id": session_id}


@app.get("/api/sessions/{session_id}/status")
async def get_status(session_id: str):
    """Poll current session state — for non-WebSocket clients."""
    if session_id not in _sessions:
        raise HTTPException(404, "Session not found")
    state = _sessions[session_id]

    # Determine pipeline status string
    if state.get("error"):
        pipeline_status = "failed"
    elif state.get("pending_approval"):
        pipeline_status = "paused"
    elif state.get("pipeline_complete"):
        pipeline_status = "completed"
    elif state.get("current_agent") and state.get("current_agent") != "":
        pipeline_status = "running"
    else:
        pipeline_status = "idle"

    def _normalize_job(job: dict) -> dict:
        """Map backend job field names to frontend TypeScript type names."""
        return {
            "job_id": job.get("job_id", ""),
            "title": job.get("title", ""),
            "company": job.get("company", ""),
            "location": job.get("location", ""),
            "employment_type": job.get("employment_type") or job.get("job_type", ""),
            "experience_level": job.get("experience_level", ""),
            "description": job.get("description", ""),
            "requirements": job.get("requirements") or job.get("required_skills", []),
            "preferred_qualifications": job.get("preferred_qualifications") or job.get("preferred_skills", []),
            "technical_skills_required": job.get("technical_skills_required") or job.get("required_skills", []),
            "salary_min": job.get("salary_min"),
            "salary_max": job.get("salary_max"),
            "salary_currency": job.get("salary_currency", "USD"),
            "remote_friendly": job.get("remote_friendly", False),
            "posted_date": job.get("posted_date", ""),
            "application_url": job.get("application_url") or job.get("apply_url", ""),
            "source": job.get("source", ""),
            "match_score": job.get("match_score", 0),
        }

    def _normalize_ats(ats: dict) -> dict:
        """Map backend ATS field names to frontend TypeScript ATSBreakdown type."""
        return {
            "total_score": ats.get("total_score", 0),
            "keyword_score": ats.get("keyword_score") or ats.get("keyword_match_pct", 0),
            "skills_coverage_score": ats.get("skills_coverage_score") or ats.get("skills_coverage", 0),
            "experience_alignment_score": ats.get("experience_alignment_score") or ats.get("experience_alignment", 0),
            "education_match_score": ats.get("education_match_score") or ats.get("education_match", 0),
            "formatting_score": ats.get("formatting_score", 0),
            "matched_keywords": ats.get("matched_keywords") or ats.get("present_keywords", []),
            "missing_keywords": ats.get("missing_keywords", []),
            "matched_skills": ats.get("matched_skills", []),
            "missing_skills": ats.get("missing_skills", []),
            "experience_years_required": ats.get("experience_years_required"),
            "experience_years_candidate": ats.get("experience_years_candidate", 0),
            "recommendations": ats.get("recommendations", []),
        }

    normalized_jobs = [_normalize_job(j) for j in state.get("filtered_jobs", [])]
    raw_ats = state.get("ats_scores", {})
    normalized_ats = {k: _normalize_ats(v) for k, v in raw_ats.items()}

    return {
        "session_id": session_id,
        "status": pipeline_status,
        "current_agent": state.get("current_agent", ""),
        "progress": state.get("progress", 0),
        "pending_approval": state.get("pending_approval", False),
        "approved_job_ids": state.get("approved_job_ids", []),
        "error": state.get("error"),
        "candidate_profile": state.get("candidate_profile"),
        "discovered_jobs": [_normalize_job(j) for j in state.get("discovered_jobs", [])],
        "filtered_jobs": normalized_jobs,
        "ats_scores": normalized_ats,
        "optimized_resumes": state.get("optimized_resumes", {}),
        "validation_results": state.get("validation_results", {}),
        "application_statuses": state.get("application_statuses", {}),
        "interview_preps": state.get("interview_preps", {}),
        "mock_sessions": state.get("mock_sessions", {}),
        "agent_messages": state.get("agent_messages", []),
        "jobs_discovered": state.get("jobs_discovered_count", 0),
        "applications_ready": state.get("applications_ready", 0),
        "interviews_completed": state.get("interviews_completed", 0),
        "resume_versions": state.get("optimizations_run", 0),
        "analytics": _build_analytics(session_id),
    }


@app.post("/api/sessions/{session_id}/approve")
async def approve_applications(
    session_id: str,
    req: ApproveRequest,
    background_tasks: BackgroundTasks,
):
    """Human-in-the-loop: approve jobs for interview prep and submission."""
    if session_id not in _sessions:
        raise HTTPException(404, "Session not found")

    state = _sessions[session_id]
    state["approved_job_ids"] = req.approved_job_ids
    state["pending_approval"] = False

    # Resume the graph after human approval
    background_tasks.add_task(_resume_after_approval, session_id, state)
    return {"approved": req.approved_job_ids, "message": "Approval received. Resuming pipeline."}


async def _resume_after_approval(session_id: str, state: CareerCopilotState) -> None:
    """Resume the LangGraph graph from the human_approval interrupt."""
    graph = _graph  # Use shared singleton — checkpoint is still in memory
    config = {"configurable": {"thread_id": session_id}}
    try:
        # Resume from the last checkpoint (human_approval interrupt).
        # Pass the approved_job_ids as a state update so route_after_approval
        # sees them and routes to interview_intel instead of __end__.
        resume_input = {
            "approved_job_ids": state.get("approved_job_ids", []),
            "pending_approval": False,
        }
        async for event in graph.astream(resume_input, config=config, stream_mode="values"):
            _sessions[session_id] = event
            messages = event.get("agent_messages", [])
            for msg in messages[-1:]:
                await broadcast(session_id, {
                    "type": "agent_update",
                    "agent": msg.get("agent", ""),
                    "message": msg.get("message", ""),
                    "level": msg.get("level", "info"),
                    "timestamp": msg.get("timestamp", ""),
                })
        await broadcast(session_id, {"type": "pipeline_complete"})
    except Exception as e:
        logger.error("resume_pipeline.error", session=session_id, error=str(e))


@app.get("/api/sessions/{session_id}/profile")
async def get_profile(session_id: str):
    if session_id not in _sessions:
        raise HTTPException(404, "Session not found")
    return _sessions[session_id].get("candidate_profile") or {}


@app.get("/api/sessions/{session_id}/jobs")
async def get_jobs(session_id: str):
    if session_id not in _sessions:
        raise HTTPException(404, "Session not found")
    state = _sessions[session_id]
    jobs = state.get("filtered_jobs", [])
    ats = state.get("ats_scores", {})
    statuses = state.get("application_statuses", {})
    return {
        "jobs": [
            {
                **job,
                "ats_score": ats.get(job["job_id"], {}).get("total_score", 0),
                "decision": statuses.get(job["job_id"], {}).get("decision"),
            }
            for job in jobs
        ],
        "total": len(jobs),
    }


@app.get("/api/sessions/{session_id}/optimize/{job_id}")
async def get_optimization(session_id: str, job_id: str):
    if session_id not in _sessions:
        raise HTTPException(404, "Session not found")
    state = _sessions[session_id]
    opt = state.get("optimized_resumes", {}).get(job_id)
    val = state.get("validation_results", {}).get(job_id)
    if not opt and not val:
        raise HTTPException(404, "No optimization found for this job")
    return {"optimization": opt, "validation": val}


@app.get("/api/sessions/{session_id}/applications")
async def get_applications(session_id: str):
    if session_id not in _sessions:
        raise HTTPException(404, "Session not found")
    state = _sessions[session_id]
    return {
        "statuses": state.get("application_statuses", {}),
        "approved": state.get("approved_job_ids", []),
    }


@app.get("/api/sessions/{session_id}/interview/{job_id}")
async def get_interview_prep(session_id: str, job_id: str):
    if session_id not in _sessions:
        raise HTTPException(404, "Session not found")
    prep = _sessions[session_id].get("interview_preps", {}).get(job_id)
    if not prep:
        raise HTTPException(404, "Interview prep not yet generated for this job")
    return prep


@app.post("/api/sessions/{session_id}/interview/{job_id}/start")
async def start_mock_interview(session_id: str, job_id: str):
    """Initialize and start a mock interview session."""
    if session_id not in _sessions:
        raise HTTPException(404, "Session not found")
    state = _sessions[session_id]
    prep = state.get("interview_preps", {}).get(job_id)
    profile = state.get("candidate_profile")
    if not prep:
        raise HTTPException(404, "Run interview prep first via the main pipeline.")

    candidate_summary = (
        f"{profile['full_name'] if profile else 'Candidate'} — "
        f"{profile['total_years_experience'] if profile else 0}yr experience. "
        f"Skills: {', '.join((profile or {}).get('technical_skills', [])[:8])}"
    )

    result = await start_interview(
        job_id=job_id,
        company=prep["company"],
        role=prep["role"],
        candidate_summary=candidate_summary,
        questions=prep.get("top_questions", []),
    )

    # Initialize session in state
    state["mock_sessions"][job_id] = {
        "job_id": job_id,
        "turns": [{"role": "coach", "message": result["coach_message"], "timestamp": datetime.utcnow().isoformat(), "evaluation": None}],
        "current_question_idx": 0,
        "scores": {},
        "overall_score": 0.0,
        "feedback_summary": "",
        "completed": False,
    }
    return {"coach_message": result["coach_message"], "question_idx": 0}


@app.post("/api/sessions/{session_id}/interview/{job_id}/answer")
async def submit_interview_answer(session_id: str, job_id: str, req: InterviewAnswerRequest):
    """Submit a candidate answer and get coach feedback + next question."""
    if session_id not in _sessions:
        raise HTTPException(404, "Session not found")
    state = _sessions[session_id]
    prep = state.get("interview_preps", {}).get(job_id)
    session = state.get("mock_sessions", {}).get(job_id)

    if not prep or not session:
        raise HTTPException(404, "Interview session not started")

    questions = prep.get("top_questions", [])
    result = await evaluate_answer(
        question=req.question,
        answer=req.answer,
        current_idx=req.question_idx,
        total_questions=min(len(questions), 10),
        questions=questions,
    )

    # Record turn
    session["turns"].append({
        "role": "candidate",
        "message": req.answer,
        "timestamp": datetime.utcnow().isoformat(),
        "evaluation": None,
    })
    session["turns"].append({
        "role": "coach",
        "message": result.get("feedback", "") + (f"\n\n**Next question:** {result['next_question']}" if result.get("next_question") else ""),
        "timestamp": datetime.utcnow().isoformat(),
        "evaluation": {"scores": result.get("scores", {}), "feedback": result.get("feedback", "")},
    })
    session["current_question_idx"] = result["next_idx"]
    session["completed"] = result["is_complete"]

    if result["is_complete"]:
        session["scores"] = compute_session_score(session["turns"])
        session["overall_score"] = session["scores"].get("overall", 0)
        state["interviews_completed"] = state.get("interviews_completed", 0) + 1

    return {
        "feedback": result.get("feedback", ""),
        "scores": result.get("scores", {}),
        "next_question": result.get("next_question"),
        "overall_impression": result.get("overall_impression"),
        "is_complete": result["is_complete"],
        "session_scores": session["scores"] if result["is_complete"] else {},
    }


@app.get("/api/sessions/{session_id}/interview/{job_id}/session")
async def get_mock_session(session_id: str, job_id: str):
    if session_id not in _sessions:
        raise HTTPException(404, "Session not found")
    session = _sessions[session_id].get("mock_sessions", {}).get(job_id)
    if not session:
        raise HTTPException(404, "No mock interview session found")
    return session


@app.get("/api/sessions/{session_id}/analytics")
async def get_analytics(session_id: str):
    if session_id not in _sessions:
        raise HTTPException(404, "Session not found")
    return _build_analytics(session_id)


def _build_analytics(session_id: str) -> dict[str, Any]:
    state = _sessions.get(session_id, {})
    ats_scores = state.get("ats_scores", {})
    opt = state.get("optimized_resumes", {})
    statuses = state.get("application_statuses", {})

    scores = [v.get("total_score", 0) for v in ats_scores.values()]
    avg_ats = round(sum(scores) / len(scores), 1) if scores else 0

    return {
        "jobs_discovered": state.get("jobs_discovered_count", 0),
        "jobs_above_threshold": state.get("jobs_above_threshold", 0),
        "avg_ats_score": avg_ats,
        "optimizations_run": state.get("optimizations_run", 0),
        "applications_ready": state.get("applications_ready", 0),
        "interviews_completed": state.get("interviews_completed", 0),
        "decisions": {
            "apply": sum(1 for s in statuses.values() if s.get("decision") == "apply"),
            "improve": sum(1 for s in statuses.values() if s.get("decision") == "improve"),
            "skip": sum(1 for s in statuses.values() if s.get("decision") == "skip"),
        },
        "ats_distribution": [
            {"job_id": jid, "score": v.get("total_score", 0), "before": opt.get(jid, {}).get("before_score", 0)}
            for jid, v in list(ats_scores.items())[:10]
        ],
    }


# ─── WebSocket ────────────────────────────────────────────────────────────────

@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    await websocket.accept()
    _ws_clients.setdefault(session_id, []).append(websocket)
    logger.info("ws.connected", session=session_id)

    try:
        # Send current state on connect
        if session_id in _sessions:
            state = _sessions[session_id]
            await websocket.send_json({
                "type": "state_sync",
                "current_agent": state.get("current_agent", ""),
                "analytics": _build_analytics(session_id),
            })

        while True:
            # Keep connection alive; actual messages are broadcast by pipeline
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=30)
                if data == "ping":
                    await websocket.send_json({"type": "pong"})
            except asyncio.TimeoutError:
                await websocket.send_json({"type": "heartbeat"})

    except WebSocketDisconnect:
        logger.info("ws.disconnected", session=session_id)
        if session_id in _ws_clients:
            _ws_clients[session_id] = [
                ws for ws in _ws_clients[session_id] if ws != websocket
            ]
