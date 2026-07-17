"""
LangGraph Orchestrator — AI Career Copilot
"""
from __future__ import annotations
import json
from datetime import datetime
from typing import Literal

from langgraph.graph import StateGraph, END, START
from langgraph.checkpoint.memory import MemorySaver

from core.state import CareerCopilotState, AgentMessage
from agents.resume_parser import parse_resume_node
from agents.job_discovery import discover_jobs_node
from agents.ats_optimizer import optimize_ats_node
from agents.resume_validator import validate_resume_node
from agents.application_agent import application_readiness_node
from agents.interview_intel import interview_intel_node
from agents.interview_coach import interview_coach_node
import structlog

logger = structlog.get_logger()


# ─── Routing Functions ────────────────────────────────────────────────────────

def route_after_discovery(state: CareerCopilotState) -> Literal["optimize_ats", "application_readiness", "__end__"]:
    filtered = state.get("filtered_jobs", [])
    if not filtered:
        logger.warning("routing.no_jobs_found")
        return "__end__"
    scores = state.get("ats_scores", {})
    needs_opt = any(
        scores.get(j["job_id"], {}).get("total_score", 0) < 80
        for j in filtered
    )
    return "optimize_ats" if needs_opt else "application_readiness"


def route_after_validation(state: CareerCopilotState) -> Literal["optimize_ats", "application_readiness"]:
    # Always proceed to application_readiness — avoid infinite retry loop
    # (small models often cannot improve scores enough to pass validation threshold)
    return "application_readiness"


def route_after_application(state: CareerCopilotState) -> Literal["human_approval", "__end__"]:
    apply_jobs = [
        jid for jid, s in state.get("application_statuses", {}).items()
        if s.get("decision") == "apply"
    ]
    if apply_jobs:
        return "human_approval"
    return "__end__"


def route_after_approval(state: CareerCopilotState) -> Literal["interview_intel", "__end__"]:
    approved = state.get("approved_job_ids", [])
    if approved:
        return "interview_intel"
    return "__end__"


# ─── Human-in-the-Loop Node ──────────────────────────────────────────────────

def human_approval_node(state: CareerCopilotState) -> dict:
    apply_jobs = [
        jid for jid, s in state.get("application_statuses", {}).items()
        if s.get("decision") == "apply"
    ]
    logger.info("human_approval.waiting", jobs_pending_approval=len(apply_jobs))
    return {
        "pending_approval": True,
        "current_agent": "human_approval",
        "agent_messages": [AgentMessage(
            agent="human_approval",
            message=f"{len(apply_jobs)} job(s) ready for your review. Please approve which ones to proceed with.",
            level="info",
            timestamp=datetime.utcnow().isoformat(),
        )],
    }


# ─── Graph Builder ────────────────────────────────────────────────────────────

def build_graph(checkpointer=None) -> StateGraph:
    g = StateGraph(CareerCopilotState)

    g.add_node("parse_resume", parse_resume_node)
    g.add_node("discover_jobs", discover_jobs_node)
    g.add_node("optimize_ats", optimize_ats_node)
    g.add_node("validate_resume", validate_resume_node)
    g.add_node("application_readiness", application_readiness_node)
    g.add_node("human_approval", human_approval_node)
    g.add_node("interview_intel", interview_intel_node)
    g.add_node("interview_coach", interview_coach_node)

    g.add_edge(START, "parse_resume")
    g.add_edge("parse_resume", "discover_jobs")

    g.add_conditional_edges(
        "discover_jobs",
        route_after_discovery,
        {
            "optimize_ats": "optimize_ats",
            "application_readiness": "application_readiness",
            "__end__": END,
        },
    )

    g.add_edge("optimize_ats", "validate_resume")

    g.add_conditional_edges(
        "validate_resume",
        route_after_validation,
        {
            "optimize_ats": "optimize_ats",
            "application_readiness": "application_readiness",
        },
    )

    g.add_conditional_edges(
        "application_readiness",
        route_after_application,
        {
            "human_approval": "human_approval",
            "__end__": END,
        },
    )

    g.add_conditional_edges(
        "human_approval",
        route_after_approval,
        {
            "interview_intel": "interview_intel",
            "__end__": END,
        },
    )

    g.add_edge("interview_intel", "interview_coach")
    g.add_edge("interview_coach", END)

    return g


def compile_graph(db_path: str = "./data/checkpoints.db"):
    """Compile the graph with in-memory checkpointing."""
    checkpointer = MemorySaver()
    g = build_graph(checkpointer=checkpointer)
    return g.compile(checkpointer=checkpointer, interrupt_before=["human_approval"])
