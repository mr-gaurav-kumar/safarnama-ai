"""Reproducible metrics for the project write-up.

    cd backend
    python -m benchmarks.run_metrics

Every number is computed here, against a baseline, with fixed random seeds.
Runs offline: in-memory SQLite, the local embedder (no GEMINI_API_KEY), no
network. What each benchmark measures -- and what it does NOT -- is written
next to it; read that before quoting a number.

  1. Memory recall      RAG retrieval vs "use the most recent trip"
  2. Feedback loop      rating-weighted ranking vs similarity only
  3. Season model       Random Forest vs "guess from the month alone"
  4. Budget recommender full scoring vs style-similarity only
  5. Fraud detection    rules + Isolation Forest vs rules only (simulated)
  6. Rate limiting      a password-guessing burst against /auth/login
  7. Speed              think step and recommender latency
"""
from __future__ import annotations

import os

os.environ.update({
    "GEMINI_API_KEY": "", "GEOCODING_ENABLED": "false", "TASK_BACKEND": "inline",
    "SCHEDULER_ENABLED": "false", "SMTP_HOST": "", "RATE_LIMIT_ENABLED": "false",
    "JWT_SECRET_KEY": os.environ.get("JWT_SECRET_KEY") or "benchmark-only-secret-not-for-production-use-0123456789",
})

import random
import statistics
import time
import uuid
from collections import Counter
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import hash_password
from app.data.destinations import DESTINATIONS, REGION_MONTHS, STYLES
from app.models import Base
from app.models.group import TripFeedback
from app.models.risk import ActivityEvent
from app.models.trip import Trip
from app.models.user import User

SEED = 7
PW = None  # one hash for every synthetic user -- hashing is slow and irrelevant here


def fresh_db():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, autoflush=False)()


def make_user(db) -> User:
    global PW
    PW = PW or hash_password("benchmark-password-1")
    u = User(name="B", email=f"{uuid.uuid4().hex[:12]}@bench.local", password_hash=PW, is_verified=True)
    db.add(u)
    db.flush()
    return u


def pct(x: float) -> str:
    return f"{100 * x:.1f}%"


# --- 1 + 2. memory ----------------------------------------------------------------

def bench_memory(n_users=150, trips_per_user=8):
    """Each synthetic user has 8 past trips to 8 different destinations. A new
    request names one of those destinations (different month, length and
    budget). Hit@1 = the right past trip comes back first.
    Measures: can retrieval find the relevant memory. Does NOT measure plan
    quality, and uses the offline embedder, not Gemini's."""
    from app.rag import retrieval

    rng = random.Random(SEED)
    db = fresh_db()
    cases = []
    for _ in range(n_users):
        u = make_user(db)
        places = rng.sample(DESTINATIONS, trips_per_user)
        trips = []
        for k, d in enumerate(places):
            start = date(2025, 1, 1) + timedelta(days=40 * k + rng.randint(0, 20))
            t = Trip(user_id=u.id, destination=d.name, start_date=start,
                     end_date=start + timedelta(days=rng.randint(2, 6)),
                     budget=rng.choice([15000, 25000, 40000, 60000]), travelers=rng.randint(1, 4),
                     style_tags=rng.sample(list(STYLES), rng.randint(1, 2)), status="completed")
            db.add(t)
            db.flush()
            trips.append(t)
        db.commit()
        for t in trips:
            retrieval.store_trip_embedding(db, t)
        target = rng.choice(trips)
        q_start = date(2026, rng.randint(1, 12), rng.randint(1, 25))
        query = retrieval.summarise_request(
            destination=target.destination, start_date=q_start,
            end_date=q_start + timedelta(days=rng.randint(1, 6)),
            style_tags=list(target.style_tags), budget=float(rng.choice([20000, 35000, 50000])),
        )
        cases.append((u.id, target, trips, query))

    hits = recency = 0
    rr = []
    for uid, target, trips, query in cases:
        ranked = retrieval.find_similar_trips(db, user_id=uid, query_text=query,
                                              top_k=trips_per_user, min_similarity=-1)
        ids = [h.trip_id for h in ranked]
        hits += ids[0] == target.id
        rr.append(1 / (ids.index(target.id) + 1))
        recency += max(trips, key=lambda t: t.start_date).id == target.id
    n = len(cases)
    return {"queries": n, "hit1": hits / n, "mrr": statistics.mean(rr),
            "recency_hit1": recency / n, "random_hit1": 1 / trips_per_user}


