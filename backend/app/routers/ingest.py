from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.models.schemas import IngestRequest, IngestedVideo
from app.services import youtube, instagram
from app.services.indexing import index_video

router = APIRouter()


class IngestResponse(BaseModel):
    video: IngestedVideo
    chunks_indexed: int


def _route_by_url(url: str):
    if "instagram.com" in url:
        return instagram.ingest_instagram
    if "youtube.com" in url or "youtu.be" in url:
        return youtube.ingest_youtube
    return None


@router.post("", response_model=IngestResponse)
async def ingest(req: IngestRequest):
    url = str(req.url)
    handler = _route_by_url(url)
    if handler is None:
        raise HTTPException(status_code=400, detail="URL must be YouTube or Instagram")

    try:
        video = await handler(url)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {e}")

    # Indexing is best-effort: if Qdrant is down the user still has
    # metadata+transcript. Frontend can flag "RAG unavailable" instead
    # of failing the whole request.
    try:
        indexed = await index_video(video)
    except Exception as e:
        print(f"WARN: indexing failed for {video.metadata.video_id}: {e}")
        indexed = 0

    return IngestResponse(video=video, chunks_indexed=indexed)


@router.post("/youtube", response_model=IngestedVideo)
async def ingest_youtube_endpoint(req: IngestRequest):
    try:
        return await youtube.ingest_youtube(str(req.url))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"YouTube ingestion failed: {e}")


@router.post("/instagram", response_model=IngestedVideo)
async def ingest_instagram_endpoint(req: IngestRequest):
    try:
        return await instagram.ingest_instagram(str(req.url))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Instagram ingestion failed: {e}")