"""Email bodies. Plain text first -- it is what every client can show and what
spam filters trust -- with a light HTML version alongside."""
from __future__ import annotations

from datetime import date
from html import escape

from app.core.config import settings
from app.notify.email import Attachment, Email


def _link(path: str) -> str:
    base = settings.cors_origins[0] if settings.cors_origins else "http://localhost:5173"
    return f"{base.rstrip('/')}{path}"


def _html(heading: str, body: str, button_text: str, url: str) -> str:
    return f"""<!doctype html>
<html><body style="font-family:system-ui,Segoe UI,sans-serif;color:#0f172a;max-width:520px;margin:24px auto;padding:0 16px">
  <h2 style="margin:0 0 12px">{escape(heading)}</h2>
  <p style="line-height:1.5;color:#334155">{body}</p>
  <p style="margin:24px 0">
    <a href="{escape(url, quote=True)}" style="background:#0f172a;color:#fff;padding:10px 18px;border-radius:6px;text-decoration:none">{escape(button_text)}</a>
  </p>
  <p style="font-size:12px;color:#64748b">Or paste this link into your browser:<br>{escape(url)}</p>
</body></html>"""


def _fmt(d: date) -> str:
    return d.strftime("%d %b %Y")


def verification_email(*, to: str, name: str, token: str) -> Email:
    url = _link(f"/verify?token={token}")
    hours = settings.EMAIL_VERIFY_EXPIRE_HOURS
    return Email(
        to=to,
        subject="Confirm your email for Safarnama",
        text=(
            f"Hi {name},\n\n"
            f"Confirm your email address by opening this link:\n\n{url}\n\n"
            f"It expires in {hours} hours. If you did not sign up, ignore this email."
        ),
        html=_html(
            f"Hi {name}",
            f"Confirm your email address to get itinerary and trip reminder emails. "
            f"This link expires in {hours} hours.",
            "Confirm email",
            url,
        ),
    )


def password_reset_email(*, to: str, name: str, token: str) -> Email:
    url = _link(f"/reset-password?token={token}")
    minutes = settings.PASSWORD_RESET_EXPIRE_MINUTES
    return Email(
        to=to,
        subject="Reset your Safarnama password",
        text=(
            f"Hi {name},\n\n"
            f"We received a request to reset your password. Open this link to choose a new one:\n\n{url}\n\n"
            f"The link works once and expires in {minutes} minutes.\n"
            f"If you did not ask for this, ignore this email -- your password will not change."
        ),
        html=_html(
            "Reset your password",
            f"Hi {escape(name)}, we received a request to reset your password. "
            f"The link works once and expires in {minutes} minutes. "
            f"If you did not ask for this, you can ignore this email.",
            "Choose a new password",
            url,
        ),
    )


def password_changed_email(*, to: str, name: str) -> Email:
    url = _link("/forgot-password")
    return Email(
        to=to,
        subject="Your Safarnama password was changed",
        text=(
            f"Hi {name},\n\n"
            f"The password for your account was just changed, and you were signed out everywhere.\n\n"
            f"If this was not you, reset it now: {url}"
        ),
        html=_html(
            "Your password was changed",
            f"Hi {escape(name)}, the password for your account was just changed and every "
            f"device was signed out. If this was not you, reset it straight away.",
            "Reset password",
            url,
        ),
    )


def itinerary_ready_email(
    *, to: str, name: str, trip_id: str, destination: str, start: date, end: date,
) -> Email:
    url = _link(f"/trips/{trip_id}")
    dates = f"{_fmt(start)} – {_fmt(end)}"
    return Email(
        to=to,
        subject=f"Your {destination} itinerary is ready",
        text=(
            f"Hi {name},\n\nYour day-by-day plan for {destination} ({dates}) is ready:\n\n{url}\n"
        ),
        html=_html(
            f"Your {destination} plan is ready",
            f"Hi {escape(name)}, your day-by-day itinerary for "
            f"<b>{escape(destination)}</b> ({escape(dates)}) is ready.",
            "View itinerary",
            url,
        ),
    )


