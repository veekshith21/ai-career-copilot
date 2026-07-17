"""
Job Discovery Service.

Supports two modes:
  1. JSearch API (RapidAPI) — real jobs from LinkedIn, Indeed, Glassdoor
  2. Mock data — realistic seed jobs for offline development/testing
"""
from __future__ import annotations
import uuid
import httpx
from core.config import get_settings
from core.state import JobListing
import structlog

logger = structlog.get_logger()
settings = get_settings()


# ─── JSearch API ─────────────────────────────────────────────────────────────

async def search_jsearch(
    query: str,
    location: str = "United States",
    num_pages: int = 3,
) -> list[JobListing]:
    """Fetch jobs from JSearch (RapidAPI) — real LinkedIn/Indeed data."""
    if not settings.jsearch_api_key:
        logger.warning("jsearch.no_api_key", fallback="mock_data")
        return []

    headers = {
        "X-RapidAPI-Key": settings.jsearch_api_key,
        "X-RapidAPI-Host": settings.jsearch_host,
    }
    jobs: list[JobListing] = []

    async with httpx.AsyncClient(timeout=30) as client:
        for page in range(1, num_pages + 1):
            try:
                resp = await client.get(
                    f"https://{settings.jsearch_host}/search",
                    headers=headers,
                    params={
                        "query": f"{query} in {location}",
                        "page": str(page),
                        "num_pages": "1",
                        "date_posted": "month",
                        "employment_types": "FULLTIME,CONTRACTOR",
                    },
                )
                resp.raise_for_status()
                data = resp.json()
                for item in data.get("data", []):
                    jobs.append(_parse_jsearch_item(item))
            except Exception as e:
                logger.warning("jsearch.fetch_error", page=page, error=str(e))
    return jobs


def _parse_jsearch_item(item: dict) -> JobListing:
    return JobListing(
        job_id=item.get("job_id") or str(uuid.uuid4()),
        title=item.get("job_title", ""),
        company=item.get("employer_name", ""),
        location=f"{item.get('job_city', '')}, {item.get('job_state', '')}".strip(", "),
        job_type=item.get("job_employment_type", "full_time").lower().replace(" ", "_"),
        salary_min=item.get("job_min_salary"),
        salary_max=item.get("job_max_salary"),
        description=item.get("job_description", ""),
        required_skills=_parse_highlights(item, "required"),
        preferred_skills=_parse_highlights(item, "preferred"),
        experience_required=_extract_experience(item.get("job_description", "")),
        apply_url=item.get("job_apply_link", ""),
        source="jsearch",
        posted_date=item.get("job_posted_at_datetime_utc", "")[:10],
        match_score=0.0,
    )


def _parse_highlights(item: dict, category: str) -> list[str]:
    highlights = item.get("job_highlights", {})
    qualifications = highlights.get("Qualifications", [])
    return qualifications[:10] if qualifications else []


def _extract_experience(description: str) -> str:
    import re
    m = re.search(r'(\d+)\+?\s*(?:to\s*\d+\s*)?years?\s*(?:of\s+)?experience', description, re.I)
    return f"{m.group(1)}+ years" if m else "Not specified"


# ─── Mock Job Data ────────────────────────────────────────────────────────────