def bench_feedback(n_users=150):
    """Each user has two past trips to the request's destination -- one in the
    same month as the request (a little MORE similar) and one in another
    month -- plus 4 unrelated trips. One of the two was rated 5/5, the other
    1/5, at random. Success = the loved one is retrieved first.
    Similarity alone ignores the rating, so it picks the loved trip only when
    the loved trip happens to be the closer one (about half the time)."""
    from app.rag import retrieval

    rng = random.Random(SEED + 1)
    db = fresh_db()
    cases = []
    for _ in range(n_users):
        u = make_user(db)
        d = rng.choice(DESTINATIONS)
        month = rng.randint(1, 12)
        other_month = (month + rng.randint(3, 8) - 1) % 12 + 1
        tags = rng.sample(list(STYLES), 2)

        def trip(dest, m, year):
            start = date(year, m, 5)
            t = Trip(user_id=u.id, destination=dest, start_date=start, end_date=start + timedelta(days=3),
                     budget=30000, travelers=2, style_tags=tags, status="completed")
            db.add(t)
            db.flush()
            return t
        close, far = trip(d.name, month, 2024), trip(d.name, other_month, 2025)
        others = [trip(x.name, rng.randint(1, 12), 2023)
                  for x in rng.sample([x for x in DESTINATIONS if x.name != d.name], 4)]
        loved, hated = (close, far) if rng.random() < 0.5 else (far, close)
        db.add_all([TripFeedback(trip_id=loved.id, user_id=u.id, rating=5),
                    TripFeedback(trip_id=hated.id, user_id=u.id, rating=1)])
        db.commit()
        for t in [close, far, *others]:
            retrieval.store_trip_embedding(db, t)
        q = date(2026, month, 10)
        query = retrieval.summarise_request(destination=d.name, start_date=q, end_date=q + timedelta(days=3),
                                            style_tags=tags, budget=30000)
        cases.append((u.id, loved.id, query))

    def run():
        return sum(retrieval.find_similar_trips(db, user_id=uid, query_text=q, top_k=6,
                                                min_similarity=-1)[0].trip_id == loved
                   for uid, loved, q in cases) / len(cases)

    weighted = run()
    saved = dict(retrieval.RATING_WEIGHT)
    retrieval.RATING_WEIGHT.update({k: 1.0 for k in retrieval.RATING_WEIGHT})
    try:
        plain = run()
    finally:
        retrieval.RATING_WEIGHT.update(saved)
    return {"users": len(cases), "loved_first": weighted, "baseline_loved_first": plain}


# --- 3. season model --------------------------------------------------------------

def bench_season():
    """Leave-one-destination-out: train on 67 places, predict all 12 months of
    the 68th, repeat for every place. Labels come from the CURATED climate
    table, so this measures generalising to an unseen place, not weather."""
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.metrics import f1_score
    from sklearn.model_selection import LeaveOneGroupOut

    from app.ml import season

    X, y, groups = season.training_set()
    pred, base = [None] * len(y), [None] * len(y)
    for train, test in LeaveOneGroupOut().split(X, y, groups):
        model = RandomForestClassifier(n_estimators=season.N_TREES, random_state=0, n_jobs=1)
        model.fit([X[i] for i in train], [y[i] for i in train])
        for i, p in zip(test, model.predict([X[i] for i in test])):
            pred[i] = p
        by_month: dict = {}
        for i in train:
            by_month.setdefault((round(X[i][4], 6), round(X[i][5], 6)), Counter())[y[i]] += 1
        for i in test:
            base[i] = by_month[(round(X[i][4], 6), round(X[i][5], 6))].most_common(1)[0][0]
    acc = sum(p == t for p, t in zip(pred, y)) / len(y)
    bacc = sum(p == t for p, t in zip(base, y)) / len(y)
    return {"rows": len(y), "places": len(set(groups)), "accuracy": acc, "baseline_accuracy": bacc,
            "macro_f1": f1_score(y, pred, average="macro"), "baseline_macro_f1": f1_score(y, base, average="macro")}


# --- 4. budget recommender -----------------------------------------------------------

