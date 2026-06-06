from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.services.chat import stream_chat


router = APIRouter()


class ChatRequest(BaseModel):
    session_id: str
    video_ids: list[str] = []  # empty list = search across all videos
    message: str


@router.post("")
async def chat(req: ChatRequest):
    """
    SSE chat endpoint.

    SSE over WebSockets:
    - One-way server→client streaming is the exact shape of LLM tokens
    - Works through CDNs/proxies without sticky-session pain
    - Native EventSource in browsers, no client library required
    - WebSockets would be heavier and harder to horizontally scale
    """
    return StreamingResponse(
        stream_chat(req.session_id, req.video_ids, req.message),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # disable nginx/Cloud Run buffering
        },
    )