from __future__ import annotations

import asyncio
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import yt_dlp

from app.models.schemas import IngestedVideo, VideoMetadata
from app.services.apify import fetch_instagram_post
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
    opts = {"quiet": True, "no_warnings": True, "skip_download": True}
    with yt_dlp.YoutubeDL(opts) as ydl:
        return ydl.extract_info(url, download=False, process=False)


def _download_audio(url: str, target_dir: Path) -> Path:
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


def _parse_ig_timestamp(ts) -> Optional[datetime]:
    """yt-dlp returns Unix epoch int; Apify returns ISO 8601."""
    if not ts:
        return None
    if isinstance(ts, (int, float)):
        try:
            return datetime.fromtimestamp(ts, tz=timezone.utc)
        except (TypeError, ValueError, OSError):
            return None
    if isinstance(ts, str):
        try:
            return datetime.fromisoformat(ts.replace("Z", "+00:00"))
        except ValueError:
            return None
    return None


def _build_metadata(
    reel_id: str,
    url: str,
    ytdlp_info: dict,
    apify_data: Optional[dict],
) -> VideoMetadata:
    """
    Merge yt-dlp and Apify metadata. Apify wins for engagement metrics
    (views/likes/comments/follower_count) because those are the ones
    yt-dlp can't get reliably. yt-dlp fills any gaps if Apify failed.
    """
    apify = apify_data or {}

    # Engagement core — Apify preferred
    views = apify.get("videoPlayCount") or apify.get("videoViewCount") or 0
    likes = apify.get("likesCount") if apify else ytdlp_info.get("like_count") or 0
    comments = apify.get("commentsCount") if apify else ytdlp_info.get("comment_count") or 0
    likes = likes or 0
    comments = comments or 0

    # Creator
    creator = (
        apify.get("ownerFullName")
        or apify.get("ownerUsername")
        or ytdlp_info.get("uploader")
        or ytdlp_info.get("channel")
        or ""
    )

    # Follower count comes from Apify's parent data
    followers = None
    if apify.get("owner"):
        followers = apify["owner"].get("followers_count") or apify["owner"].get("followersCount")
    followers = followers or apify.get("ownerFollowersCount")

    # Description / caption / hashtags
    description = apify.get("caption") or ytdlp_info.get("description") or ""
    raw_hashtags = apify.get("hashtags")
    if raw_hashtags:
        hashtags = [h if h.startswith("#") else f"#{h}" for h in raw_hashtags]
    else:
        hashtags = re.findall(r"#\w+", description)

    # Time + duration + thumbnail
    upload_date = _parse_ig_timestamp(apify.get("timestamp")) or _parse_ig_timestamp(
        ytdlp_info.get("timestamp")
    )
    duration = apify.get("videoDuration") or ytdlp_info.get("duration") or 0
    thumbnail = apify.get("displayUrl") or ytdlp_info.get("thumbnail")

    engagement_rate = ((likes + comments) / views * 100) if views else 0.0

    return VideoMetadata(
        platform="instagram",
        video_id=reel_id,
        url=url,
        title=(description[:120] or f"Reel {reel_id}"),
        creator=creator,
        creator_followers=followers,
        upload_date=upload_date,
        duration_seconds=duration,
        views=views,
        likes=likes,
        comments=comments,
        engagement_rate=round(engagement_rate, 3),
        hashtags=hashtags,
        thumbnail_url=thumbnail,
    )


async def ingest_instagram(url: str) -> IngestedVideo:
    reel_id = extract_reel_id(url)

    # Run free + paid metadata fetches in parallel — they're both pure
    # network I/O so this halves wall-clock latency vs sequential.
    ytdlp_info, apify_data = await asyncio.gather(
        asyncio.to_thread(_fetch_metadata, url),
        fetch_instagram_post(url),
        return_exceptions=True,
    )

    if isinstance(ytdlp_info, Exception):
        ytdlp_info = {}
    if isinstance(apify_data, Exception):
        apify_data = None

    metadata = _build_metadata(reel_id, url, ytdlp_info, apify_data)

    # Audio path is always yt-dlp — Apify is metadata-only
    with tempfile.TemporaryDirectory() as tmpdir:
        audio_path = await asyncio.to_thread(_download_audio, url, Path(tmpdir))
        transcript = await transcribe_audio_file(audio_path)

    return IngestedVideo(
        metadata=metadata,
        transcript=transcript,
        transcript_source="asr_deepgram",
    )