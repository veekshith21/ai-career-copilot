"""Agent 7: Interview Coach — Conduct mock interviews with STAR evaluation."""
from __future__ import annotations
import json
from datetime import datetime
from core.state import (
    CareerCopilotState, MockInterviewSession, MockInterviewTurn, AgentMessage
)
from core.llm import get_llm, PROMPTS
import structlog

logger = structlog.get_logger()


async def interview_coach_node(state: CareerCopilotState) -> dict:
    """
    LangGraph node: initialize mock interview sessions for approved jobs.
    The actual turn-by-turn coaching is handled via the /interview/chat endpoint
    (WebSocket), which calls `run_interview_turn` directly.
    This node just sets up the session scaffold.
    """
    logger.info("agent.interview_coach.start", session=state["session_id"])

    approved_ids = state.get("approved_job_ids", [])
    interview_preps = state.get("interview_preps", {})
    profile = state.get("candidate_profile")

    mock_sessions: dict[str, MockInterviewSession] = dict(state.get("mock_sessions", {}))

    for job_id in approved_ids:
        prep = interview_preps.get(job_id)
        if not prep or job_id in mock_sessions:
            continue

        # Create empty session scaffold — turns are added via chat endpoint
        mock_sessions[job_id] = MockInterviewSession(
            job_id=job_id,
            turns=[],
            current_question_idx=0,
            scores={"clarity": 0.0, "technical_depth": 0.0, "communication": 0.0, "confidence": 0.0},
            overall_score=0.0,
            feedback_summary="",
            completed=False,
        )

    return {
        "mock_sessions": mock_sessions,
        "interviews_completed": 0,
        "current_agent": "interview_coach",
        "agent_messages": [AgentMessage(
            agent="interview_coach",
            message=f"Mock interview sessions initialized for {len(mock_sessions)} role(s). Click 'Start Mock Interview' to begin.",
            level="info",
            timestamp=datetime.utcnow().isoformat(),
        )],
    }


# ─── Turn-by-Turn Interview Logic (called from API) ──────────────────────────

async def start_interview(
    job_id: str,
    company: str,
    role: str,
    candidate_summary: str,
    questions: list[dict],
) -> dict:
    """Generate the first question and start the mock interview."""
    llm = get_llm(temperature=0.3)
    prompt = PROMPTS["interview_coach_start"]
    chain = prompt | llm

    response = await chain.ainvoke({
        "role": role,
        "company": company,
        "candidate_summary": candidate_summary,
    })

    raw = response.content if hasattr(response, "content") else str(response)
    raw = raw.strip().lstrip("```json").rstrip("```").strip()

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        # Fallback: use first prepared question
        first_q = questions[0]["question"] if questions else "Tell me about yourself."
        data = {
            "feedback": "",
            "scores": {"clarity": 0, "technical_depth": 0, "communication": 0},
            "next_question": first_q,
        }

    return {
        "coach_message": data.get("next_question", questions[0]["question"] if questions else "Tell me about yourself."),
        "feedback": data.get("feedback", ""),
        "scores": data.get("scores", {}),
        "question_idx": 0,
    }


async def evaluate_answer(
    question: str,
    answer: str,
    current_idx: int,
    total_questions: int,
    questions: list[dict],
) -> dict:
    """Evaluate a candidate's answer and return feedback + next question."""
    llm = get_llm(temperature=0.2)
    prompt = PROMPTS["interview_coach_eval"]
    chain = prompt | llm

    response = await chain.ainvoke({
        "question": question,
        "answer": answer,
        "current_idx": current_idx + 1,
        "total_questions": total_questions,
    })

    raw = response.content if hasattr(response, "content") else str(response)
    raw = raw.strip().lstrip("```json").rstrip("```").strip()

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        data = {
            "feedback": "Good attempt. Try to be more specific with examples.",
            "scores": {"clarity": 6, "technical_depth": 6, "communication": 7},
            "next_question": questions[current_idx + 1]["question"] if current_idx + 1 < len(questions) else None,
            "overall_impression": "Solid interview performance." if current_idx + 1 >= total_questions else None,
        }

    next_idx = current_idx + 1
    next_q = data.get("next_question")
    if not next_q and next_idx < len(questions):
        next_q = questions[next_idx]["question"]

    is_complete = next_idx >= total_questions or next_q is None

    return {
        "feedback": data.get("feedback", ""),
        "scores": data.get("scores", {}),
        "next_question": next_q,
        "overall_impression": data.get("overall_impression", ""),
        "is_complete": is_complete,
        "next_idx": next_idx,
    }


def compute_session_score(turns: list[MockInterviewTurn]) -> dict[str, float]:
    """Aggregate scores across all evaluated turns."""
    score_keys = ["clarity", "technical_depth", "communication"]
    totals: dict[str, list[float]] = {k: [] for k in score_keys}

    for turn in turns:
        if turn.get("evaluation"):
            scores = turn["evaluation"].get("scores", {})
            for k in score_keys:
                if k in scores:
                    totals[k].append(float(scores[k]))

    avg: dict[str, float] = {}
    for k, vals in totals.items():
        avg[k] = round(sum(vals) / len(vals), 1) if vals else 0.0

    overall = round(sum(avg.values()) / len(avg) if avg else 0.0, 1)
    return {**avg, "overall": overall}
