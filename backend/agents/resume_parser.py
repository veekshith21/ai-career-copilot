"""Agent 1: Resume Parser — Extract structured CandidateProfile from raw text."""
from __future__ import annotations
import json
from datetime import datetime
from core.state import CareerCopilotState, CandidateProfile, AgentMessage
from core.llm import get_structured_llm, PROMPTS
from core.embeddings import safe_embed
from core.vectorstore import upsert_resume
import structlog

logger = structlog.get_logger()


async def parse_resume_node(state: CareerCopilotState) -> dict:
    """
    LangGraph node: parse raw resume text into a structured CandidateProfile.
    Also generates and stores a resume embedding in Qdrant.
    """
    logger.info("agent.resume_parser.start", session=state["session_id"])

    resume_text = state.get("resume_raw_text", "")
    if not resume_text:
        return {
            "error": "No resume text provided.",
            "current_agent": "parse_resume",
        }

    llm = get_structured_llm()
    prompt = PROMPTS["resume_parser"]
    chain = prompt | llm

    try:
        response = await chain.ainvoke({"resume_text": resume_text})
        raw_json = response.content if hasattr(response, "content") else str(response)

        # Strip markdown code blocks if present
        raw_json = raw_json.strip()
        if raw_json.startswith("```"):
            raw_json = raw_json.split("```")[1]
            if raw_json.startswith("json"):
                raw_json = raw_json[4:]

        profile_data = json.loads(raw_json)

        # Validate and set defaults
        profile = _build_profile(profile_data)

        # Generate and store embedding
        embed_text = (
            f"{profile['summary']} "
            f"{' '.join(profile['technical_skills'])} "
            f"{' '.join(b for exp in profile['experience'] for b in exp.get('bullets', [])[:2])}"
        )
        embedding = await safe_embed(embed_text)
        embedding_id = await upsert_resume(
            session_id=state["session_id"],
            embedding=embedding,
            payload={
                "name": profile["full_name"],
                "skills": profile["technical_skills"],
                "seniority": profile["seniority_level"],
            },
        )

        logger.info(
            "agent.resume_parser.done",
            name=profile["full_name"],
            skills=len(profile["technical_skills"]),
            yoe=profile["total_years_experience"],
        )

        return {
            "candidate_profile": profile,
            "resume_embedding_id": embedding_id,
            "current_agent": "parse_resume",
            "agent_messages": [AgentMessage(
                agent="resume_parser",
                message=f"Parsed profile for {profile['full_name']} — {profile['total_years_experience']}yr {profile['seniority_level']} with {len(profile['technical_skills'])} skills detected.",
                level="success",
                timestamp=datetime.utcnow().isoformat(),
            )],
        }

    except json.JSONDecodeError as e:
        logger.error("agent.resume_parser.json_error", error=str(e))
        return {
            "error": f"Failed to parse resume structure: {e}",
            "current_agent": "parse_resume",
        }
    except Exception as e:
        logger.error("agent.resume_parser.error", error=str(e))
        return {
            "error": f"Resume parsing failed: {e}",
            "current_agent": "parse_resume",
        }


def _build_profile(data: dict) -> CandidateProfile:
    """Validate and normalize the LLM output into a CandidateProfile."""
    return CandidateProfile(
        full_name=data.get("full_name", "Unknown"),
        email=data.get("email", ""),
        phone=data.get("phone", ""),
        location=data.get("location", ""),
        linkedin_url=data.get("linkedin_url"),
        github_url=data.get("github_url"),
        summary=data.get("summary", ""),
        education=data.get("education", []),
        experience=data.get("experience", []),
        projects=data.get("projects", []),
        technical_skills=data.get("technical_skills", []),
        soft_skills=data.get("soft_skills", []),
        certifications=data.get("certifications", []),
        languages=data.get("languages", []),
        total_years_experience=float(data.get("total_years_experience", 0)),
        seniority_level=data.get("seniority_level", "mid"),
    )
