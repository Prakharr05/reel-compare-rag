from __future__ import annotations

import re
from datetime import datetime
from typing import Optional

import yt_dlp
from youtube_transcript_api import (
    YouTubeTranscriptApi,
    NoTranscriptFound,
    TranscriptsDisabled,
)

from app.models.schemas import IngestedVideo, TranscriptSegment, VideoMetadata


_YT_ID_PATTERNS = [
    r"(?:v=|/shorts/|youtu\.be/)([0-9A-Za-z_-]{11})",
]


def extract_video_id(url: str) -> str:
    for pat in _YT_ID_PATTERNS:
        m = re.search(pat, url)
        if m:
            return m.group(1)
    raise ValueError(f"Could not extract YouTube video ID from: {url}")


def _fetch_metadata(url: str) -> dict:
    """
    yt-dlp metadata without downloading the video.

    Note: skip_download=True does NOT skip format selection in yt-dlp's
    default flow, so on some YouTube Shorts the default 'bv*+ba/b' format
    string raises 'Requested format is not available'. We only need
    metadata, so pass process=False to short-circuit format resolution
    entirely. Roughly 2x faster too.
    """
    opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
    }
    with yt_dlp.YoutubeDL(opts) as ydl:
        return ydl.extract_info(url, download=False, process=False)


def _fetch_transcript_via_api(video_id: str) -> Optional[list[TranscriptSegment]]:
    """Free captions path. Returns None if unavailable — caller falls back to ASR."""
    try:
        raw = YouTubeTranscriptApi.get_transcript(
            video_id, languages=["en", "en-US", "en-GB", "hi"]
        )
        return [
            TranscriptSegment(text=seg["text"], start=seg["start"], duration=seg["duration"])
            for seg in raw
        ]
    except (NoTranscriptFound, TranscriptsDisabled):
        return None
    except Exception:
        return None


def _parse_yt_date(yyyymmdd: Optional[str]) -> Optional[datetime]:
    if not yyyymmdd:
        return None
    try:
        return datetime.strptime(yyyymmdd, "%Y%m%d")
    except ValueError:
        return None


def ingest_youtube(url: str) -> IngestedVideo:
    video_id = extract_video_id(url)
    info = _fetch_metadata(url)

    likes = info.get("like_count") or 0
    views = info.get("view_count") or 0
    comments = info.get("comment_count") or 0
    engagement_rate = ((likes + comments) / views * 100) if views else 0.0

    hashtags = re.findall(r"#\w+", info.get("description") or "")

    metadata = VideoMetadata(
        platform="youtube",
        video_id=video_id,
        url=url,
        title=info.get("title") or "",
        creator=info.get("uploader") or info.get("channel") or "",
        creator_followers=info.get("channel_follower_count"),
        upload_date=_parse_yt_date(info.get("upload_date")),
        duration_seconds=info.get("duration") or 0,
        views=views,
        likes=likes,
        comments=comments,
        engagement_rate=round(engagement_rate, 3),
        hashtags=hashtags,
        thumbnail_url=info.get("thumbnail"),
    )

    transcript = _fetch_transcript_via_api(video_id)
    transcript_source = "youtube_captions" if transcript else "asr_pending"

    return IngestedVideo(
        metadata=metadata,
        transcript=transcript or [],
        transcript_source=transcript_source,
    )