def bench_recommender():
    """A grid of requests (budget x days x travellers x styles x month). For
    each, the top 6 from the full recommender vs the top 6 by style
    similarity alone. Judged against the curated data: affordable = on-ground
    money is at least the place's typical daily cost; good season = the
    climate table says ideal or pleasant; open = not a closed park."""
    from app.ml.budget_recommender import TRAVEL_SHARE, recommend
    from app.ml.features import all_destinations, cosine, style_vector

    db = fresh_db()
    rows = all_destinations(db)
    by_name = {r.name: r for r in rows}
    tag_sets = [[s] for s in STYLES] + [["culture", "food"], ["adventure", "nature"], ["relax", "nature"]]
    grid = [(b, d, t, tags, m) for b in (10000, 20000, 40000, 80000) for d in (3, 5)
            for t in (1, 2, 4) for tags in tag_sets for m in range(1, 13)]

    def judge(names, budget, days, travelers, month, tags):
        on_ground = budget / travelers / days * (1 - TRAVEL_SHARE)
        want = [1.0 if s in tags else 0.0 for s in STYLES]
        out = []
        for n in names:
            r = by_name[n]
            out.append((on_ground >= r.daily_cost,
                        REGION_MONTHS[r.region][month - 1] in ("ideal", "pleasant"),
                        month not in (r.closed_months or []),
                        cosine(want, style_vector(r))))
        return out

    ours, base = [], []
    empty = 0
    for budget, days, trav, tags, month in grid:
        res = recommend(db, budget=budget, days=days, travelers=trav, style_tags=tags, month=month, limit=6)
        names = [i["name"] for i in res["items"]]
        if not names:
            # Nothing anywhere is affordable (e.g. Rs 10,000 for 4 people for 5
            # days). Both sides are scored only on requests that CAN be met.
            empty += 1
            continue
        ours += judge(names, budget, days, trav, month, tags)
        want = [1.0 if s in tags else 0.0 for s in STYLES]
        top = sorted(rows, key=lambda r: -cosine(want, style_vector(r)))[:6]
        base += judge([r.name for r in top], budget, days, trav, month, tags)

    def share(picks, k):
        return sum(p[k] for p in picks) / len(picks)
    return {"requests": len(grid), "feasible_requests": len(grid) - empty,
            "affordable": share(ours, 0), "baseline_affordable": share(base, 0),
            "good_season": share(ours, 1), "baseline_good_season": share(base, 1),
            "open": share(ours, 2), "baseline_open": share(base, 2),
            "style_match": statistics.mean(p[3] for p in ours),
            "baseline_style_match": statistics.mean(p[3] for p in base)}


# --- 5. fraud ---------------------------------------------------------------------

def bench_fraud(n_normal=300):
    """SIMULATED population -- not real traffic. 300 ordinary users, 20 'loud'
    abusers (each crosses one rule), 20 'quiet' abusers (several behaviours,
    every one just under its rule's threshold). Same rules, features and
    Isolation Forest settings as app/fraud/scorer.py; the forest is fitted
    once on everyone's last-24h features (the app refits per check)."""
    import numpy as np
    from sklearn.ensemble import IsolationForest

    from app.fraud import scorer

    rng = random.Random(SEED + 2)
    db = fresh_db()
    now = datetime.now(timezone.utc)
    ip_n = iter(range(10, 10_000_000))

    def ip():
        n = next(ip_n)
        return f"10.{n // 65536 % 256}.{n // 256 % 256}.{n % 256}"

    def ev(u, kind, n, ips=None, minutes=50):
        for i in range(n):
            db.add(ActivityEvent(user_id=u.id, kind=kind, ip=ips[i % len(ips)] if ips else u._ip,
                                 created_at=now - timedelta(minutes=rng.uniform(0, minutes))))

    people = []
    for _ in range(n_normal):
        u = make_user(db)
        u._ip = ip()
        ev(u, "signup", 1, minutes=1400)
        ev(u, "login_ok", rng.randint(1, 3), ips=[u._ip, ip()] if rng.random() < 0.2 else None, minutes=1400)
        ev(u, "trip_created", rng.choice([0, 0, 1, 1, 2]), minutes=1400)
        ev(u, "invite_sent", rng.choice([0, 0, 0, 1, 2]), minutes=1400)
        ev(u, "login_failed", rng.choice([0, 0, 0, 1]), minutes=1400)
        ev(u, "match_request", rng.choice([0, 0, 0, 0, 1]), minutes=1400)
        people.append((u, False))

    loud_kinds = [("trip_created", 7, 8), ("invite_sent", 14, 50), ("login_failed", 8, 10)]
    for k in range(20):
        u = make_user(db)
        u._ip = ip()
        ev(u, "signup", 1, minutes=1400)
        if k % 5 == 3:     # account farm: three more accounts from this IP
            for _ in range(3):
                v = make_user(db)
                db.add(ActivityEvent(user_id=v.id, kind="signup", ip=u._ip, created_at=now - timedelta(hours=2)))
                people.append((v, True))
        elif k % 5 == 4:   # one account, many IPs
            ev(u, "login_ok", 5, ips=[ip() for _ in range(5)])
        else:
            kind, n, window = loud_kinds[k % 5]
            ev(u, kind, n, minutes=window)
        people.append((u, True))

    for _ in range(20):
        u = make_user(db)
        u._ip = ip()
        ev(u, "signup", 1, minutes=1400)
        ev(u, "trip_created", rng.randint(3, 4), minutes=600)
        ev(u, "invite_sent", rng.randint(7, 9), minutes=600)
        ev(u, "login_failed", rng.randint(3, 4), minutes=600)
        ev(u, "login_ok", 3, ips=[ip() for _ in range(3)], minutes=600)
        ev(u, "match_request", rng.randint(4, 8), minutes=600)
        people.append((u, True))
    db.commit()

    def rule_hit(u):
        sip = db.query(ActivityEvent.ip).filter(ActivityEvent.user_id == u.id, ActivityEvent.kind == "signup").scalar()
        return any(scorer._count(db, r, u.id, sip)[0] >= r.threshold for r in scorer.RULES)

    rules = [rule_hit(u) for u, _ in people]
    feats = np.array([scorer.features_for(db, u.id) for u, _ in people], dtype=float)
    forest = IsolationForest(n_estimators=200, contamination=scorer.FOREST_CONTAMINATION, random_state=0).fit(feats)
    iso = list(forest.predict(feats) == -1)
    both = [a or b for a, b in zip(rules, iso)]
    bad = [b for _, b in people]

    def rates(flags):
        tp = sum(f and b for f, b in zip(flags, bad))
        fp = sum(f and not b for f, b in zip(flags, bad))
        return tp / sum(bad), fp / (len(bad) - sum(bad)), tp / max(tp + fp, 1)
    r_rec, r_fpr, r_prec = rates(rules)
    c_rec, c_fpr, c_prec = rates(both)
    quiet = list(range(len(people) - 20, len(people)))
    return {"users": len(people), "abusers": sum(bad),
            "rules_recall": r_rec, "rules_fpr": r_fpr, "rules_precision": r_prec,
            "combined_recall": c_rec, "combined_fpr": c_fpr, "combined_precision": c_prec,
            "quiet_caught_by_rules": sum(rules[i] for i in quiet) / 20,
            "quiet_caught_combined": sum(both[i] for i in quiet) / 20}


