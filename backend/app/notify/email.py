"""Send an email -- or, with no SMTP configured, print it.

The console fallback is deliberate, not a stub: it lets sign-up and
verification work on a laptop with nothing set up, because the verification
link appears in the backend window ready to click.

Messages also land in a small in-memory OUTBOX in console mode, which is what
the tests read.
"""
from __future__ import annotations

import logging
import smtplib
import ssl
from collections import deque
from dataclasses import dataclass
from email.message import EmailMessage as MimeMessage
from email.utils import formataddr, parseaddr

from app.core.config import settings

logger = logging.getLogger(__name__)

SMTP_TIMEOUT_SECONDS = 20


@dataclass(frozen=True)
class Attachment:
    filename: str
    content: bytes
    mime_type: str = "application/pdf"


@dataclass(frozen=True)
class Email:
    to: str
    subject: str
    text: str
    html: str | None = None
    attachments: tuple[Attachment, ...] = ()


OUTBOX: deque[Email] = deque(maxlen=200)


class EmailDeliveryError(Exception):
    """Raised on an SMTP failure. The Celery task retries on it; the inline
    path logs it -- a failed email must never lose a user their itinerary."""


def smtp_configured() -> bool:
    # A host with a user but no password cannot log in (Gmail needs an App
    # Password), so fall back to printing rather than failing every email.
    if settings.SMTP_HOST and settings.SMTP_USER and not settings.SMTP_PASS:
        logger.warning("SMTP_PASS is empty -- printing emails instead of sending them")
        return False
    return bool(settings.SMTP_HOST)


def send_email(email: Email) -> None:
    if smtp_configured():
        _send_smtp(email)
    else:
        _send_console(email)


def _send_console(email: Email) -> None:
    OUTBOX.append(email)
    bar = "=" * 64
    # print, not just logging: uvicorn's default log level can hide INFO, and
    # the point of this fallback is that the link is visible.
    attached = "".join(
        f" [attachment: {a.filename}, {len(a.content):,} bytes]\n" for a in email.attachments
    )
    print(
        f"\n{bar}\n EMAIL (not sent -- SMTP is not fully set up in .env, printing instead)\n{bar}\n"
        f" To:      {email.to}\n Subject: {email.subject}\n\n{email.text}\n"
        f"{attached}{bar}\n",
        flush=True,
    )


def _send_smtp(email: Email) -> None:
    sender = settings.SMTP_FROM or settings.SMTP_USER

    message = MimeMessage()
    # SMTP_FROM may be a bare address or already "Name <address>".
    name, address = parseaddr(sender)
    message["From"] = formataddr((name or "Safarnama", address or sender))
    message["To"] = email.to
    message["Subject"] = email.subject
    message.set_content(email.text)
    if email.html:
        message.add_alternative(email.html, subtype="html")
    for a in email.attachments:
        maintype, _, subtype = a.mime_type.partition("/")
        message.add_attachment(a.content, maintype=maintype, subtype=subtype, filename=a.filename)

    context = ssl.create_default_context()
    try:
        if settings.SMTP_PORT == 465:
            with smtplib.SMTP_SSL(
                settings.SMTP_HOST, settings.SMTP_PORT,
                timeout=SMTP_TIMEOUT_SECONDS, context=context,
            ) as server:
                _login_and_send(server, message)
        else:
            with smtplib.SMTP(
                settings.SMTP_HOST, settings.SMTP_PORT, timeout=SMTP_TIMEOUT_SECONDS
            ) as server:
                server.starttls(context=context)
                _login_and_send(server, message)
    except (smtplib.SMTPException, OSError) as exc:
        raise EmailDeliveryError(f"Could not send '{email.subject}' to {email.to}: {exc}") from exc

    logger.info("Sent '%s' to %s", email.subject, email.to)


def _login_and_send(server: smtplib.SMTP, message: MimeMessage) -> None:
    if settings.SMTP_USER:
        server.login(settings.SMTP_USER, settings.SMTP_PASS)
    server.send_message(message)
