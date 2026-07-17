"""Agent 4: Resume Validator — Re-score and verify optimization quality."""
from __future__ import annotations
import json
from datetime import datetime
from core.state import CareerCopilotState, ValidationResult, AgentMessage
from core.llm import get_structured_llm, PROMPTS
from core.config import get_settings
from services.ats_service import compute_ats_score, extract_jd_keywords
import structlog

logger = structlog.get_logger()
settings = get_settings()


async def validate_resume_node(state: CareerCopilotState) -> dict:
    """
    LangGraph node: re-score each optimized resume, verify keyword coverage,
    check formatting, identify remaining gaps, and generate actionable recs.
    """
    logger.info("agent.resume_validator.start", session=state["session_id"])

    profile = state.get("candidate_profile")
    resume_text = state.get("resume_raw_text", "")
    filtered_jobs = state.get("filtered_jobs", [])
    optimized_resumes = state.get("optimized_resumes", {})
    ats_scores = state.get("ats_scores", {})

    if not filtered_jobs:
        return {"current_agent": "validate_resume"}

    llm = get_structured_llm()
    validation_results: dict[str, ValidationResult] = {}

    for job in filtered_jobs:
        job_id = job["job_id"]
        jd_text = job["description"]
        req_kws, pref_kws = extract_jd_keywords(jd_text)

        # Use optimized content if available, else original
        opt = optimized_resumes.get(job_id)
        # Use optimizer's after_score if available (it was computed from the fully augmented resume)
        optimizer_score = ats_scores.get(job_id, {}).get("total_score", 0) if opt else 0

        if opt:
            # Rebuild full optimized text including appended keywords
            resume_to_validate = resume_text.replace(
                opt["original_summary"], opt["optimized_summary"]
            )
            # Re-append any keyword additions (mirror what optimizer did)
            added_kws = opt.get("added_keywords", [])
            if added_kws:
                extras = [k for k in added_kws if k.lower() not in resume_to_validate.lower()]
                if extras:
                    resume_to_validate += "\n\nAdditional Skills: " + ", ".join(extras)
        else:
            resume_to_validate = resume_text

        try:
            # ── Quick algorithmic re-score ─────────────────────────────────
            new_score = compute_ats_score(
                resume_text=resume_to_validate,
                jd_text=jd_text,
                years_experience=profile.get("total_years_experience", 0) if profile else 0,
            )

            # Use the higher of recomputed vs optimizer's stored score
            algo_score = max(new_score["total_score"], optimizer_score)

            # ── LLM deep validation (only when resume was optimized) ────────
            if opt:
                val_prompt = PROMPTS["validation"]
                val_chain = val_prompt | llm
                val_response = await val_chain.ainvoke({
                    "original_resume": resume_text[:2000],
                    "optimized_resume": resume_to_validate[:2000],
                    "job_description": jd_text[:2000],
                    "required_keywords": ", ".join(req_kws[:20]),
                })
                val_raw = val_response.content if hasattr(val_response, "content") else str(val_response)
                val_raw = val_raw.strip().lstrip("```json").rstrip("```").strip()
                val_data = json.loads(val_raw)
                llm_score = float(val_data.get("recalculated_score", algo_score))
                final_score = round(algo_score * 0.6 + llm_score * 0.4, 1)
                keyword_coverage = val_data.get("keyword_coverage_pct", new_score["keyword_match_pct"])
                missing_skills_val = val_data.get("missing_skills", new_score["missing_keywords"][:5])
                experience_gaps_val = val_data.get("experience_gaps", [])
                actionable_recs_val = val_data.get("actionable_recs", new_score["recommendations"])
                formatting_ok = bool(val_data.get("formatting_compliant", True))
            else:
                # Skip LLM — use algorithmic score only (no optimization was done)
                final_score = algo_score
                keyword_coverage = new_score["keyword_match_pct"]
                missing_skills_val = new_score["missing_keywords"][:5]
                experience_gaps_val = []
                actionable_recs_val = new_score["recommendations"]
                formatting_ok = True

            passed = final_score >= settings.ats_target_score_low

            validation_results[job_id] = ValidationResult(
                job_id=job_id,
                recalculated_score=final_score,
                keyword_coverage_pct=float(keyword_coverage),
                formatting_compliant=formatting_ok,
                missing_skills=missing_skills_val,
                experience_gaps=experience_gaps_val,
                passed=passed,
                actionable_recs=actionable_recs_val,
            )

            logger.info(
                "validator.job_done",
                job=job["title"],
                score=final_score,
                passed=passed,
            )

        except Exception as e:
            logger.error("validator.error", job=job.get("title"), error=str(e))
            # Fallback to algorithmic score only
            algo = compute_ats_score(resume_to_validate, jd_text)
            validation_results[job_id] = ValidationResult(
                job_id=job_id,
                recalculated_score=algo["total_score"],
                keyword_coverage_pct=algo["keyword_match_pct"],
                formatting_compliant=True,
                missing_skills=algo["missing_keywords"][:5],
                experience_gaps=[],
                passed=algo["total_score"] >= settings.ats_target_score_low,
                actionable_recs=algo["recommendations"],
            )

    passed_count = sum(1 for v in validation_results.values() if v["passed"])

    return {
        "validation_results": validation_results,
        "current_agent": "validate_resume",
        "agent_messages": [AgentMessage(
            agent="resume_validator",
            message=f"Validated {len(validation_results)} resume(s). {passed_count} passed ATS threshold (≥{settings.ats_target_score_low}).",
            level="success" if passed_count > 0 else "warning",
            timestamp=datetime.utcnow().isoformat(),
        )],
    }
