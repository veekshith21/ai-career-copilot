"""LangGraph state schema for the AI Career Copilot."""
from __future__ import annotations
from typing import Any, Optional
from typing_extensions import TypedDict, Annotated
import operator


# ─── Sub-state Types ──────────────────────────────────────────────────────────

class EducationItem(TypedDict):
    institution: str
    degree: str
    field: str
    graduation_year: Optional[str]
    gpa: Optional[str]


class ExperienceItem(TypedDict):
    company: str
    title: str
    start_date: str
    end_date: str
    is_current: bool
    bullets: list[str]
    technologies: list[str]


class ProjectItem(TypedDict):
    name: str
    description: str
    technologies: list[str]
    url: Optional[str]


class CandidateProfile(TypedDict):
    full_name: str
    email: str
    phone: str
    location: str
    linkedin_url: Optional[str]
    github_url: Optional[str]
    summary: str
    education: list[EducationItem]
    experience: list[ExperienceItem]
    projects: list[ProjectItem]
    technical_skills: list[str]
    soft_skills: list[str]
    certifications: list[str]
    languages: list[str]
    total_years_experience: float
    seniority_level: str   # junior | mid | senior | staff | principal


class JobListing(TypedDict):
    job_id: str
    title: str
    company: str
    location: str
    job_type: str           # full_time | part_time | contract | remote
    salary_min: Optional[int]
    salary_max: Optional[int]
    description: str
    required_skills: list[str]
    preferred_skills: list[str]
    experience_required: str
    apply_url: str
    source: str             # linkedin | indeed | jsearch | mock
    posted_date: str
    match_score: float      # 0–100, computed after discovery


class ATSBreakdown(TypedDict):
    keyword_match_pct: float
    skills_coverage: float
    experience_alignment: float
    education_match: float
    formatting_score: float
    total_score: float
    missing_keywords: list[str]
    present_keywords: list[str]
    recommendations: list[str]


class OptimizedResume(TypedDict):
    job_id: str
    original_summary: str
    optimized_summary: str
    original_bullets: list[str]
    optimized_bullets: list[str]
    added_keywords: list[str]
    cover_letter: str
    before_score: float
    after_score: float
    optimization_notes: str


class ValidationResult(TypedDict):
    job_id: str
    recalculated_score: float
    keyword_coverage_pct: float
    formatting_compliant: bool
    missing_skills: list[str]
    experience_gaps: list[str]
    passed: bool            # True if score >= target
    actionable_recs: list[str]


class ApplicationStatus(TypedDict):
    job_id: str
    decision: str           # "apply" | "improve" | "skip"
    ats_score: float
    reasoning: str
    common_app_answers: dict[str, str]
    outreach_message: str
    outreach_subject: str


class InterviewQuestion(TypedDict):
    question: str
    category: str           # technical | behavioral | company | role
    difficulty: str         # easy | medium | hard
    model_answer: str
    star_framework: Optional[dict[str, str]]
    follow_up_questions: list[str]


class InterviewPrep(TypedDict):
    job_id: str
    company: str
    role: str
    top_questions: list[InterviewQuestion]
    company_research: str
    salary_negotiation_tips: str
    questions_to_ask: list[str]


class MockInterviewTurn(TypedDict):
    role: str               # "coach" | "candidate"
    message: str
    timestamp: str
    evaluation: Optional[dict[str, Any]]


class MockInterviewSession(TypedDict):
    job_id: str
    turns: list[MockInterviewTurn]
    current_question_idx: int
    scores: dict[str, float]    # communication, clarity, depth, confidence
    overall_score: float
    feedback_summary: str
    completed: bool


class AgentMessage(TypedDict):
    agent: str
    message: str
    level: str              # info | warning | error | success
    timestamp: str


# ─── Main LangGraph State ────────────────────────────────────────────────────

class CareerCopilotState(TypedDict):
    # Session
    session_id: str
    user_id: Optional[str]

    # Stage 1: Resume
    resume_raw_text: str
    resume_file_path: str
    linkedin_url: Optional[str]
    candidate_profile: Optional[CandidateProfile]
    resume_embedding_id: Optional[str]

    # Stage 2: Jobs
    search_query: str
    search_location: str
    target_roles: list[str]
    discovered_jobs: Annotated[list[JobListing], operator.add]
    filtered_jobs: list[JobListing]          # score >= min_match_score

    # Stage 3: ATS Optimization
    ats_scores: dict[str, ATSBreakdown]      # keyed by job_id
    optimized_resumes: dict[str, OptimizedResume]

    # Stage 4: Validation
    validation_results: dict[str, ValidationResult]

    # Stage 5: Application Readiness
    application_statuses: dict[str, ApplicationStatus]

    # Stage 6: Interview Intelligence
    interview_preps: dict[str, InterviewPrep]

    # Stage 7: Mock Interview
    mock_sessions: dict[str, MockInterviewSession]

    # Orchestration
    current_agent: str
    active_job_id: Optional[str]
    agent_messages: Annotated[list[AgentMessage], operator.add]
    error: Optional[str]

    # Human-in-the-loop
    pending_approval: bool
    approved_job_ids: list[str]

    # Analytics
    jobs_discovered_count: int
    jobs_above_threshold: int
    optimizations_run: int
    applications_ready: int
    interviews_completed: int
