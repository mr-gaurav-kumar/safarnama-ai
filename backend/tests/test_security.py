import pytest

from app.core.security import (
    MAX_PASSWORD_BYTES,
    InvalidTokenError,
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


def test_hash_is_not_the_password_and_is_salted():
    h1 = hash_password("correct horse battery")
    h2 = hash_password("correct horse battery")
    assert h1 != "correct horse battery"
    assert h1 != h2, "same password must not produce the same hash"


def test_verify_accepts_right_password_and_rejects_wrong():
    h = hash_password("correct horse battery")
    assert verify_password("correct horse battery", h) is True
    assert verify_password("wrong horse battery", h) is False


def test_overlong_password_is_rejected_not_truncated():
    """bcrypt ignores bytes past 72 -- without this guard two different long
    passwords would unlock the same account."""
    with pytest.raises(ValueError):
        hash_password("a" * (MAX_PASSWORD_BYTES + 1))


def test_verify_survives_a_corrupt_stored_hash():
    assert verify_password("anything", "not-a-bcrypt-hash") is False


def test_token_round_trip_carries_subject_and_role():
    token = create_access_token(subject="user-123", role="admin")
    payload = decode_access_token(token)
    assert payload["sub"] == "user-123"
    assert payload["role"] == "admin"
    assert payload["exp"] > payload["iat"]


def test_tampered_token_is_rejected():
    token = create_access_token(subject="user-123", role="user")
    tampered = token[:-4] + ("aaaa" if not token.endswith("aaaa") else "bbbb")
    with pytest.raises(InvalidTokenError):
        decode_access_token(tampered)
