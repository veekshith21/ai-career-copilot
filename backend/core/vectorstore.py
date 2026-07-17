"""Qdrant vector store operations for resumes, jobs, and interview questions."""
from __future__ import annotations
import uuid
import asyncio
from typing import Any
from qdrant_client import AsyncQdrantClient, QdrantClient
from qdrant_client.models import (
    Distance, VectorParams, PointStruct, Filter,
    FieldCondition, MatchValue, SearchRequest, ScoredPoint,
)
from core.config import get_settings
import structlog

logger = structlog.get_logger()
settings = get_settings()

VECTOR_DIM = 768  # nomic-embed-text dimension


# ─── Sync client (for startup collection init) ────────────────────────────────

def get_sync_client() -> QdrantClient:
    return QdrantClient(
        url=settings.qdrant_url,
        api_key=settings.qdrant_api_key or None,
        timeout=30,
    )


# ─── Async client (for request handlers) ─────────────────────────────────────

_async_client: AsyncQdrantClient | None = None


def get_async_client() -> AsyncQdrantClient:
    global _async_client
    if _async_client is None:
        _async_client = AsyncQdrantClient(
            url=settings.qdrant_url,
            api_key=settings.qdrant_api_key or None,
            timeout=60,
        )
    return _async_client


# ─── Collection Setup ─────────────────────────────────────────────────────────

COLLECTIONS = {
    settings.qdrant_resumes_collection: VECTOR_DIM,
    settings.qdrant_jobs_collection: VECTOR_DIM,
    settings.qdrant_interview_collection: VECTOR_DIM,
}


def init_collections() -> None:
    """Create Qdrant collections if they don't exist (called at startup)."""
    client = get_sync_client()
    existing = {c.name for c in client.get_collections().collections}
    for name, dim in COLLECTIONS.items():
        if name not in existing:
            client.create_collection(
                collection_name=name,
                vectors_config=VectorParams(size=dim, distance=Distance.COSINE),
            )
            logger.info("qdrant.collection.created", name=name)
        else:
            logger.info("qdrant.collection.exists", name=name)
    client.close()


# ─── Upsert Operations ────────────────────────────────────────────────────────

async def upsert_resume(
    session_id: str,
    embedding: list[float],
    payload: dict[str, Any],
) -> str:
    """Store a resume embedding. Returns the point ID."""
    client = get_async_client()
    point_id = str(uuid.uuid4())
    await client.upsert(
        collection_name=settings.qdrant_resumes_collection,
        points=[PointStruct(
            id=point_id,
            vector=embedding,
            payload={"session_id": session_id, **payload},
        )],
    )
    return point_id


async def upsert_job(
    job_id: str,
    embedding: list[float],
    payload: dict[str, Any],
) -> None:
    """Store a job embedding."""
    client = get_async_client()
    await client.upsert(
        collection_name=settings.qdrant_jobs_collection,
        points=[PointStruct(
            id=job_id,
            vector=embedding,
            payload=payload,
        )],
    )


async def upsert_interview_questions(
    questions: list[dict[str, Any]],
    company: str,
    role: str,
    embeddings: list[list[float]],
) -> None:
    """Store interview questions for RAG retrieval."""
    client = get_async_client()
    points = [
        PointStruct(
            id=str(uuid.uuid4()),
            vector=emb,
            payload={"company": company, "role": role, **q},
        )
        for q, emb in zip(questions, embeddings)
    ]
    await client.upsert(
        collection_name=settings.qdrant_interview_collection,
        points=points,
    )


# ─── Search Operations ────────────────────────────────────────────────────────

async def search_similar_jobs(
    query_embedding: list[float],
    top_k: int = 20,
    score_threshold: float = 0.4,
) -> list[ScoredPoint]:
    """Find jobs semantically similar to a resume or query."""
    client = get_async_client()
    results = await client.search(
        collection_name=settings.qdrant_jobs_collection,
        query_vector=query_embedding,
        limit=top_k,
        score_threshold=score_threshold,
        with_payload=True,
    )
    return results


async def search_interview_questions(
    query_embedding: list[float],
    company: str,
    role: str,
    top_k: int = 30,
) -> list[ScoredPoint]:
    """RAG: retrieve relevant interview questions for a company/role."""
    client = get_async_client()
    results = await client.search(
        collection_name=settings.qdrant_interview_collection,
        query_vector=query_embedding,
        limit=top_k,
        with_payload=True,
        query_filter=Filter(
            should=[
                FieldCondition(key="company", match=MatchValue(value=company)),
                FieldCondition(key="role", match=MatchValue(value=role)),
            ]
        ),
    )
    return results


async def delete_session_data(session_id: str) -> None:
    """Clean up all vectors for a session."""
    client = get_async_client()
    filt = Filter(must=[
        FieldCondition(key="session_id", match=MatchValue(value=session_id))
    ])
    await client.delete(
        collection_name=settings.qdrant_resumes_collection,
        points_selector=filt,
    )
