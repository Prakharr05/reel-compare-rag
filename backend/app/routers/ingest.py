from fastapi import APIRouter, HTTPException

from app.models.schemas import IngestRequest, IngestedVideo
from app.services import youtube

router = APIRouter()


@router.post("/youtube", response_model=IngestedVideo)
async def ingest_youtube_endpoint(req: IngestRequest):
    try:
        return youtube.ingest_youtube(str(req.url))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"YouTube ingestion failed: {e}")