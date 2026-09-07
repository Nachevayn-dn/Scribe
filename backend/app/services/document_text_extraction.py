"""Pulls plain text out of an uploaded knowledge-base document at upload
time, so it can go straight into a Claude prompt later without re-parsing
the file on every call turn. Best-effort: returns None for anything it
doesn't recognize rather than failing the upload — the file is still
stored either way, just without prompt-ready text."""
import io
import logging

import docx
from pypdf import PdfReader

logger = logging.getLogger(__name__)

_PDF_MIME = "application/pdf"
_DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
_TEXT_MIMES = {"text/plain", "text/markdown", "text/csv"}


def extract_text(content: bytes, mime_type: str) -> str | None:
    try:
        if mime_type == _PDF_MIME:
            reader = PdfReader(io.BytesIO(content))
            return "\n\n".join(page.extract_text() or "" for page in reader.pages).strip() or None
        if mime_type == _DOCX_MIME:
            document = docx.Document(io.BytesIO(content))
            return "\n".join(p.text for p in document.paragraphs).strip() or None
        if mime_type in _TEXT_MIMES:
            return content.decode("utf-8", errors="replace").strip() or None
    except Exception:  # noqa: BLE001 — extraction is best-effort, never blocks the upload
        logger.exception("Text extraction failed for mime type %s", mime_type)
        return None
    return None
