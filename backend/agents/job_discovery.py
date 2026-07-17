"""Agent 2: Job Discovery — Find relevant jobs and compute match scores."""
from __future__ import annotations
import json
from datetime import datetime
from core.state import CareerCopilotState, JobListing, AgentMessage
from core.llm import get_structured_llm, PROMPTS
from core.embeddings import safe_embed
from core.vectorstore import upsert_job
from core.config import get_settings
from services.job_service import discover_jobs
from services.ats_service import compute_ats_score
import structlog

logger = structlog.get_logger()
settings = get_settings()


async def discover_jobs_node(state: CareerCopilotState) -> dict:
    """
    LangGraph node: discover jobs and filter by match score.
    Computes both semantic similarity (embeddings) and keyword match (ATS).
    Only surfaces jobs with match_score >= min_match_score (default: 40).
    """
    logger.info("agent.job_discovery.start", session=state["session_id"])

    profile = state.get("candidate_profile")
    resume_text = state.get("resume_raw_text", "")

    if not profile:
        return {"error": "No candidate profile. Run resume parsing first.", "current_agent": "discover_jobs"}

    query = state.get("search_query", "")
    location = state.get("search_location", "United States")
    roles = state.get("target_roles", [profile["seniority_level"] + " " + (profile["technical_skills"][0] if profile["technical_skills"] else "engineer")])

    # 1. Fetch jobs
    raw_jobs = await discover_jobs(query, location, roles)

    # 2. Build resume embedding for semantic matching
    resume_embed_text = f"{profile['summary']} {' '.join(profile['technical_skills'])}"
    resume_embedding = await safe_embed(resume_embed_text)

    # 3. Score each job and embed it
    scored_jobs: list[JobListing] = []
    ats_scores: dict = {}

    for job in raw_jobs:
        try:
            # Semantic similarity via embeddings
            job_embed_text = f"{job['title']} {job['description'][:1000]}"
            job_embedding = await safe_embed(job_embed_text)

            # Keyword-based ATS score (quick, no LLM needed)
            ats = compute_ats_score(
                resume_text=resume_text,
                jd_text=job["description"],
                years_experience=profile["total_years_experience"],
            )

            # Job match = 60% semantic + 40% keyword
            from core.embeddings import cosine_similarity
            semantic_score = cosine_similarity(resume_embedding, job_embedding) * 100
            match_score = round(semantic_score * 0.60 + ats["keyword_match_pct"] * 0.40, 1)

            # Update job with match score
            scored_job = dict(job)
            scored_job["match_score"] = match_score

            # Store job embedding in Qdrant for later RAG
            await upsert_job(
                job_id=job["job_id"],
                embedding=job_embedding,
                payload={
                    "title": job["title"],
                    "company": job["company"],
                    "match_score": match_score,
                    "session_id": state["session_id"],
                },
            )

            if match_score >= settings.ats_min_match_score:
                scored_jobs.append(JobListing(**scored_job))
                ats_scores[job["job_id"]] = ats

        except Exception as e:
            logger.warning("job_discovery.score_error", job=job.get("title"), error=str(e))
            continue

    # Sort by match score descending
    scored_jobs.sort(key=lambda j: j["match_score"], reverse=True)

    # Cap at top 10 jobs to keep processing manageable
    top_jobs = scored_jobs[:10]

    logger.info(
        "agent.job_discovery.done",
        total_found=len(raw_jobs),
        above_threshold=len(scored_jobs),
        showing=len(top_jobs),
    )

    return {
        "discovered_jobs": raw_jobs,
        "filtered_jobs": top_jobs,
        "ats_scores": ats_scores,
        "jobs_discovered_count": len(raw_jobs),
        "jobs_above_threshold": len(scored_jobs),
        "current_agent": "discover_jobs",
        "agent_messages": [AgentMessage(
            agent="job_discovery",
            message=f"Found {len(raw_jobs)} jobs. {len(scored_jobs)} match your profile (score ≥ {settings.ats_min_match_score}). Showing top {len(top_jobs)}.",
            level="success",
            timestamp=datetime.utcnow().isoformat(),
        )],
    }
