from __future__ import annotations

from app.models.schemas import TranscriptSegment


def chunk_transcript(
    segments: list[TranscriptSegment],
    target_words: int = 80,
    overlap_segments: int = 1,
) -> list[dict]:
    """
    Group utterance-level segments into retrieval-friendly chunks.

    Each chunk preserves timestamps so we can cite back to a specific
    moment in the video ("seen at 0:14") rather than just 'somewhere
    in video A'.

    Defaults tuned for short-form video:
    - 100-400 word total transcripts → target_words=80 gives 3-5
      chunks per video. Enough granularity for retrieval to matter
      without producing trivially small vectors.
    - overlap_segments=1: consecutive chunks share their last
      utterance. Preserves context across boundaries (e.g., a hook
      that spans the cut).
    """
    if not segments:
        return []

    chunks: list[dict] = []
    buffer: list[TranscriptSegment] = []
    buffer_word_count = 0
    position = 0

    for seg in segments:
        buffer.append(seg)
        buffer_word_count += len(seg.text.split())

        if buffer_word_count >= target_words:
            chunks.append(_emit(buffer, position))
            position += 1
            buffer = buffer[-overlap_segments:] if overlap_segments else []
            buffer_word_count = sum(len(s.text.split()) for s in buffer)

    if buffer:
        chunks.append(_emit(buffer, position))

    return chunks


def _emit(buffer: list[TranscriptSegment], position: int) -> dict:
    return {
        "text": " ".join(s.text.strip() for s in buffer).strip(),
        "start_time": buffer[0].start,
        "end_time": buffer[-1].start + buffer[-1].duration,
        "position": position,
    }