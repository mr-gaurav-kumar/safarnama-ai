"""The same job can run inline or on Celery; the switch is one setting."""
from app.core.config import settings
from app.tasks import jobs
from app.tasks.dispatch import enqueue


def test_celery_mode_sends_the_job_to_its_task(monkeypatch):
    from app.tasks import celery_app

    sent = []
    task = celery_app.task_for(jobs.run_trip_generation)
    monkeypatch.setattr(settings, "TASK_BACKEND", "celery")
    monkeypatch.setattr(task, "delay", lambda *args: sent.append(args))

    enqueue(None, jobs.run_trip_generation, "trip-123")
    assert sent == [("trip-123",)]


def test_every_job_has_a_celery_task_and_the_beat_runs_reminders():
    from app.tasks.celery_app import celery_app, task_for

    for job in (jobs.run_trip_generation, jobs.send_verification_email,
                jobs.send_itinerary_ready_email, jobs.send_trip_reminders):
        assert task_for(job).name == f"jobs.{job.__name__}"

    beat = celery_app.conf.beat_schedule["trip-reminders-daily"]
    assert beat["task"] == "jobs.send_trip_reminders"


def test_inline_failures_are_logged_not_raised(caplog):
    def broken():
        raise RuntimeError("boom")

    enqueue(None, broken)  # must not raise
    assert "broken" in caplog.text
