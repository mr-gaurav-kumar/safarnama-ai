"""Background jobs.

Plain functions that take ids (never ORM objects -- those do not survive the
trip to a Celery worker) and open their own database session. The same function
runs inline in the API process or in a Celery worker; `app.tasks.dispatch`
decides which.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import select

from app.core import database
from app.core.config import settings
from app.core.security import create_email_verification_token, create_password_reset_token
from app.models.trip import Trip
from app.models.user import User
from app.notify import templates
from app.notify.email import EmailDeliveryError, send_email
from app.realtime.progress import publish_done, publish_progress
from app.services import trip_service

logger = logging.getLogger(__name__)

GENERIC_FAILURE = "Something went wrong while planning this trip. Please try again."


def run_trip_generation(trip_id: str) -> str:
    """Retrieve memory, generate the plan, store it -- reporting each step to
    anyone watching the trip's WebSocket. Returns the final status."""
    from app.tasks.dispatch import enqueue

    tid = uuid.UUID(trip_id)

    with database.SessionLocal() as db:
        trip = db.get(Trip, tid)
        if trip is None:
            logger.warning("Trip %s vanished before generation started", trip_id)
            return "missing"

        try:
            trip_service.attach_itinerary(
                db, trip,
                progress=lambda step, message, thoughts=None: publish_progress(tid, step, message, thoughts),
            )
        except Exception:  # noqa: BLE001 -- a crash must still end in a final state
            logger.exception("Generation crashed for trip %s", trip_id)
            db.rollback()
            trip = db.get(Trip, tid)
            if trip is not None:
                trip.status = "failed"
                # The traceback is in the log; the user gets a sentence.
                trip.error = GENERIC_FAILURE
                db.commit()

        status = trip.status if trip is not None else "failed"
        error = trip.error if trip is not None else GENERIC_FAILURE

    # Without this the browser would wait on a spinner forever.
    publish_done(tid, status, error)

    if status == "completed":
        enqueue(None, send_itinerary_ready_email, trip_id)
    return status


def send_password_reset_email(email_address: str) -> bool:
    """Looked up here, in the background, so the endpoint answers the same way
    -- and in the same time -- whether or not the address is registered."""
    from app.services import user_service

    with database.SessionLocal() as db:
        user = user_service.get_by_email(db, email_address)
        if user is None or user.is_blocked:
            return False
        email = templates.password_reset_email(
            to=user.email,
            name=user.name,
            token=create_password_reset_token(str(user.id), user.password_hash),
        )
    send_email(email)
    return True


def send_password_changed_email(user_id: str) -> bool:
    with database.SessionLocal() as db:
        user = db.get(User, uuid.UUID(user_id))
        if user is None:
            return False
        email = templates.password_changed_email(to=user.email, name=user.name)
    send_email(email)
    return True


def send_verification_email(user_id: str) -> bool:
    with database.SessionLocal() as db:
        user = db.get(User, uuid.UUID(user_id))
        if user is None or user.is_verified:
            return False
        email = templates.verification_email(
            to=user.email,
            name=user.name,
            token=create_email_verification_token(str(user.id), user.email),
        )
    send_email(email)
    return True


def send_itinerary_ready_email(trip_id: str) -> bool:
    with database.SessionLocal() as db:
        trip = db.get(Trip, uuid.UUID(trip_id))
        if trip is None:
            return False
        user = db.get(User, trip.user_id)
        # Only to confirmed addresses. Mailing whatever someone typed at sign-up
        # would let anyone use this app to send mail to a stranger.
        if user is None or not user.is_verified or user.is_blocked:
            return False
        email = templates.itinerary_ready_email(
            to=user.email, name=user.name, trip_id=str(trip.id),
            destination=trip.destination, start=trip.start_date, end=trip.end_date,
        )
    send_email(email)
    return True


def enrich_saved_plan(trip_id: str) -> bool:
    """Map pins and travel memory for a plan the traveller wrote, edited or copied."""
    from app.services import own_plan

    with database.SessionLocal() as db:
        trip = db.get(Trip, uuid.UUID(trip_id))
        if trip is None:
            return False
        own_plan.enrich(db, trip)
    return True


def send_itinerary_copy_email(trip_id: str, user_id: str | None = None) -> bool:
    """The "email me this itinerary" button: the plan as a PDF attachment."""
    from sqlalchemy.orm import selectinload

    from app.export.pdf import filename_for, render_itinerary_pdf

    with database.SessionLocal() as db:
        trip = db.scalar(
            select(Trip).where(Trip.id == uuid.UUID(trip_id)).options(selectinload(Trip.itinerary))
        )
        if trip is None or trip.itinerary is None:
            return False
        # The requester (owner or member); older callers passed only the trip.
        user = db.get(User, uuid.UUID(user_id)) if user_id else db.get(User, trip.user_id)
        if user is None or not user.is_verified or user.is_blocked:
            return False
        email = templates.itinerary_copy_email(
            to=user.email, name=user.name, trip_id=str(trip.id),
            destination=trip.destination, start=trip.start_date, end=trip.end_date,
            pdf_name=filename_for(trip), pdf_bytes=render_itinerary_pdf(trip, db=db, user_id=user.id),
        )
    send_email(email)
    return True


