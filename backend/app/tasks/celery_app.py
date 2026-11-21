"""Celery: the worker and the daily reminder schedule.

Only used when TASK_BACKEND=celery. Run with:

    celery -A app.tasks.celery_app worker --pool=solo --loglevel=info
    celery -A app.tasks.celery_app beat --loglevel=info

(--pool=solo because Celery's default process pool does not run on Windows.)

Each task is a thin wrapper round a function in `app.tasks.jobs`, so the job
logic is the same whether it runs here or inline in the API.
"""
from celery import Celery
from celery.schedules import crontab

from app.core.config import settings
from app.notify.email import EmailDeliveryError
from app.tasks import jobs

celery_app = Celery("travel_planner", broker=settings.CELERY_BROKER_URL)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    # Nothing reads task results -- progress goes over pub/sub and outcomes
    # live in Postgres -- so do not store them.
    task_ignore_result=True,
    timezone=settings.APP_TIMEZONE,
    enable_utc=True,
    # Acknowledge after the task finishes, so a worker that dies mid-generation
    # hands the job to another instead of dropping it.
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    broker_connection_retry_on_startup=True,
    beat_schedule={
        "trip-reminders-daily": {
            "task": "jobs.send_trip_reminders",
            "schedule": crontab(hour=8, minute=0),  # 08:00 in APP_TIMEZONE
        },
    },
)

_EMAIL_RETRY = {
    "autoretry_for": (EmailDeliveryError,),
    "retry_backoff": True,
    "retry_backoff_max": 600,
    "max_retries": 5,
}


@celery_app.task(name="jobs.run_trip_generation")
def run_trip_generation_task(trip_id: str) -> str:
    return jobs.run_trip_generation(trip_id)


@celery_app.task(name="jobs.send_verification_email", **_EMAIL_RETRY)
def send_verification_email_task(user_id: str) -> bool:
    return jobs.send_verification_email(user_id)


@celery_app.task(name="jobs.send_password_reset_email", **_EMAIL_RETRY)
def send_password_reset_email_task(email_address: str) -> bool:
    return jobs.send_password_reset_email(email_address)


@celery_app.task(name="jobs.send_password_changed_email", **_EMAIL_RETRY)
def send_password_changed_email_task(user_id: str) -> bool:
    return jobs.send_password_changed_email(user_id)


@celery_app.task(name="jobs.send_itinerary_ready_email", **_EMAIL_RETRY)
def send_itinerary_ready_email_task(trip_id: str) -> bool:
    return jobs.send_itinerary_ready_email(trip_id)


@celery_app.task(name="jobs.send_itinerary_copy_email", **_EMAIL_RETRY)
def send_itinerary_copy_email_task(trip_id: str, user_id: str | None = None) -> bool:
    return jobs.send_itinerary_copy_email(trip_id, user_id)


@celery_app.task(name="jobs.send_escalation_alert", **_EMAIL_RETRY)
def send_escalation_alert_task(escalation_id: str) -> bool:
    return jobs.send_escalation_alert(escalation_id)


@celery_app.task(name="jobs.send_trip_invitation", **_EMAIL_RETRY)
def send_trip_invitation_task(collaborator_id: str, token: str) -> bool:
    return jobs.send_trip_invitation(collaborator_id, token)


@celery_app.task(name="jobs.send_match_request", **_EMAIL_RETRY)
def send_match_request_task(from_trip_id: str, to_trip_id: str) -> bool:
    return jobs.send_match_request(from_trip_id, to_trip_id)


@celery_app.task(name="jobs.score_activity")
def score_activity_task(user_id: str, ip: str = "") -> int:
    return jobs.score_activity(user_id, ip)


@celery_app.task(name="jobs.enrich_saved_plan")
def enrich_saved_plan_task(trip_id: str) -> bool:
    return jobs.enrich_saved_plan(trip_id)


@celery_app.task(name="jobs.send_trip_reminders")
def send_trip_reminders_task() -> int:
    return jobs.send_trip_reminders()


_TASKS = {
    jobs.run_trip_generation: run_trip_generation_task,
    jobs.send_verification_email: send_verification_email_task,
    jobs.send_password_reset_email: send_password_reset_email_task,
    jobs.send_password_changed_email: send_password_changed_email_task,
    jobs.send_itinerary_ready_email: send_itinerary_ready_email_task,
    jobs.send_itinerary_copy_email: send_itinerary_copy_email_task,
    jobs.send_escalation_alert: send_escalation_alert_task,
    jobs.send_trip_invitation: send_trip_invitation_task,
    jobs.send_match_request: send_match_request_task,
    jobs.score_activity: score_activity_task,
    jobs.send_trip_reminders: send_trip_reminders_task,
    jobs.enrich_saved_plan: enrich_saved_plan_task,
}


def task_for(job):
    try:
        return _TASKS[job]
    except KeyError:
        raise LookupError(f"{job.__name__} has no Celery task registered") from None
