from __future__ import annotations

import hashlib
from typing import Optional

from qdrant_client import AsyncQdrantClient
from qdrant_client.http import models as qm

from app.config import settings
from app.services.embedding import EMBED_DIM


COLLECTION_NAME = "video_chunks"

_client: Optional[AsyncQdrantClient] = None


def get_client() -> AsyncQdrantClient:
    global _client
    if _client is None:
        _client = AsyncQdrantClient(
            url=settings.qdrant_url,
            api_key=settings.qdrant_api_key,
            prefer_grpc=False,
        )
    return _client


async def ensure_collection() -> None:
    """Idempotent. Safe to call on every startup."""
    client = get_client()
    cols = await client.get_collections()
    if any(c.name == COLLECTION_NAME for c in cols.collections):
        return

    await client.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=qm.VectorParams(size=EMBED_DIM, distance=qm.Distance.COSINE),
    )
    # Payload indexes on hot filter fields — every query filters by
    # video_id, so this is the critical perf knob.
    await client.create_payload_index(
        collection_name=COLLECTION_NAME,
        field_name="video_id",
        field_schema=qm.PayloadSchemaType.KEYWORD,
    )
    await client.create_payload_index(
        collection_name=COLLECTION_NAME,
        field_name="platform",
        field_schema=qm.PayloadSchemaType.KEYWORD,
    )


def _point_id(video_id: str, position: int) -> str:
    """Deterministic ID → re-ingest upserts instead of duplicating."""
    return hashlib.md5(f"{video_id}:{position}".encode()).hexdigest()


async def upsert_chunks(
    video_id: str,
    platform: str,
    creator: str,
    engagement_rate: float,
    chunks: list[dict],
    vectors: list[list[float]],
) -> int:
    if not chunks:
        return 0

    points = [
        qm.PointStruct(
            id=_point_id(video_id, chunk["position"]),
            vector=vec,
            payload={
                "video_id": video_id,
                "platform": platform,
                "creator": creator,
                "engagement_rate": engagement_rate,
                "position": chunk["position"],
                "start_time": chunk["start_time"],
                "end_time": chunk["end_time"],
                "text": chunk["text"],
            },
        )
        for chunk, vec in zip(chunks, vectors)
    ]
    await get_client().upsert(collection_name=COLLECTION_NAME, points=points)
    return len(points)


async def search(
    query_vector: list[float],
    video_ids: Optional[list[str]] = None,
    top_k: int = 6,
) -> list[dict]:
    """Semantic search, filtered to specific video(s) for compare-A-vs-B flows."""
    flt = None
    if video_ids:
        flt = qm.Filter(
            must=[qm.FieldCondition(key="video_id", match=qm.MatchAny(any=video_ids))]
        )

    result = await get_client().query_points(
        collection_name=COLLECTION_NAME,
        query=query_vector,
        query_filter=flt,
        limit=top_k,
        with_payload=True,
    )
    return [{"score": p.score, **p.payload} for p in result.points]