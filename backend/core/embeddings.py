"""Embedding generation via Ollama nomic-embed-text (local, no API cost)."""
from __future__ import annotations
import asyncio
from functools import lru_cache
import httpx
from core.config import get_settings
import structlog

logger = structlog.get_logger()
settings = get_settings()


async def embed_text(text: str) -> list[float]:
    """Generate embedding for a single text string via Ollama."""
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(
            f"{settings.ollama_base_url}/api/embeddings",
            json={"model": settings.ollama_embed_model, "prompt": text},
        )
        resp.raise_for_status()
        return resp.json()["embedding"]


async def embed_texts(texts: list[str]) -> list[list[float]]:
    """Batch embed multiple texts (sequential to avoid overloading Ollama)."""
    results = []
    for text in texts:
        emb = await embed_text(text)
        results.append(emb)
    return results


def embed_text_sync(text: str) -> list[float]:
    """Sync wrapper for contexts that can't use async."""
    return asyncio.run(embed_text(text))


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Compute cosine similarity between two vectors."""
    import math
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


# ─── Fallback: sentence-transformers if Ollama is unavailable ────────────────

_st_model = None


def _get_st_model():
    global _st_model
    if _st_model is None:
        from sentence_transformers import SentenceTransformer
        _st_model = SentenceTransformer("all-MiniLM-L6-v2")
    return _st_model


async def embed_text_fallback(text: str) -> list[float]:
    """Fallback to sentence-transformers (384-dim) if Ollama unavailable."""
    model = _get_st_model()
    embedding = model.encode(text, normalize_embeddings=True)
    # Pad to 768 dimensions for Qdrant collection compatibility
    padded = list(embedding) + [0.0] * (768 - len(embedding))
    return padded


async def safe_embed(text: str) -> list[float]:
    """Try Ollama first, fall back to sentence-transformers."""
    try:
        return await embed_text(text)
    except Exception as e:
        logger.warning("embedding.ollama_failed", error=str(e), fallback="sentence-transformers")
        return await embed_text_fallback(text)
