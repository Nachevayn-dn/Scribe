"""Outgoing email — sharing an encounter's transcript or clinical note.

Uses Resend (console.resend.com — free tier, no domain required to start).
Without a verified sending domain, the `from` address is always Resend's
shared onboarding@resend.dev (see config.py's resend_from_email) — so the
doctor's or clinic's chosen identity is carried as Reply-To instead of being
spoofed in the From header. Once the clinic verifies its own domain in
Resend, set RESEND_FROM_EMAIL and real addresses work as the sender too.
"""
import logging

import resend

from app.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)


class EmailNotConfiguredError(RuntimeError):
    pass


def send_share_email(
    *,
    to: list[str],
    subject: str,
    body_text: str,
    reply_to: str | None = None,
) -> str:
    """Returns the Resend message id.

    Raises EmailNotConfiguredError if no RESEND_API_KEY is set, or
    RuntimeError if Resend rejects/fails the send.
    """
    if not settings.resend_api_key:
        raise EmailNotConfiguredError(
            "Email sending isn't set up yet — add a Resend API key under Integrations."
        )
    resend.api_key = settings.resend_api_key

    params: resend.Emails.SendParams = {
        "from": settings.resend_from_email,
        "to": to,
        "subject": subject,
        "text": body_text,
    }
    if reply_to:
        params["reply_to"] = reply_to

    try:
        result = resend.Emails.send(params)
    except Exception as exc:  # noqa: BLE001 — surface a clean failure, not a raw traceback
        logger.exception("Resend send failed")
        raise RuntimeError(f"Failed to send email: {exc}") from exc
    return result["id"]