MOCK_JOBS: list[dict] = [
    {
        "title": "Senior Software Engineer – Backend",
        "company": "Stripe",
        "location": "San Francisco, CA (Remote OK)",
        "job_type": "full_time",
        "salary_min": 180000, "salary_max": 240000,
        "description": """We're looking for a Senior Backend Engineer to join Stripe's Payments Infrastructure team.

Required:
- 5+ years of professional software engineering experience
- Expert proficiency in Python or Go
- Deep understanding of distributed systems, microservices architecture
- Experience with PostgreSQL, Redis, Kafka
- Strong knowledge of REST APIs and gRPC
- Experience with Docker and Kubernetes
- CI/CD pipeline experience with GitHub Actions or Jenkins
- Bachelor's degree in Computer Science or equivalent experience

Preferred:
- Experience with payment systems or financial infrastructure
- Contributions to open-source projects
- AWS or GCP cloud infrastructure experience
- Knowledge of system design patterns and scalability

Responsibilities:
- Design, build, and maintain high-throughput payment processing systems
- Lead technical design discussions and code reviews
- Mentor junior engineers
- Collaborate cross-functionally with product and design teams
- Drive engineering best practices and technical documentation""",
        "required_skills": ["Python", "Go", "PostgreSQL", "Redis", "Kafka", "Docker", "Kubernetes", "REST", "gRPC"],
        "preferred_skills": ["AWS", "GitHub Actions", "open-source", "payment systems"],
        "experience_required": "5+ years",
        "apply_url": "https://stripe.com/jobs",
        "source": "mock",
        "posted_date": "2026-06-01",
    },
    {
        "title": "Machine Learning Engineer",
        "company": "OpenAI",
        "location": "San Francisco, CA",
        "job_type": "full_time",
        "salary_min": 250000, "salary_max": 370000,
        "description": """OpenAI is seeking a Machine Learning Engineer to join our Applied AI team.

Required:
- 3+ years of machine learning engineering experience
- Expert Python skills (PyTorch, TensorFlow)
- Experience training and fine-tuning large language models (LLMs)
- Strong understanding of transformer architectures and attention mechanisms
- Experience with MLOps: model serving, monitoring, A/B testing
- Proficiency with distributed training across GPU clusters
- Bachelor's or Master's degree in Computer Science, Machine Learning, or related field

Preferred:
- PhD in ML or related field
- Experience with RLHF or alignment techniques
- Publications in NLP or deep learning conferences (NeurIPS, ICML, ICLR)
- RAG pipeline implementation experience
- Knowledge of CUDA programming

Responsibilities:
- Train and fine-tune foundation models
- Implement and evaluate new ML architectures
- Build scalable ML infrastructure
- Collaborate with research team to bring models to production
- Optimize model performance and efficiency""",
        "required_skills": ["Python", "PyTorch", "TensorFlow", "LLM", "deep learning", "MLOps", "distributed training"],
        "preferred_skills": ["RAG", "RLHF", "CUDA", "NLP", "transformers", "PhD"],
        "experience_required": "3+ years",
        "apply_url": "https://openai.com/careers",
        "source": "mock",
        "posted_date": "2026-06-05",
    },
    {
        "title": "Data Scientist – Growth Analytics",
        "company": "Airbnb",
        "location": "San Francisco, CA (Hybrid)",
        "job_type": "full_time",
        "salary_min": 160000, "salary_max": 210000,
        "description": """Airbnb is hiring a Data Scientist to join the Growth Analytics team.

Required:
- 3+ years of experience as a data scientist or analyst
- Expert SQL skills (PostgreSQL, BigQuery, or Snowflake)
- Proficiency in Python (pandas, numpy, scikit-learn)
- Strong statistical foundation: A/B testing, hypothesis testing, regression analysis
- Experience with data visualization tools (Tableau, Looker, or similar)
- Experience with Spark or other big data processing frameworks
- Bachelor's degree in Statistics, Mathematics, Computer Science, or related field

Preferred:
- Experience with causal inference and experimentation platforms
- Knowledge of dbt for data modeling
- Experience in marketplace or e-commerce analytics
- Familiarity with Airflow for pipeline orchestration

Responsibilities:
- Design and analyze A/B experiments to drive growth
- Build predictive models for user behavior and revenue forecasting
- Partner with product and engineering to define and track KPIs
- Create dashboards and self-serve analytics tools
- Communicate findings to senior leadership""",
        "required_skills": ["SQL", "Python", "pandas", "scikit-learn", "statistics", "A/B testing", "Tableau", "Spark"],
        "preferred_skills": ["dbt", "Airflow", "causal inference", "BigQuery", "Looker"],
        "experience_required": "3+ years",
        "apply_url": "https://careers.airbnb.com",
        "source": "mock",
        "posted_date": "2026-06-03",
    },
    {
        "title": "Senior Product Manager – AI Platform",
        "company": "Google",
        "location": "Mountain View, CA (Hybrid)",
        "job_type": "full_time",
        "salary_min": 200000, "salary_max": 280000,
        "description": """Google is seeking a Senior PM to lead AI Platform product strategy.

Required:
- 5+ years of product management experience
- 2+ years working on AI/ML products or platforms
- Technical background: ability to understand ML systems, APIs, and infrastructure
- Experience with agile/scrum methodologies
- Strong stakeholder management and cross-functional collaboration
- Data-driven decision making with SQL and analytics tools
- Excellent written and verbal communication skills
- Bachelor's degree in Computer Science, Engineering, or business-related field

Preferred:
- MBA or advanced degree
- Experience with developer tools or platform products
- Understanding of LLMs, Vertex AI, or cloud ML services
- Prior experience in Big Tech or high-growth startup

Responsibilities:
- Own the product roadmap for Google's ML developer platform
- Define metrics, success criteria, and OKRs
- Work closely with engineering, research, and GTM teams
- Conduct user research and competitive analysis
- Drive launches and communicate product decisions company-wide""",
        "required_skills": ["product management", "AI/ML", "agile", "scrum", "SQL", "stakeholder management", "roadmap"],
        "preferred_skills": ["MBA", "Vertex AI", "LLM", "developer tools", "OKR"],
        "experience_required": "5+ years",
        "apply_url": "https://careers.google.com",
        "source": "mock",
        "posted_date": "2026-06-08",
    },
    {
        "title": "Full Stack Engineer – React/Node.js",
        "company": "Figma",
        "location": "San Francisco, CA (Remote OK)",
        "job_type": "full_time",
        "salary_min": 160000, "salary_max": 220000,
        "description": """Figma is hiring a Full Stack Engineer to work on our core collaboration platform.

Required:
- 3+ years of software engineering experience
- Expert React and TypeScript skills
- Proficiency in Node.js and Express (or similar)
- Experience with PostgreSQL and Redis
- REST API design and implementation
- Testing: Jest, Cypress, or similar
- CI/CD experience (GitHub Actions)
- Git proficiency

Preferred:
- WebGL or Canvas rendering experience
- Experience with real-time collaborative systems (OT, CRDTs)
- GraphQL API experience
- Docker and Kubernetes experience
- Experience with design tools or creative software

Responsibilities:
- Build and maintain features in Figma's web-based design tool
- Optimize performance of complex rendering pipelines
- Collaborate with designers and product managers
- Write high-quality, well-tested code
- Participate in code reviews and architecture discussions""",
        "required_skills": ["React", "TypeScript", "JavaScript", "Node.js", "PostgreSQL", "Redis", "REST", "Jest"],
        "preferred_skills": ["GraphQL", "Docker", "WebGL", "CRDTs", "GitHub Actions"],
        "experience_required": "3+ years",
        "apply_url": "https://figma.com/careers",
        "source": "mock",
        "posted_date": "2026-06-10",
    },
    {
        "title": "Business Analyst – Operations",
        "company": "McKinsey & Company",
        "location": "New York, NY (Hybrid)",
        "job_type": "full_time",
        "salary_min": 95000, "salary_max": 130000,
        "description": """McKinsey seeks a Business Analyst to join our Operations Practice.

Required:
- 1-3 years of experience in consulting, finance, or operations
- Strong analytical and problem-solving skills
- Proficiency in Excel and PowerPoint (financial modeling, executive presentations)
- SQL proficiency for data querying
- Experience with business intelligence tools (Tableau or Power BI)
- Excellent communication and stakeholder management skills
- Bachelor's degree in Business, Economics, Engineering, or related field

Preferred:
- MBA or advanced degree
- Experience in supply chain, logistics, or manufacturing
- Python or R for data analysis
- Project management certification (PMP, Six Sigma)

Responsibilities:
- Analyze complex business problems and develop data-driven recommendations
- Build financial models and operational dashboards
- Support client engagements from diagnosis through implementation
- Present findings to C-suite stakeholders
- Collaborate with cross-functional teams across client organizations""",
        "required_skills": ["Excel", "PowerPoint", "SQL", "Tableau", "business analysis", "stakeholder management", "analytical"],
        "preferred_skills": ["MBA", "Python", "R", "Power BI", "supply chain", "PMP"],
        "experience_required": "1-3 years",
        "apply_url": "https://mckinsey.com/careers",
        "source": "mock",
        "posted_date": "2026-06-06",
    },
    {
        "title": "DevOps Engineer – Platform Engineering",
        "company": "Datadog",
        "location": "New York, NY (Remote OK)",
        "job_type": "full_time",
        "salary_min": 155000, "salary_max": 200000,
        "description": """Datadog is hiring a DevOps/Platform Engineer to scale our infrastructure.

Required:
- 4+ years of DevOps or Site Reliability Engineering experience
- Expert Kubernetes and Docker skills
- Proficiency with Terraform and infrastructure-as-code
- CI/CD pipeline design and optimization (GitHub Actions, Jenkins, ArgoCD)
- AWS or GCP cloud infrastructure management
- Monitoring and observability (Prometheus, Grafana, or Datadog itself)
- Linux/bash scripting proficiency
- Python or Go for automation

Preferred:
- Experience with Istio or service mesh architectures
- Helm chart authoring
- Security best practices (SOC2, zero-trust networking)
- Kafka or message queue infrastructure management
- Experience supporting high-throughput, low-latency systems

Responsibilities:
- Design and maintain Kubernetes clusters at scale
- Automate infrastructure provisioning with Terraform
- Build and maintain CI/CD pipelines
- Implement monitoring, alerting, and incident response procedures
- Drive security and compliance initiatives""",
        "required_skills": ["Kubernetes", "Docker", "Terraform", "AWS", "CI/CD", "Python", "Go", "Linux", "GitHub Actions"],
        "preferred_skills": ["Istio", "Helm", "Kafka", "Prometheus", "Grafana", "GCP"],
        "experience_required": "4+ years",
        "apply_url": "https://datadoghq.com/careers",
        "source": "mock",
        "posted_date": "2026-06-07",
    },
    {
        "title": "AI Research Engineer – NLP",
        "company": "Anthropic",
        "location": "San Francisco, CA",
        "job_type": "full_time",
        "salary_min": 240000, "salary_max": 350000,
        "description": """Anthropic is looking for an AI Research Engineer to advance safe and capable AI.

Required:
- PhD or equivalent research experience in ML, NLP, or Computer Science
- Expert Python and PyTorch skills
- Strong publication record or demonstrated research contributions
- Experience with transformer architectures and large-scale language model training
- Proficiency with distributed training (DeepSpeed, FSDP, Megatron)
- Experience with RLHF, Constitutional AI, or alignment techniques

Preferred:
- Contributions to open-source ML research
- Experience with mechanistic interpretability
- Knowledge of scaling laws and emergent behavior
- RAG and retrieval-augmented systems experience
- Strong mathematical background (linear algebra, probability, optimization)

Responsibilities:
- Design and execute large-scale ML experiments
- Develop novel alignment and safety techniques
- Implement and optimize training infrastructure
- Publish research and engage with the academic community
- Collaborate with policy and safety teams""",
        "required_skills": ["Python", "PyTorch", "NLP", "transformers", "LLM", "RLHF", "deep learning", "distributed training"],
        "preferred_skills": ["RAG", "interpretability", "DeepSpeed", "Constitutional AI", "PhD"],
        "experience_required": "PhD or equivalent",
        "apply_url": "https://anthropic.com/careers",
        "source": "mock",
        "posted_date": "2026-06-04",
    },
]


