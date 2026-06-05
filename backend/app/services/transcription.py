from __future__ import annotations

import mimetypes
from pathlib import Path

import httpx

from app.config import settings
from app.models.schemas import TranscriptSegment


DEEPGRAM_URL = "https://api.deepgram.com/v1/listen"


def _content_type_for(path: Path) -> str:
    mime, _ = mimetypes.guess_type(str(path))
    if mime and (mime.startswith("audio") or mime == "video/mp4"):
        return mime
    return "audio/mp4"  # Deepgram-safe default


async def transcribe_audio_file(audio_path: Path) -> list[TranscriptSegment]:
    """
    Transcribe a local audio file via Deepgram Nova-2.

    Returns utterance-level segments (not word-level). Reasons:
    1. Deepgram's VAD groups semantically coherent chunks that embed
       better than word fragments (a 4-word utterance has more retrieval
       signal than 4 separate single-word vectors).
    2. ~10x smaller response payload, ~10x fewer chunks downstream,
       which compounds into real cost savings at 1000 creators/day.
    """
    if not settings.deepgram_api_key:
        raise RuntimeError("DEEPGRAM_API_KEY not set in .env")

    headers = {
        "Authorization": f"Token {settings.deepgram_api_key}",
        "Content-Type": _content_type_for(audio_path),
    }
    params = {
        "model": "nova-2",
        "smart_format": "true",
        "utterances": "true",
        "punctuate": "true",
    }

    audio_bytes = audio_path.read_bytes()

    async with httpx.AsyncClient(timeout=120.0) as client:
        resp = await client.post(
            DEEPGRAM_URL, headers=headers, params=params, content=audio_bytes
        )
        resp.raise_for_status()
        data = resp.json()

    utterances = data.get("results", {}).get("utterances") or []
    return [
        TranscriptSegment(
            text=u["transcript"],
            start=u["start"],
            duration=u["end"] - u["start"],
        )
        for u in utterances
    ]