# --- 6. rate limiting -----------------------------------------------------------------

def bench_ratelimit(attempts=100):
    """100 wrong-password logins from one IP within one minute, through the
    real middleware and endpoint."""
    from fastapi.testclient import TestClient

    from app.core import cache
    from app.core.config import settings
    from app.core.database import get_db
    from app.main import app

    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)

    def _db():
        s = factory()
        try:
            yield s
        finally:
            s.close()
    app.dependency_overrides[get_db] = _db
    cache._cache = cache.MemoryCache()
    settings.RATE_LIMIT_ENABLED = True
    try:
        with TestClient(app) as c:
            codes = Counter(c.post("/auth/login", json={"email": "victim@example.com", "password": "guess-123456"}).status_code
                            for _ in range(attempts))
    finally:
        settings.RATE_LIMIT_ENABLED = False
        app.dependency_overrides.clear()
    return {"attempts": attempts, "reached_auth": codes[401], "blocked": codes[429],
            "limit_per_min": settings.RATE_LIMIT_AUTH_PER_MIN}


# --- 7. speed ---------------------------------------------------------------------

def bench_speed(n=200):
    from app.ml import season
    from app.ml.budget_recommender import recommend
    from app.ml.think import think_about_trip

    db = fresh_db()
    t0 = time.perf_counter()
    season.build_model()
    train_ms = (time.perf_counter() - t0) * 1000
    season._model()
    think_about_trip(db, destination="Goa", start_date=date(2026, 7, 1), end_date=date(2026, 7, 4),
                     budget=30000, travelers=2, style_tags=["relax"])

    rng = random.Random(SEED + 3)
    think, rec = [], []
    for _ in range(n):
        d = rng.choice(DESTINATIONS)
        s = date(2026, rng.randint(1, 12), 1)
        t0 = time.perf_counter()
        think_about_trip(db, destination=d.name, start_date=s, end_date=s + timedelta(days=4),
                         budget=40000, travelers=2, style_tags=["culture"])
        think.append((time.perf_counter() - t0) * 1000)
    for _ in range(n // 4):
        t0 = time.perf_counter()
        recommend(db, budget=40000, days=4, travelers=2, style_tags=["food"], month=rng.randint(1, 12))
        rec.append((time.perf_counter() - t0) * 1000)

    def p(xs, q):
        return sorted(xs)[int(q * (len(xs) - 1))]
    return {"model_train_ms": train_ms, "think_p50_ms": p(think, 0.5), "think_p95_ms": p(think, 0.95),
            "recommend_p50_ms": p(rec, 0.5), "recommend_p95_ms": p(rec, 0.95)}


def main():
    import json
    import logging

    logging.disable(logging.WARNING)
    results = {}
    for name, fn in [("memory", bench_memory), ("feedback", bench_feedback), ("season", bench_season),
                     ("recommender", bench_recommender), ("fraud", bench_fraud),
                     ("ratelimit", bench_ratelimit), ("speed", bench_speed)]:
        t0 = time.perf_counter()
        results[name] = fn()
        print(f"[{name}] {time.perf_counter() - t0:.1f}s", flush=True)
        print(json.dumps({k: (round(v, 4) if isinstance(v, float) else v) for k, v in results[name].items()},
                         indent=2), flush=True)


if __name__ == "__main__":
    main()
