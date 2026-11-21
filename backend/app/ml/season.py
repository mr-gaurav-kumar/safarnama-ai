"""The month-and-region season model behind "Think on the Plan" (Phase 8).

A Random Forest that answers: what is <place> like in <month>?
  -> ideal | pleasant | hot | rainy | cold, with a confidence.

Inputs are physical -- latitude, longitude, altitude, coast or not, and the
month as a point on a circle (so December sits next to January). Training
rows are every curated destination x 12 months, labelled with its climate
region's month-by-month table in app/data/destinations.py.

Why a model and not just the table: the table only knows the places someone
wrote down. The forest generalises from where a place is, so a destination
added to destination_features later -- or one only known by its coordinates
-- gets a season reading too. Its confidence is lower where the curated
regions meet, which is honest: that is where the answer really is less sure.

The training data is CURATED (see destinations.py), so this is a sensible
prior, not a weather forecast.
"""
from __future__ import annotations

import math
from functools import lru_cache

from app.data.destinations import DESTINATIONS, REGION_MONTHS

N_TREES = 300


def features(lat: float, lng: float, altitude_m: float, coastal: bool, month: int) -> list[float]:
    angle = 2 * math.pi * (month - 1) / 12
    return [lat, lng, altitude_m / 1000.0, 1.0 if coastal else 0.0, math.sin(angle), math.cos(angle)]


def training_set() -> tuple[list[list[float]], list[str], list[str]]:
    """(X, y, groups) -- groups is the destination name, for grouped CV."""
    X: list[list[float]] = []
    y: list[str] = []
    groups: list[str] = []
    for d in DESTINATIONS:
        labels = REGION_MONTHS[d.region]
        for month in range(1, 13):
            X.append(features(d.lat, d.lng, d.altitude_m, d.coastal, month))
            y.append(labels[month - 1])
            groups.append(d.name)
    return X, y, groups


def build_model():
    from sklearn.ensemble import RandomForestClassifier

    X, y, _ = training_set()
    return RandomForestClassifier(n_estimators=N_TREES, random_state=0, n_jobs=1).fit(X, y)


@lru_cache(maxsize=1)
def _model():
    return build_model()


def _predict_rows(rows: list[list[float]]) -> list[tuple[str, float]]:
    model = _model()
    out = []
    for row in model.predict_proba(rows):
        best = int(row.argmax())
        out.append((str(model.classes_[best]), round(float(row[best]), 3)))
    return out


# A place does not move and the model is fixed for the life of the process, so
# every (place, month) answer is cached. One forest call per request instead of
# one per destination: the recommender asks about every place at once.
_cache: dict[tuple, tuple[str, float]] = {}
CACHE_LIMIT = 50_000


def predict_many(points: list[tuple[float, float, float, bool]], month: int) -> list[tuple[str, float]]:
    """[(label, confidence)] for each (lat, lng, altitude_m, coastal) in one month."""
    keys = [(round(lat, 4), round(lng, 4), round(alt, 1), bool(c), month) for lat, lng, alt, c in points]
    missing = [k for k in dict.fromkeys(keys) if k not in _cache]
    if missing:
        if len(_cache) + len(missing) > CACHE_LIMIT:
            _cache.clear()
        for k, answer in zip(missing, _predict_rows([features(*k) for k in missing])):
            _cache[k] = answer
    return [_cache[k] for k in keys]


def predict_months(lat: float, lng: float, altitude_m: float, coastal: bool,
                   months: list[int]) -> list[tuple[str, float]]:
    """[(label, confidence 0-1)] for each month, in order."""
    return [predict_many([(lat, lng, altitude_m, coastal)], m)[0] for m in months]


def predict(lat: float, lng: float, altitude_m: float, coastal: bool, month: int) -> tuple[str, float]:
    return predict_many([(lat, lng, altitude_m, coastal)], month)[0]
