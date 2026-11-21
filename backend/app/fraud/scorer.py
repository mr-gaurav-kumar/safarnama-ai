"""Risk scoring (§4.12) -- explainable rules first, a model for the rest.

Rules catch the patterns we can name. Each has a window, a threshold and a
fixed risk score, and the flag records exactly what was counted:

  trip_burst            5+ trips created in 10 minutes            0.80
  invite_burst          10+ invitations sent in an hour           0.70
  many_accounts_one_ip  3+ accounts signed up from one IP in 24h  0.70
  login_failures        5+ failed logins in 15 minutes            0.60
  ip_hopping            logins from 4+ different IPs in an hour   0.60

An Isolation Forest catches what the rules miss: it is fitted on every active
user's last-24h activity and flags users whose mix of behaviour is unusual
compared with everyone else, even if no single rule fires. It only runs once
there are enough users to say what "usual" is (MIN_POPULATION).

Nothing here blocks anyone. A flag is a prompt for a person to look -- the
admin dashboard's Fraud Flags tab -- because a false positive that locks out a
real traveller is worse than a review queue.
"""
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import distinct, func, select
from sqlalchemy.orm import Session

from app.models.risk import ActivityEvent, FraudFlag

logger = logging.getLogger(__name__)

FEATURES = ("trips_24h", "invites_24h", "failed_logins_24h", "distinct_ips_24h",
            "match_requests_24h", "accounts_on_ip_24h")
MIN_POPULATION = 20
FOREST_CONTAMINATION = 0.05
DEDUPE_HOURS = 24


@dataclass(frozen=True)
class Rule:
    reason: str
    kind: str
    window: timedelta
    threshold: int
    risk: float
    scope: str  # "user" -- count this user's events; "ip" -- accounts on the IP; "ips" -- distinct IPs


RULES = (
    Rule("trip_burst", "trip_created", timedelta(minutes=10), 5, 0.80, "user"),
    Rule("invite_burst", "invite_sent", timedelta(hours=1), 10, 0.70, "user"),
    Rule("many_accounts_one_ip", "signup", timedelta(hours=24), 3, 0.70, "ip"),
    Rule("login_failures", "login_failed", timedelta(minutes=15), 5, 0.60, "user"),
    Rule("ip_hopping", "login_ok", timedelta(hours=1), 4, 0.60, "ips"),
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _count(db: Session, rule: Rule, user_id: uuid.UUID, ip: str | None) -> tuple[int, dict]:
    since = _now() - rule.window
    base = (ActivityEvent.kind == rule.kind, ActivityEvent.created_at >= since)
    if rule.scope == "user":
        n = db.scalar(select(func.count()).select_from(ActivityEvent)
                      .where(*base, ActivityEvent.user_id == user_id)) or 0
        return n, {}
    if rule.scope == "ips":
        n = db.scalar(select(func.count(distinct(ActivityEvent.ip)))
                      .where(*base, ActivityEvent.user_id == user_id)) or 0
        return n, {}
    if ip is None:
        return 0, {}
    n = db.scalar(select(func.count(distinct(ActivityEvent.user_id)))
                  .where(*base, ActivityEvent.ip == ip)) or 0
    return n, {"ip": ip}


def _already_open(db: Session, user_id: uuid.UUID, reason: str) -> bool:
    return db.scalar(select(FraudFlag.id).where(
        FraudFlag.user_id == user_id, FraudFlag.reason == reason, FraudFlag.status == "open",
        FraudFlag.created_at >= _now() - timedelta(hours=DEDUPE_HOURS),
    )) is not None


def _flag(db: Session, user_id: uuid.UUID, reason: str, risk: float, details: dict,
          trip_id: uuid.UUID | None = None) -> FraudFlag | None:
    if _already_open(db, user_id, reason):
        return None
    row = FraudFlag(user_id=user_id, trip_id=trip_id, reason=reason,
                    risk_score=round(risk, 3), details=details, status="open")
    db.add(row)
    db.commit()
    logger.warning("Fraud flag %s for user %s (risk %.2f)", reason, user_id, risk)
    return row


# --- the model ---------------------------------------------------------------

def features_for(db: Session, user_id: uuid.UUID) -> list[float]:
    since = _now() - timedelta(hours=24)

    def n(kind: str) -> int:
        return db.scalar(select(func.count()).select_from(ActivityEvent).where(
            ActivityEvent.user_id == user_id, ActivityEvent.kind == kind,
            ActivityEvent.created_at >= since)) or 0

    ips = db.scalar(select(func.count(distinct(ActivityEvent.ip))).where(
        ActivityEvent.user_id == user_id, ActivityEvent.created_at >= since)) or 0
    signup_ip = db.scalar(select(ActivityEvent.ip).where(
        ActivityEvent.user_id == user_id, ActivityEvent.kind == "signup"))
    accounts_on_ip = db.scalar(select(func.count(distinct(ActivityEvent.user_id))).where(
        ActivityEvent.ip == signup_ip, ActivityEvent.kind == "signup",
        ActivityEvent.created_at >= since)) or 0 if signup_ip else 0
    return [n("trip_created"), n("invite_sent"), n("login_failed"), ips,
            n("match_request"), accounts_on_ip]


def forest_score(db: Session, user_id: uuid.UUID) -> tuple[float, dict] | None:
    """(risk 0-1, details) if this user's recent activity is anomalous, else None."""
    active = db.scalars(select(distinct(ActivityEvent.user_id)).where(
        ActivityEvent.user_id.is_not(None),
        ActivityEvent.created_at >= _now() - timedelta(days=7),
    )).all()
    if len(active) < MIN_POPULATION or user_id not in active:
        return None

    import numpy as np
    from sklearn.ensemble import IsolationForest

    matrix = np.array([features_for(db, uid) for uid in active], dtype=float)
    mine = np.array([features_for(db, user_id)], dtype=float)
    forest = IsolationForest(
        n_estimators=200, contamination=FOREST_CONTAMINATION, random_state=0,
    ).fit(matrix)
    if forest.predict(mine)[0] != -1:
        return None
    # decision_function < 0 means anomalous; map to a 0.5-1.0 risk.
    decision = float(forest.decision_function(mine)[0])
    risk = min(1.0, 0.5 + abs(decision))
    return risk, {
        "features": dict(zip(FEATURES, mine[0].tolist())),
        "population": len(active),
        "decision": round(decision, 4),
    }


# --- entry point ------------------------------------------------------------------

def score_user(db: Session, user_id: uuid.UUID, ip: str | None = None) -> list[FraudFlag]:
    flags: list[FraudFlag] = []
    for rule in RULES:
        count, extra = _count(db, rule, user_id, ip)
        if count >= rule.threshold:
            f = _flag(db, user_id, rule.reason, rule.risk, {
                "count": count, "threshold": rule.threshold,
                "window_minutes": int(rule.window.total_seconds() // 60), **extra,
            })
            if f:
                flags.append(f)

    try:
        scored = forest_score(db, user_id)
    except Exception:  # noqa: BLE001 -- the model is an extra, the rules stand alone
        logger.exception("Isolation Forest failed for user %s", user_id)
        scored = None
    if scored:
        f = _flag(db, user_id, "anomalous_activity", scored[0], scored[1])
        if f:
            flags.append(f)
    return flags
