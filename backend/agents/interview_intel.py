"""Agent 6: Interview Intelligence — Generate top 20 questions via RAG."""
from __future__ import annotations
import json
from datetime import datetime
from core.state import CareerCopilotState, InterviewPrep, InterviewQuestion, AgentMessage
from core.llm import get_creative_llm, PROMPTS
from core.embeddings import safe_embed
from core.vectorstore import search_interview_questions, upsert_interview_questions
import structlog

logger = structlog.get_logger()


async def interview_intel_node(state: CareerCopilotState) -> dict:
    """
    LangGraph node: for each approved job, generate interview intelligence:
    - RAG-retrieve relevant prior interview questions from Qdrant
    - Generate top 20 questions with model answers tailored to the candidate
    - Add company research, salary tips, and questions to ask
    """
    logger.info("agent.interview_intel.start", session=state["session_id"])

    profile = state.get("candidate_profile")
    filtered_jobs = state.get("filtered_jobs", [])
    approved_ids = state.get("approved_job_ids", [])
    application_statuses = state.get("application_statuses", {})

    # Only prepare for approved jobs (or all apply-decision jobs if none approved yet)
    target_job_ids = approved_ids or [
        jid for jid, s in application_statuses.items() if s.get("decision") == "apply"
    ]

    if not profile or not target_job_ids:
        return {"current_agent": "interview_intel"}

    llm = get_creative_llm()
    preps: dict[str, InterviewPrep] = {}

    job_map = {j["job_id"]: j for j in filtered_jobs}

    for job_id in target_job_ids[:3]:  # Max 3 interview preps per run
        job = job_map.get(job_id)
        if not job:
            continue

        try:
            logger.info("interview_intel.preparing", job=job["title"], company=job["company"])

            # ── RAG: retrieve relevant existing questions ──────────────────
            query_text = f"{job['title']} {job['company']} interview questions"
            query_embedding = await safe_embed(query_text)
            rag_hits = await search_interview_questions(
                query_embedding=query_embedding,
                company=job["company"],
                role=job["title"],
                top_k=10,
            )
            rag_context = "\n".join(
                hit.payload.get("question", "") for hit in rag_hits if hit.payload
            )

            # ── LLM: Generate 20 questions ────────────────────────────────
            candidate_summary = (
                f"{profile['full_name']} — {profile['total_years_experience']}yr "
                f"{profile['seniority_level']} engineer. "
                f"Skills: {', '.join(profile['technical_skills'][:12])}. "
                f"Recent: {profile['experience'][0]['title'] if profile.get('experience') else 'N/A'} "
                f"at {profile['experience'][0]['company'] if profile.get('experience') else 'N/A'}."
            )

            prompt = PROMPTS["interview_intel"]
            chain = prompt | llm
            response = await chain.ainvoke({
                "company": job["company"],
                "role": job["title"],
                "candidate_summary": candidate_summary,
                "job_description": job["description"][:2000],
            })

            raw = response.content if hasattr(response, "content") else str(response)
            raw = raw.strip().lstrip("```json").rstrip("```").strip()
            questions_data = json.loads(raw)

            # Validate and cap at 20
            questions: list[InterviewQuestion] = []
            for q in questions_data[:20]:
                questions.append(InterviewQuestion(
                    question=q.get("question", ""),
                    category=q.get("category", "behavioral"),
                    difficulty=q.get("difficulty", "medium"),
                    model_answer=q.get("model_answer", ""),
                    star_framework=q.get("star_framework"),
                    follow_up_questions=q.get("follow_up_questions", []),
                ))

            # Store questions in Qdrant for future RAG
            if questions:
                embeds = await safe_embed(questions[0]["question"])
                # Store all at once (simplified — batch one by one)
                all_embeds = [await safe_embed(q["question"]) for q in questions[:5]]
                await upsert_interview_questions(
                    questions=[dict(q) for q in questions[:5]],
                    company=job["company"],
                    role=job["title"],
                    embeddings=all_embeds,
                )

            preps[job_id] = InterviewPrep(
                job_id=job_id,
                company=job["company"],
                role=job["title"],
                top_questions=questions,
                company_research=_generate_company_research(job["company"], job["description"]),
                salary_negotiation_tips=_salary_tips(job),
                questions_to_ask=_questions_to_ask(job),
            )

            logger.info(
                "interview_intel.done",
                job=job["title"],
                questions_generated=len(questions),
            )

        except Exception as e:
            logger.error("interview_intel.error", job=job.get("title"), error=str(e))
            continue

    return {
        "interview_preps": preps,
        "current_agent": "interview_intel",
        "agent_messages": [AgentMessage(
            agent="interview_intel",
            message=f"Generated interview prep for {len(preps)} role(s) with 20 questions each.",
            level="success",
            timestamp=datetime.utcnow().isoformat(),
        )],
    }


def _generate_company_research(company: str, jd: str) -> str:
    return (
        f"Research checklist for {company}:\n"
        "• Review recent earnings/news (past 6 months)\n"
        "• Study the product — use it if possible\n"
        "• Read Glassdoor reviews (culture, interview process)\n"
        "• Check LinkedIn for your interviewers' backgrounds\n"
        "• Review their engineering blog / open-source projects\n"
        "• Know their mission, values, and key competitors"
    )


def _salary_tips(job: dict) -> str:
    low = job.get("salary_min", 0)
    high = job.get("salary_max", 0)
    if low and high:
        midpoint = (low + high) // 2
        return (
            f"Salary range: ${low:,}–${high:,}. "
            f"Negotiate toward ${high:,}. "
            "Delay salary discussion until you have an offer. "
            "Anchor high — start 10-15% above your target. "
            "Always negotiate — 85% of employers expect it."
        )
    return (
        "Research market rates on Levels.fyi, Glassdoor, and LinkedIn Salary. "
        "Delay salary discussion until offer stage. Anchor 15% above your target."
    )


def _questions_to_ask(job: dict) -> list[str]:
    return [
        f"What does success look like in this role at {job['company']} in the first 90 days?",
        "What are the biggest technical challenges the team is currently facing?",
        "How does the team approach code reviews and engineering standards?",
        "What does the on-call rotation look like?",
        "How does {company} support professional development and learning?".replace("{company}", job["company"]),
        "What are the next major projects or initiatives for this team?",
        "How are priorities set and how does the team handle competing demands?",
    ]
