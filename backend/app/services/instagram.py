from __future__ import annotations

import asyncio
import re
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Optional

import yt_dlp

from app.models.schemas import IngestedVideo, VideoMetadata
from app.services.transcription import transcribe_audio_file


_IG_PATTERNS = [
    r"instagram\.com/(?:reel|reels|p)/([A-Za-z0-9_-]+)",
]


def extract_reel_id(url: str) -> str:
    for pat in _IG_PATTERNS:
        m = re.search(pat, url)
        if m:
            return m.group(1)
    raise ValueError(f"Could not extract Instagram reel ID from: {url}")


def _fetch_metadata(url: str) -> dict:
    """yt-dlp metadata only. process=False for same reason as YouTube."""
    opts = {"quiet": True, "no_warnings": True, "skip_download": True}
    with yt_dlp.YoutubeDL(opts) as ydl:
        return ydl.extract_info(url, download=False, process=False)


def _download_audio(url: str, target_dir: Path) -> Path:
    """
    Download best audio track to disk, no transcoding.

    No FFmpegExtractAudio postprocessor — Instagram serves audio as m4a
    inside an mp4 container, Deepgram accepts that directly, and skipping
    ffmpeg keeps deploy artifacts ~200MB smaller.
    """
    out_template = str(target_dir / "%(id)s.%(ext)s")
    opts = {
        "quiet": True,
        "no_warnings": True,
        "format": "bestaudio[ext=m4a]/bestaudio/best",
        "outtmpl": out_template,
    }
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=True)
    if info.get("requested_downloads"):
        return Path(info["requested_downloads"][0]["filepath"])
    return next(target_dir.glob(f"{info['id']}.*"))


def _parse_ig_timestamp(ts: Optional[int]) -> Optional[datetime]:
    if not ts:
        return None
    try:
        return datetime.fromtimestamp(ts)
    except (TypeError, ValueError):
        return None


async def ingest_instagram(url: str) -> IngestedVideo:
    reel_id = extract_reel_id(url)
    info = await asyncio.to_thread(_fetch_metadata, url)

    likes = info.get("like_count") or 0
    views = info.get("view_count") or info.get("play_count") or 0
    comments = info.get("comment_count") or 0
    engagement_rate = ((likes + comments) / views * 100) if views else 0.0

    description = info.get("description") or ""
    hashtags = re.findall(r"#\w+", description)

    metadata = VideoMetadata(
        platform="instagram",
        video_id=reel_id,
        url=url,
        title=(description[:120] or f"Reel {reel_id}"),
        creator=info.get("uploader") or info.get("channel") or "",
        creator_followers=info.get("channel_follower_count"),
        upload_date=_parse_ig_timestamp(info.get("timestamp")),
        duration_seconds=info.get("duration") or 0,
        views=views,
        likes=likes,
        comments=comments,
        engagement_rate=round(engagement_rate, 3),
        hashtags=hashtags,
        thumbnail_url=info.get("thumbnail"),
    )

    with tempfile.TemporaryDirectory() as tmpdir:
        audio_path = await asyncio.to_thread(_download_audio, url, Path(tmpdir))
        transcript = await transcribe_audio_file(audio_path)

    return IngestedVideo(
        metadata=metadata,
        transcript=transcript,
        transcript_source="asr_deepgram",
    )