def trip_reminder_email(
    *, to: str, name: str, trip_id: str, destination: str, start: date, days_until: int,
) -> Email:
    url = _link(f"/trips/{trip_id}")
    when = "today" if days_until == 0 else "tomorrow" if days_until == 1 else f"in {days_until} days"
    return Email(
        to=to,
        subject=f"Your {destination} trip starts {when}",
        text=(
            f"Hi {name},\n\nYour trip to {destination} starts {when} ({_fmt(start)}).\n"
            f"Your itinerary:\n\n{url}\n"
        ),
        html=_html(
            f"{destination} starts {when}",
            f"Hi {escape(name)}, your trip to <b>{escape(destination)}</b> starts "
            f"{escape(when)} ({escape(_fmt(start))}). Your itinerary is one click away.",
            "Open itinerary",
            url,
        ),
    )


def itinerary_copy_email(
    *, to: str, name: str, trip_id: str, destination: str, start: date, end: date,
    pdf_name: str, pdf_bytes: bytes,
) -> Email:
    url = _link(f"/trips/{trip_id}")
    dates = f"{_fmt(start)} – {_fmt(end)}"
    return Email(
        to=to,
        subject=f"Your {destination} itinerary ({dates})",
        text=(
            f"Hi {name},\n\nYour itinerary for {destination} ({dates}) is attached as a PDF.\n"
            f"The latest version is always here:\n\n{url}\n"
        ),
        html=_html(
            f"{destination} itinerary",
            f"Hi {escape(name)}, your day-by-day plan for <b>{escape(destination)}</b> "
            f"({escape(dates)}) is attached as a PDF.",
            "Open in the app",
            url,
        ),
        attachments=(Attachment(filename=pdf_name, content=pdf_bytes),),
    )


def escalation_alert_email(
    *, to: str, user_name: str, user_email: str, reason: str, intent: str | None,
    excerpt: str, escalation_id: str,
) -> Email:
    why = {
        "negative_sentiment": "the customer sounds upset",
        "repeated_issue": "the same issue came up several times and the bot is not solving it",
    }.get(reason, reason)
    return Email(
        to=to,
        subject=f"[Support] {user_name} needs a person ({reason.replace('_', ' ')})",
        text=(
            f"A support chat was escalated because {why}.\n\n"
            f"Customer: {user_name} <{user_email}>\n"
            f"Topic: {intent or 'unknown'}\n"
            f"Escalation id: {escalation_id}\n\n"
            f"Their message:\n> {excerpt}\n"
        ),
    )


def trip_invitation_email(
    *, to: str, inviter: str, destination: str, start: date, end: date, trip_id: str, token: str,
) -> Email:
    url = _link(f"/join?trip={trip_id}&token={token}")
    dates = f"{_fmt(start)} – {_fmt(end)}"
    return Email(
        to=to,
        subject=f"{inviter} invited you to plan a trip to {destination}",
        text=(
            f"{inviter} is planning a trip to {destination} ({dates}) and wants you in.\n\n"
            f"Join and add what you'd like to do:\n\n{url}\n\n"
            "You'll need an account with this email address. If you weren't expecting "
            "this, ignore it."
        ),
        html=_html(
            f"Join {escape(inviter)}'s {escape(destination)} trip",
            f"{escape(inviter)} is planning <b>{escape(destination)}</b> ({escape(dates)}) and "
            "wants you in. Join to add what you'd like to do; the plan will balance "
            "everyone's preferences.",
            "Join the trip",
            url,
        ),
    )


def match_request_email(
    *, to: str, owner_name: str, requester_name: str, requester_email: str,
    destination: str, overlap_days: int, trip_id: str,
) -> Email:
    url = _link(f"/trips/{trip_id}")
    return Email(
        to=to,
        subject=f"{requester_name} is also going to {destination}",
        text=(
            f"Hi {owner_name},\n\n{requester_name} is travelling to {destination} on "
            f"dates that overlap yours by {overlap_days} day(s), and suggested planning "
            f"together. They chose to share their email: {requester_email}\n\n"
            f"If you'd like to, invite them from your trip page:\n\n{url}\n\n"
            "You're getting this because you made your trip discoverable. You can turn "
            "that off on the same page."
        ),
    )
