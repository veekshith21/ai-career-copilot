"""
ATS Scoring Engine.

Computes a weighted ATS compatibility score by:
  1. Extracting required/preferred keywords from the job description
  2. Checking presence and placement in the resume
  3. Scoring skills coverage, experience alignment, education match
  4. Returning a detailed breakdown with missing keywords and recommendations
"""
from __future__ import annotations
import re
import math
from collections import Counter
from typing import NamedTuple
from core.state import ATSBreakdown

# ─── Keyword Extraction ───────────────────────────────────────────────────────

# Common technical terms to look for in JDs
TECH_PATTERNS = re.compile(
    r'\b('
    r'python|javascript|typescript|java|kotlin|swift|go|rust|c\+\+|c#|ruby|php|scala|r\b|'
    r'react|angular|vue|nextjs|svelte|node(?:\.?js)?|express|fastapi|django|flask|spring|rails|'
    r'aws|azure|gcp|kubernetes|k8s|docker|terraform|ansible|jenkins|github\s?actions|'
    r'postgresql|mysql|mongodb|redis|elasticsearch|kafka|rabbitmq|sqlite|dynamodb|'
    r'machine\s?learning|deep\s?learning|nlp|computer\s?vision|llm|rag|pytorch|tensorflow|'
    r'pandas|numpy|scikit-?learn|spark|hadoop|airflow|dbt|'
    r'agile|scrum|kanban|ci/?cd|devops|mlops|tdd|rest(?:ful)?|graphql|grpc|'
    r'git|linux|bash|shell|vim|'
    r'product\s?management|project\s?management|pmp|'
    r'data\s?analysis|business\s?intelligence|tableau|power\s?bi|looker|'
    r'sql|nosql|orm|'
    r'microservices|serverless|saas|paas|iaas|'
    r'security|oauth|jwt|ssl|'
    r'figma|sketch|adobe|ux|ui'
    r')\b',
    re.IGNORECASE,
)

SOFT_SKILL_PATTERNS = re.compile(
    r'\b('
    r'leadership|communication|collaboration|problem.solving|critical\s?thinking|'
    r'analytical|strategic|cross.functional|stakeholder|mentoring|coaching|'
    r'detail.oriented|self.motivated|innovative|adaptable|prioritiz'
    r')\b',
    re.IGNORECASE,
)

# Words that indicate requirements in JDs
REQUIRED_SIGNALS = re.compile(
    r'\b(required|must have|essential|mandatory|minimum|need|expected)\b',
    re.IGNORECASE,
)
PREFERRED_SIGNALS = re.compile(
    r'\b(preferred|plus|bonus|nice.to.have|ideally|desired|advantage)\b',
    re.IGNORECASE,
)


def extract_jd_keywords(jd_text: str) -> tuple[list[str], list[str]]:
    """Extract required and preferred keywords from a job description."""
    required_kws: set[str] = set()
    preferred_kws: set[str] = set()

    # Split into sentences for context
    sentences = re.split(r'[.\n•\-]', jd_text)

    for sent in sentences:
        sent_lower = sent.lower()
        tech_matches = set(m.group().lower() for m in TECH_PATTERNS.finditer(sent))
        soft_matches = set(m.group().lower() for m in SOFT_SKILL_PATTERNS.finditer(sent))
        all_kws = tech_matches | soft_matches

        if not all_kws:
            continue

        if REQUIRED_SIGNALS.search(sent):
            required_kws |= all_kws
        elif PREFERRED_SIGNALS.search(sent):
            preferred_kws |= all_kws
        else:
            # Unlabeled = assume required
            required_kws |= all_kws

    # Remove overlap (required takes precedence)
    preferred_kws -= required_kws

    return sorted(required_kws), sorted(preferred_kws)


def extract_resume_keywords(resume_text: str) -> set[str]:
    """Extract all technical and soft skill keywords from a resume."""
    tech = {m.group().lower() for m in TECH_PATTERNS.finditer(resume_text)}
    soft = {m.group().lower() for m in SOFT_SKILL_PATTERNS.finditer(resume_text)}
    return tech | soft


# ─── Section Scoring ─────────────────────────────────────────────────────────

def _score_keyword_match(
    resume_text: str,
    required_kws: list[str],
    preferred_kws: list[str],
) -> tuple[float, list[str], list[str]]:
    """
    Score keyword coverage.
    Required matches are worth 2x; preferred 1x.
    Returns (score 0-100, matched_kws, missing_kws).
    """
    resume_lower = resume_text.lower()
    resume_kws = extract_resume_keywords(resume_text)

    matched: list[str] = []
    missing: list[str] = []

    req_score = 0.0
    for kw in required_kws:
        # Check for the keyword anywhere in resume text
        if kw in resume_lower or kw in resume_kws:
            matched.append(kw)
            req_score += 2.0
        else:
            missing.append(kw)

    pref_score = 0.0
    for kw in preferred_kws:
        if kw in resume_lower or kw in resume_kws:
            matched.append(kw)
            pref_score += 1.0

    max_possible = len(required_kws) * 2.0 + len(preferred_kws) * 1.0
    if max_possible == 0:
        return 70.0, matched, missing   # no keywords found in JD; neutral score

    raw_score = req_score + pref_score
    pct = min(raw_score / max_possible, 1.0) * 100
    return round(pct, 1), matched, missing


