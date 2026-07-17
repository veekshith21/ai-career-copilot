"""Application configuration via pydantic-settings."""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # LLM
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2"
    ollama_embed_model: str = "nomic-embed-text"

    # Vector DB
    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: str = ""

    # Job Discovery
    jsearch_api_key: str = ""
    jsearch_host: str = "jsearch.p.rapidapi.com"
    use_mock_jobs: bool = True

    # Database
    database_url: str = "sqlite+aiosqlite:///./data/career_copilot.db"

    # App
    secret_key: str = "dev-secret-change-in-production"
    environment: str = "development"
    log_level: str = "info"
    max_upload_size_mb: int = 10

    # ATS Thresholds
    ats_min_match_score: int = 40
    ats_target_score_low: int = 80   # Skip optimization for jobs already above this
    ats_target_score_high: int = 95

    # Collections
    qdrant_resumes_collection: str = "resumes"
    qdrant_jobs_collection: str = "jobs"
    qdrant_interview_collection: str = "interview_questions"


@lru_cache
def get_settings() -> Settings:
    return Settings()
