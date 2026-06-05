from fastapi import APIRouter, HTTPException

from app.models.schemas import IngestRequest, IngestedVideo
from app.services import youtube, instagram

router = APIRouter()


def _route_by_url(url: str):
    if "instagram.com" in url:
        return instagram.ingest_instagram
    if "youtube.com" in url or "youtu.be" in url:
        return youtube.ingest_youtube
    return None


@router.post("", response_model=IngestedVideo)
async def ingest(req: IngestRequest):
    """Single endpoint, routes by URL. This is what the frontend calls."""
    url = str(req.url)
    handler = _route_by_url(url)
    if handler is None:
        raise HTTPException(status_code=400, detail="URL must be YouTube or Instagram")
    try:
        return await handler(url)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {e}")


# Platform-specific endpoints kept for direct testing / debugging
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