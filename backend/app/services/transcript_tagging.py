"""Lazily tags a transcript's entities the first time it's viewed.

Deliberately NOT part of the audio pipeline (services/pipeline.py) — that
would spend a Claude call on every recording whether or not anyone ever
reviews the transcript. Instead this runs at most once per transcript,
triggered from GET /encounters/{id}/transcript: if entities are already
present, it's a no-op, so repeated views don't repeat the spend.
"""
import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.transcript import Transcript, TranscriptEntity
from app.services.extraction.anthropic_provider import AnthropicExtractionProvider

logger = logging.getLogger(__name__)


async def ensure_transcript_tagged(db: AsyncSession, transcript: Transcript) -> None:
    if transcript.entities:
        return

    lines = transcript.raw_text.split("\n") if transcript.raw_text else []
    if not lines:
        return

    try:
        provider = AnthropicExtractionProvider()
        result = await provider.tag_lines(lines)
    except Exception:
        # Best-effort: the transcript itself is still shown to the doctor
        # even if highlighting couldn't be computed (e.g. no API key
        # configured, or a transient Claude error). Left untagged, this
        # will simply be retried on the next view since entities stays empty.
        logger.exception("Transcript entity tagging failed for transcript %s", transcript.id)
        return

    for tagged_line in result.lines:
        if not 0 <= tagged_line.line_index < len(lines):
            continue
        for entity in tagged_line.entities:
            transcript.entities.append(
                TranscriptEntity(
                    entity_type=entity.entity_type,
                    text=entity.text,
                    line_index=tagged_line.line_index,
                    start_offset=entity.start_offset,
                    end_offset=entity.end_offset,
                    confidence=entity.confidence,
                )
            )
    await db.flush()