def send_escalation_alert(escalation_id: str) -> bool:
    """Tell the support inbox a chat needs a person."""
    from app.models.chat import SupportEscalation
    from app.notify.email import smtp_configured

    with database.SessionLocal() as db:
        esc = db.get(SupportEscalation, uuid.UUID(escalation_id))
        if esc is None:
            return False
        user = db.get(User, esc.user_id)
        if user is None:
            return False
        to = settings.ADMIN_EMAIL or settings.SMTP_USER
        if smtp_configured() and "@" not in to:
            logger.warning("Escalation %s not emailed: set ADMIN_EMAIL", escalation_id)
            return False
        email = templates.escalation_alert_email(
            to=to or "admin (set ADMIN_EMAIL in .env)",
            user_name=user.name, user_email=user.email, reason=esc.reason,
            intent=esc.intent, excerpt=esc.excerpt, escalation_id=str(esc.id),
        )
    send_email(email)
    return True


def send_trip_invitation(collaborator_id: str, token: str) -> bool:
    from app.models.group import TripCollaborator

    with database.SessionLocal() as db:
        c = db.get(TripCollaborator, uuid.UUID(collaborator_id))
        if c is None or c.status != "invited":
            return False
        trip = db.get(Trip, c.trip_id)
        inviter = db.get(User, c.invited_by)
        email = templates.trip_invitation_email(
            to=c.invited_email, inviter=inviter.name, destination=trip.destination,
            start=trip.start_date, end=trip.end_date, trip_id=str(trip.id), token=token,
        )
    send_email(email)
    return True


def send_match_request(from_trip_id: str, to_trip_id: str) -> bool:
    with database.SessionLocal() as db:
        mine = db.get(Trip, uuid.UUID(from_trip_id))
        theirs = db.get(Trip, uuid.UUID(to_trip_id))
        if mine is None or theirs is None:
            return False
        requester = db.get(User, mine.user_id)
        owner = db.get(User, theirs.user_id)
        if owner is None or not owner.is_verified or owner.is_blocked:
            return False
        overlap = (min(mine.end_date, theirs.end_date) - max(mine.start_date, theirs.start_date)).days + 1
        email = templates.match_request_email(
            to=owner.email, owner_name=owner.name.split()[0],
            requester_name=requester.name.split()[0], requester_email=requester.email,
            destination=theirs.destination, overlap_days=overlap, trip_id=str(theirs.id),
        )
    send_email(email)
    return True


def score_activity(user_id: str, ip: str = "") -> int:
    """Run the fraud rules and model for one user; returns flags raised."""
    from app.fraud.scorer import score_user

    with database.SessionLocal() as db:
        return len(score_user(db, uuid.UUID(user_id), ip or None))


def send_trip_reminders() -> int:
    """Email everyone whose trip starts within REMINDER_DAYS_AHEAD days.

    Looks at a window (today .. today + N) rather than exactly day N, so a day
    the scheduler missed is caught the next time it runs. `reminder_sent_at`
    makes it safe to run as often as you like -- nobody gets two.
    """
    today = datetime.now(ZoneInfo(settings.APP_TIMEZONE)).date()
    last_day = today + timedelta(days=settings.REMINDER_DAYS_AHEAD)
    sent = 0

    with database.SessionLocal() as db:
        due = db.execute(
            select(Trip, User)
            .join(User, User.id == Trip.user_id)
            .where(
                Trip.status == "completed",
                Trip.start_date >= today,
                Trip.start_date <= last_day,
                Trip.reminder_sent_at.is_(None),
                User.is_verified.is_(True),
                User.is_blocked.is_(False),
            )
            .order_by(Trip.start_date)
        ).all()

        for trip, user in due:
            email = templates.trip_reminder_email(
                to=user.email, name=user.name, trip_id=str(trip.id),
                destination=trip.destination, start=trip.start_date,
                days_until=(trip.start_date - today).days,
            )
            try:
                send_email(email)
            except EmailDeliveryError:
                # Not marked as sent, so the next run tries again.
                logger.exception("Reminder for trip %s failed", trip.id)
                continue
            # Committed one at a time: a failure on the tenth trip must not
            # cause the first nine to be sent again.
            trip.reminder_sent_at = datetime.now(timezone.utc)
            db.commit()
            sent += 1

    if sent:
        logger.info("Sent %d trip reminder(s)", sent)
    return sent
