"""Agent 5: Application Readiness — Categorize jobs and generate outreach."""
from __future__ import annotations
import json
from datetime import datetime
from core.state import CareerCopilotState, ApplicationStatus, AgentMessage
from core.llm import get_creative_llm, PROMPTS
from core.config import get_settings
import structlog

logger = structlog.get_logger()
settings = get_settings()


async def application_readiness_node(state: CareerCopilotState) -> dict:
    """
    LangGraph node: for each filtered job, decide apply/improve/skip,
    generate outreach messages, and pre-fill common application questions.
    """
    logger.info("agent.application_readiness.start", session=state["session_id"])

    profile = state.get("candidate_profile")
    filtered_jobs = state.get("filtered_jobs", [])
    validation_results = state.get("validation_results", {})
    ats_scores = state.get("ats_scores", {})

    if not profile or not filtered_jobs:
        return {"current_agent": "application_readiness"}

    llm = get_creative_llm()
    statuses: dict[str, ApplicationStatus] = {}
    apply_count = 0

    for job in filtered_jobs:
        job_id = job["job_id"]
        validation = validation_results.get(job_id, {})
        ats = ats_scores.get(job_id, {})

        # Use the highest score across optimizer and validator — optimizer score is most accurate
        # since it was computed from the fully augmented resume (with keyword appendix)
        ats_score = max(
            float(validation.get("recalculated_score") or 0),
            float(ats.get("total_score") or 0),
        )
        match_score = job.get("match_score", 0)
        missing_skills = validation.get("missing_skills", ats.get("missing_keywords", []))

        try:
            prompt = PROMPTS["application_readiness"]
            chain = prompt | llm
            response = await chain.ainvoke({
                "job_title": job["title"],
                "company": job["company"],
                "ats_score": round(ats_score, 1),
                "match_score": round(match_score, 1),
                "missing_skills": ", ".join(missing_skills[:8]) if missing_skills else "None",
                "candidate_name": profile.get("full_name", "Candidate"),
            })

            raw = response.content if hasattr(response, "content") else str(response)
            raw = raw.strip().lstrip("```json").rstrip("```").strip()
            data = json.loads(raw)

            decision = data.get("decision", "improve")

            # Score-based override: if ATS is high enough, always apply
            if ats_score >= settings.ats_target_score_low:
                decision = "apply"
            elif ats_score >= 60 and decision not in ("apply", "improve"):
                decision = "improve"

            if decision == "apply":
                apply_count += 1

            statuses[job_id] = ApplicationStatus(
                job_id=job_id,
                decision=decision,
                ats_score=ats_score,
                reasoning=data.get("reasoning", f"ATS score {ats_score:.0f} — {'ready to apply' if decision == 'apply' else 'needs improvement'}."),
                common_app_answers=data.get("common_app_answers", {}),
                outreach_message=data.get("outreach_message", ""),
                outreach_subject=data.get("outreach_subject", ""),
            )

            logger.info(
                "application_readiness.job_done",
                job=job["title"],
                decision=decision,
                score=ats_score,
            )

        except Exception as e:
            logger.error("application_readiness.error", job=job.get("title"), error=str(e))
            # Fallback decision
            decision = "apply" if ats_score >= settings.ats_target_score_low else ("improve" if ats_score >= 60 else "skip")
            statuses[job_id] = ApplicationStatus(
                job_id=job_id,
                decision=decision,
                ats_score=ats_score,
                reasoning=f"ATS score: {ats_score:.0f}. {'Ready to apply.' if decision == 'apply' else 'Needs improvement.' if decision == 'improve' else 'Significant skill gaps.'}",
                common_app_answers={},
                outreach_message="",
                outreach_subject="",
            )

    return {
        "application_statuses": statuses,
        "applications_ready": apply_count,
        "pending_approval": apply_count > 0,
        "current_agent": "application_readiness",
        "agent_messages": [AgentMessage(
            agent="application_readiness",
            message=f"Categorized {len(statuses)} jobs: {apply_count} ready to apply, "
                    f"{sum(1 for s in statuses.values() if s['decision'] == 'improve')} need improvement, "
                    f"{sum(1 for s in statuses.values() if s['decision'] == 'skip')} skipped.",
            level="success",
            timestamp=datetime.utcnow().isoformat(),
        )],
    }
