from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, HttpUrl


class TranscriptSegment(BaseModel):
    text: str
    start: float      # seconds from video start
    duration: float   # segment duration in seconds


class VideoMetadata(BaseModel):
    platform: Literal["youtube", "instagram"]
    video_id: str
    url: str
    title: str
    creator: str
    creator_followers: Optional[int] = None
    upload_date: Optional[datetime] = None
    duration_seconds: float = 0
    views: int = 0
    likes: int = 0
    comments: int = 0
    engagement_rate: float = 0.0
    hashtags: list[str] = []
    thumbnail_url: Optional[str] = None


class IngestedVideo(BaseModel):
    metadata: VideoMetadata
    transcript: list[TranscriptSegment]
    transcript_source: Literal[
        "youtube_captions", "instagram_asr", "asr_pending", "asr_deepgram"
    ]


class IngestRequest(BaseModel):
    url: HttpUrl