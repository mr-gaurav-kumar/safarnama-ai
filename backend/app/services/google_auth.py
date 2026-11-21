"""Sign in with Google: check the ID token Google gave the browser.

The browser gets a signed ID token (a JWT) from Google Identity Services and
sends it to POST /auth/google. Nothing in it is trusted until Google's library
has checked the signature against Google's public keys, the expiry, the issuer
and that the token was issued for OUR client id. Free -- no billing needed.
"""
from __future__ import annotations

from dataclasses import dataclass

from app.core.config import settings

ISSUERS = {"accounts.google.com", "https://accounts.google.com"}


class GoogleAuthError(Exception):
    pass


@dataclass
class GoogleIdentity:
    sub: str  # Google's permanent account id -- what we key on, never the email
    email: str
    name: str


def enabled() -> bool:
    return bool(settings.GOOGLE_CLIENT_ID)


def verify(credential: str) -> GoogleIdentity:
    if not enabled():
        raise GoogleAuthError("Google sign-in is not set up on this server")
    try:
        from google.auth.transport import requests as google_requests
        from google.oauth2 import id_token

        claims = id_token.verify_oauth2_token(
            credential, google_requests.Request(), settings.GOOGLE_CLIENT_ID, clock_skew_in_seconds=10,
        )
    except Exception as exc:  # noqa: BLE001 -- any failure means "not a valid Google token"
        raise GoogleAuthError("Google sign-in failed. Please try again.") from exc

    if claims.get("iss") not in ISSUERS:
        raise GoogleAuthError("Google sign-in failed. Please try again.")
    # An unverified Google email proves nothing about who owns the address.
    if not claims.get("email") or not claims.get("email_verified"):
        raise GoogleAuthError("Your Google account's email is not verified.")
    return GoogleIdentity(
        sub=str(claims["sub"]),
        email=str(claims["email"]).lower(),
        name=str(claims.get("name") or claims["email"].split("@")[0])[:120],
    )