def _score_experience_alignment(
    resume_text: str,
    jd_text: str,
    years_experience: float,
) -> float:
    """Check if candidate experience level matches JD requirements."""
    # Try to extract required YoE from JD
    yoe_pattern = re.compile(
        r'(\d+)\+?\s*(?:to\s*(\d+))?\s*years?\s*(?:of\s+)?(?:professional\s+)?experience',
        re.IGNORECASE,
    )
    matches = yoe_pattern.findall(jd_text)
    if not matches:
        return 80.0  # No explicit requirement → neutral

    required_min = int(matches[0][0])
    required_max = int(matches[0][1]) if matches[0][1] else required_min + 3

    if years_experience >= required_min:
        if years_experience <= required_max + 5:
            return 100.0
        return 85.0   # Overqualified — slight penalty
    else:
        gap = required_min - years_experience
        penalty = min(gap * 10, 60)
        return max(100.0 - penalty, 20.0)


def _score_education_match(resume_text: str, jd_text: str) -> float:
    """Score education alignment."""
    jd_lower = jd_text.lower()
    resume_lower = resume_text.lower()

    degree_hierarchy = {
        "phd": 4, "doctorate": 4, "doctoral": 4,
        "master": 3, "msc": 3, "mba": 3, "ms ": 3, "ma ": 3,
        "bachelor": 2, "bsc": 2, "bs ": 2, "ba ": 2, "b.s": 2, "b.a": 2,
        "associate": 1, "diploma": 1,
    }

    jd_degree_level = 0
    resume_degree_level = 0

    for degree, level in degree_hierarchy.items():
        if degree in jd_lower:
            jd_degree_level = max(jd_degree_level, level)
        if degree in resume_lower:
            resume_degree_level = max(resume_degree_level, level)

    if jd_degree_level == 0:
        return 90.0  # No degree requirement mentioned

    if resume_degree_level >= jd_degree_level:
        return 100.0
    elif resume_degree_level == jd_degree_level - 1:
        return 75.0
    else:
        return 55.0


def _score_formatting(resume_text: str) -> float:
    """Score resume formatting for ATS compatibility."""
    score = 100.0
    issues = []

    # Check length (optimal: 400-900 words)
    word_count = len(resume_text.split())
    if word_count < 200:
        score -= 20
    elif word_count < 400:
        score -= 10
    elif word_count > 1200:
        score -= 5

    # Check for key sections
    lower = resume_text.lower()
    if not any(kw in lower for kw in ["experience", "work history", "employment"]):
        score -= 15
    if not any(kw in lower for kw in ["skills", "technologies", "competencies"]):
        score -= 10
    if not any(kw in lower for kw in ["education", "degree", "university", "college"]):
        score -= 10

    # Check for contact info
    if not re.search(r'\b[\w.+-]+@[\w-]+\.\w+\b', resume_text):
        score -= 10

    return max(score, 0.0)


# ─── Main Scoring Function ────────────────────────────────────────────────────

def compute_ats_score(
    resume_text: str,
    jd_text: str,
    years_experience: float = 0,
) -> ATSBreakdown:
    """
    Compute a comprehensive ATS score with detailed breakdown.
    Weights:
      - Keyword match:          40%
      - Skills coverage:        20%
      - Experience alignment:   20%
      - Education match:        10%
      - Formatting:             10%
    """
    required_kws, preferred_kws = extract_jd_keywords(jd_text)

    keyword_score, matched_kws, missing_kws = _score_keyword_match(
        resume_text, required_kws, preferred_kws
    )
    skills_coverage = keyword_score   # Use same computation for skills coverage
    experience_score = _score_experience_alignment(resume_text, jd_text, years_experience)
    education_score = _score_education_match(resume_text, jd_text)
    formatting_score = _score_formatting(resume_text)

    # Weighted composite
    total = (
        keyword_score * 0.40 +
        skills_coverage * 0.20 +
        experience_score * 0.20 +
        education_score * 0.10 +
        formatting_score * 0.10
    )

    # Generate recommendations
    recommendations = []
    if keyword_score < 70:
        top_missing = missing_kws[:5]
        recommendations.append(f"Add these high-impact keywords: {', '.join(top_missing)}")
    if experience_score < 70:
        recommendations.append("Quantify achievements with metrics (e.g., 'increased X by Y%')")
    if education_score < 75:
        recommendations.append("Highlight relevant coursework or certifications that compensate for education gaps")
    if formatting_score < 80:
        recommendations.append("Ensure your resume has clear Experience, Skills, and Education sections")
    if total >= 80:
        recommendations.append("Resume is ATS-ready — focus on personalizing the cover letter")

    return ATSBreakdown(
        keyword_match_pct=round(keyword_score, 1),
        skills_coverage=round(skills_coverage, 1),
        experience_alignment=round(experience_score, 1),
        education_match=round(education_score, 1),
        formatting_score=round(formatting_score, 1),
        total_score=round(total, 1),
        missing_keywords=missing_kws[:15],   # top 15 gaps
        present_keywords=matched_kws[:20],
        recommendations=recommendations,
    )


def compute_job_match_score(
    resume_embedding: list[float],
    job_embedding: list[float],
    resume_text: str,
    jd_text: str,
    years_experience: float = 0,
) -> float:
    """
    Compute overall job match score (0-100) combining:
    - Semantic similarity via embeddings (60%)
    - ATS keyword match (40%)
    """
    from core.embeddings import cosine_similarity
    semantic_sim = cosine_similarity(resume_embedding, job_embedding) * 100

    ats = compute_ats_score(resume_text, jd_text, years_experience)
    keyword_component = ats["keyword_match_pct"]

    match_score = (semantic_sim * 0.60) + (keyword_component * 0.40)
    return round(match_score, 1)
