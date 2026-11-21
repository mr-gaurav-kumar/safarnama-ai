"""Small admin commands.

    python -m app.cli make-admin you@example.com
    python -m app.cli remove-admin you@example.com
    python -m app.cli set-password you@example.com   (asks for the new password)
    python -m app.cli test-email you@example.com     (checks the SMTP settings)
    python -m app.cli seed-packages                  (adds the starter packages)
    python -m app.cli seed-photos                    (adds photos to starter packages that have none)
    python -m app.cli reembed                        (re-embeds every finished trip with the current model)
    python -m app.cli move-to-postgres               (copies everything into SUPABASE_DATABASE_URL)

Usually not needed: the ADMIN_EMAIL account becomes admin by itself when it
verifies its email or logs in. This is for doing it by hand from the server.
Only ADMIN_EMAIL can be made an admin.
"""
import getpass
import sys

from app.core.database import SessionLocal
from app.services import user_service


def main(argv: list[str]) -> int:
    if argv == ["seed-packages"]:
        return _seed_packages()
    if argv == ["seed-photos"]:
        return _seed_photos()
    if argv == ["reembed"]:
        return _reembed()
    if argv == ["move-to-postgres"]:
        from app.move_db import move_to_postgres

        return move_to_postgres()
    if len(argv) != 2 or argv[0] not in ("make-admin", "remove-admin", "set-password", "test-email"):
        print(__doc__)
        return 2
    command, email = argv
    if command == "set-password":
        return _set_password(email)
    if command == "test-email":
        return _test_email(email)
    if command == "make-admin" and not user_service.is_designated_admin_email(email):
        print("Only the address in ADMIN_EMAIL (.env) can be an admin.")
        return 1
    with SessionLocal() as db:
        user = user_service.get_by_email(db, email)
        if user is None:
            print(f"No account with the email {email}. Sign up first, then run this again.")
            return 1
        user.role = "admin" if command == "make-admin" else "user"
        if command == "make-admin":
            # An admin whose address was never confirmed would be a soft target.
            user.is_verified = True
        db.commit()
        print(f"{user.email} is now {'an admin' if user.role == 'admin' else 'a regular user'}.")
    return 0


def _set_password(email: str) -> int:
    from app.core.security import hash_password
    from app.schemas.user import check_password_rules

    with SessionLocal() as db:
        user = user_service.get_by_email(db, email)
        if user is None:
            print(f"No account with the email {email}.")
            return 1
        new = getpass.getpass("New password (typing is hidden): ")
        try:
            check_password_rules(new)
        except ValueError as exc:
            print(exc)
            return 1
        if getpass.getpass("Type it again: ") != new:
            print("The two passwords do not match. Nothing changed.")
            return 1
        user.password_hash = hash_password(new)
        db.commit()
        print(f"Password updated for {user.email}. Log in with the new password.")
    return 0


def _test_email(to: str) -> int:
    from app.core.config import settings
    from app.notify.email import Email, EmailDeliveryError, send_email, smtp_configured

    if not smtp_configured():
        print("SMTP is not fully set up. Fill SMTP_HOST, SMTP_USER and SMTP_PASS in .env, then try again.")
        return 1
    print(f"Sending a test email to {to} via {settings.SMTP_HOST}:{settings.SMTP_PORT} as {settings.SMTP_USER} ...")
    try:
        send_email(Email(
            to=to,
            subject="Safarnama -- SMTP test",
            text="If you can read this, email sending works. Password reset emails will arrive the same way.",
        ))
    except EmailDeliveryError as exc:
        print(f"FAILED: {exc}")
        print("Most common cause: SMTP_PASS is not a Google App Password, or 2-Step Verification is off.")
        return 1
    print("Sent. Check the inbox (and spam folder).")
    return 0


def _seed_packages() -> int:
    from sqlalchemy import select

    from app.data.seed_packages import PACKAGES
    from app.models.package import TravelPackage

    added = 0
    with SessionLocal() as db:
        existing = set(db.scalars(select(TravelPackage.title)).all())
        for data in PACKAGES:
            if data["title"] in existing:
                print(f"  skip  {data['title']} (already there)")
                continue
            from app.data.package_photos import credit_line, images_for
            desc = data.get("description", "")
            credit = credit_line(data["title"])
            db.add(TravelPackage(
                **{**data, "description": f"{desc}\n\n{credit}".strip() if credit else desc},
                images=images_for(data["title"]), is_active=True, owner_id=None,
            ))
            added += 1
            print(f"  added {data['title']}")
        db.commit()
    print(f"{added} package(s) added.")
    return 0


def _seed_photos() -> int:
    """Only fills packages that have no photos yet, so photos the admin
    uploaded or reordered are never replaced."""
    from sqlalchemy import select

    from app.data.package_photos import CREDIT_MARK, PHOTOS, credit_line, images_for
    from app.models.package import TravelPackage

    done = 0
    with SessionLocal() as db:
        for p in db.scalars(select(TravelPackage).where(TravelPackage.title.in_(list(PHOTOS)))).all():
            if p.images:
                print(f"  skip  {p.title} (already has photos)")
                continue
            p.images = images_for(p.title)
            if CREDIT_MARK not in (p.description or ""):
                p.description = f"{p.description}\n\n{credit_line(p.title)}".strip()
            done += 1
            print(f"  photos {p.title}")
        db.commit()
    print(f"{done} package(s) updated.")
    return 0



def _reembed() -> int:
    """After adding GEMINI_API_KEY (or changing the embedding model): rebuild
    every finished trip's memory vector, so old trips are found again."""
    from sqlalchemy import select

    from app.models.embedding import TripEmbedding
    from app.models.trip import Trip
    from app.rag import retrieval
    from app.rag.embeddings import current_model_name

    with SessionLocal() as db:
        trips = list(db.scalars(select(Trip).where(Trip.status == "completed")))
        print(f"Re-embedding {len(trips)} trip(s) with {current_model_name()}...")
        done = failed = 0
        for t in trips:
            try:
                row = retrieval.store_trip_embedding(db, t)
                done += row.model == current_model_name()
                failed += row.model != current_model_name()
            except Exception as exc:  # noqa: BLE001
                db.rollback()
                failed += 1
                print(f"  {t.destination}: {exc}")
        models = sorted({m for (m,) in db.execute(select(TripEmbedding.model).distinct())})
    print(f"Done: {done} with {current_model_name()}, {failed} fell back or failed. Models in memory now: {', '.join(models)}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