def get_mock_jobs(query: str = "", location: str = "") -> list[JobListing]:
    """Return mock jobs, optionally filtered by query keywords."""
    jobs: list[JobListing] = []
    query_lower = query.lower()

    for mock in MOCK_JOBS:
        # Basic relevance filter
        if query_lower:
            searchable = (
                mock["title"] + " " + mock["description"] + " " +
                " ".join(mock.get("required_skills", []))
            ).lower()
            if not any(w in searchable for w in query_lower.split()):
                continue

        jobs.append(JobListing(
            job_id=str(uuid.uuid4()),
            title=mock["title"],
            company=mock["company"],
            location=mock["location"],
            job_type=mock["job_type"],
            salary_min=mock.get("salary_min"),
            salary_max=mock.get("salary_max"),
            description=mock["description"],
            required_skills=mock.get("required_skills", []),
            preferred_skills=mock.get("preferred_skills", []),
            experience_required=mock["experience_required"],
            apply_url=mock["apply_url"],
            source=mock["source"],
            posted_date=mock["posted_date"],
            match_score=0.0,
        ))

    return jobs


async def discover_jobs(
    query: str,
    location: str,
    roles: list[str],
) -> list[JobListing]:
    """Main entry point: fetch jobs from JSearch or fall back to mock data."""
    if settings.use_mock_jobs or not settings.jsearch_api_key:
        combined_query = query or " OR ".join(roles) if roles else "software engineer"
        jobs = get_mock_jobs(combined_query, location)
        # If query filtered too aggressively, return all mock jobs
        if not jobs:
            jobs = get_mock_jobs("", location)
        logger.info("jobs.discovered", source="mock", count=len(jobs))
        return jobs

    # Real JSearch API
    combined_query = query or (roles[0] if roles else "software engineer")
    jobs = await search_jsearch(combined_query, location, num_pages=2)
    logger.info("jobs.discovered", source="jsearch", count=len(jobs))
    return jobs
