"""Splits raw prose into sentence-ish lines.

Mirrors frontend/src/components/notes/TranscriptViewer.tsx's regex exactly
— keep the two in sync. Used once, at transcript-persist time, so line
numbering stays stable for entity tagging and line-level editing.
"""
import re

_SENTENCE_SPLIT = re.compile(r"""(?<=[.!?])\s+(?=[A-Z0-9"'])""")


def split_into_lines(text: str) -> list[str]:
    stripped = text.strip()
    if not stripped:
        return []
    return [line.strip() for line in _SENTENCE_SPLIT.split(stripped) if line.strip()]
