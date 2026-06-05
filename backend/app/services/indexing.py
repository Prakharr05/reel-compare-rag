from __future__ import annotations

from app.models.schemas import IngestedVideo
from app.services.chunking import chunk_transcript
from app.services.embedding import embed_texts
from app.services.vectorstore import upsert_chunks


async def index_video(ingested: IngestedVideo) -> int:
    """Chunk → embed → upsert. Returns number of chunks indexed."""
    chunks = chunk_transcript(ingested.transcript)
    if not chunks:
        return 0

    vectors = embed_texts([c["text"] for c in chunks])

    return await upsert_chunks(
        video_id=ingested.metadata.video_id,
        platform=ingested.metadata.platform,
        creator=ingested.metadata.creator,
        engagement_rate=ingested.metadata.engagement_rate,
        chunks=chunks,
        vectors=vectors,
    )