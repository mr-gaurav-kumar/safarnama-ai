"""Single source of truth for configuration.

Every value comes from the environment (.env in development). Nothing else in
the codebase reads os.environ directly -- import `settings` from here instead,
so a new setting is declared in exactly one place.
"""
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# config.py -> core -> app -> backend -> project root
BACKEND_DIR = Path(__file__).resolve().parents[2]
PROJECT_ROOT = BACKEND_DIR.parent


class Settings(BaseSettings):
    # Absolute paths, so the app reads the same .env whether it is started
    # from the project root or from backend/. A backend/.env, if one exists,
    # wins -- handy for a throwaway local override.
    model_config = SettingsConfigDict(
        env_file=(PROJECT_ROOT / ".env", BACKEND_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- app ---
    APP_NAME: str = "Safarnama"
    # Uploaded images (package photos) live here and are served at /media.
    MEDIA_DIR: Path = BACKEND_DIR / "media"
    MAX_IMAGE_MB: int = 5
    # Travellers' ID documents, encrypted. Never served as static files.
    PRIVATE_DOCS_DIR: Path = BACKEND_DIR / "private_documents"
    # Fernet key(s) for the document vault, comma-separated (first encrypts,
    # all decrypt -- for rotation). Empty = the vault is switched off.
    # Generate: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    # Losing it makes saved documents unreadable: keep a copy somewhere safe.
    DOCUMENT_ENCRYPTION_KEY: str = ""
    DEBUG: bool = True

    # --- database ---
    DATABASE_URL: str = "postgresql+psycopg://postgres:@localhost:5432/travelplanner"

    # --- background jobs ---
    # inline: jobs run inside the API process after the response is sent. No
    #         Redis, no worker -- what you want on a laptop.
    # celery: jobs go to a Celery worker through Redis, and progress travels
    #         over Redis pub/sub. What you deploy.
    TASK_BACKEND: Literal["inline", "celery"] = "inline"

    # Inline mode only: run the daily reminder job on a timer inside the API.
    # In Celery mode, Celery Beat does this instead.
    SCHEDULER_ENABLED: bool = True

    APP_TIMEZONE: str = "Asia/Kolkata"

    # --- cache / broker ---
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"

    # --- auth ---
    # No usable default on purpose: a key everyone can read in this file would
    # let anyone sign a login token for any account. Startup fails instead.
    JWT_SECRET_KEY: str = ""
    # HMAC only. Pinning it means a token can never pick its own algorithm.
    JWT_ALGORITHM: Literal["HS256", "HS384", "HS512"] = "HS256"
    JWT_EXPIRE_MINUTES: int = 30

    # Sign in with Google (free). Web client id from Google Cloud Console ->
    # APIs & Services -> Credentials. Empty = the Google button is hidden.
    GOOGLE_CLIENT_ID: str = ""

    # Live 7-day forecasts in the travel assistant (Open-Meteo: free, no key).
    LIVE_WEATHER_ENABLED: bool = True

    # --- refresh tokens (keep people logged in across page reloads) ---
    # The access token stays short-lived and in memory. A long-lived refresh
    # token lives in an httpOnly cookie that page scripts cannot read.
    REFRESH_TOKEN_DAYS: int = 14
    # Two tabs refreshing at the same moment both present the same token; the
    # second arrives just after the first rotated it. Inside this window that
    # is treated as a race, not as a stolen token.
    REFRESH_REUSE_GRACE_SECONDS: int = 30
    REFRESH_COOKIE_NAME: str = "tp_refresh"
    # The path the BROWSER uses to reach the auth routes. In development Vite
    # serves the API under /api, so /api/auth. Set to /auth if the API is
    # served without that prefix.
    REFRESH_COOKIE_PATH: str = "/api/auth"
    # True in production (HTTPS). With the frontend and API on different
    # sites, also set REFRESH_COOKIE_SAMESITE=none.
    REFRESH_COOKIE_SECURE: bool = False
    REFRESH_COOKIE_SAMESITE: Literal["strict", "lax", "none"] = "strict"

    # --- embeddings / LLM ---
    GEMINI_API_KEY: str = ""
    LLM_MODEL: str = "gemini-2.5-flash"
    EMBEDDING_MODEL: str = "gemini-embedding-001"
    EMBEDDING_DIM: int = 768

    # --- memory (RAG retrieval) ---
    # How many past trips to feed the planner, and how similar one must be to
    # count. Below the floor a past trip is noise, not memory.
    MEMORY_TOP_K: int = 3
    MEMORY_MIN_SIMILARITY: float = 0.25

    # --- rate limiting (§4.13) ---
    # Requests per minute. The document suggests 5-10/min per user; that fits
    # expensive actions but not page loads, where one dashboard view makes
    # several reads -- so reads and writes get separate, larger buckets and the
    # expensive or abusable actions get the tight ones.
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_AUTH_PER_MIN: int = 10      # login/signup/verify, per IP
    RATE_LIMIT_REFRESH_PER_MIN: int = 30   # session refresh, per IP
    RATE_LIMIT_TRIPS_PER_MIN: int = 5      # new trips / replans, per user
    RATE_LIMIT_ASSISTANT_PER_MIN: int = 20  # travel assistant questions, per user
    RATE_LIMIT_WRITES_PER_MIN: int = 60    # other changes, per user
    RATE_LIMIT_READS_PER_MIN: int = 300    # everything else, per user

    # --- support chat ---
    # The ONE admin account. Only a verified account with exactly this address
    # can be an admin -- nobody can be promoted to admin any other way, not
    # from the dashboard and not from the command line. Escalated support
    # chats are emailed here too (falls back to SMTP_USER when empty). Leave
    # empty and there is no admin at all.
    ADMIN_EMAIL: str = ""

    @property
    def admin_email(self) -> str:
        return self.ADMIN_EMAIL.strip().lower()
    CHAT_MAX_CHARS: int = 1000
    CHAT_MESSAGES_PER_MINUTE: int = 10
    # A trip still "processing" after this long is treated as stuck.
    STUCK_TRIP_MINUTES: int = 5

    # --- live train search (RapidAPI "IRCTC" API, free plan) ---
    # Empty key = live search off; the Trains page falls back to opening IRCTC.
    RAPIDAPI_KEY: str = ""
    RAPIDAPI_IRCTC_HOST: str = "irctc1.p.rapidapi.com"

    # --- maps / geocoding ---
    # Nominatim (OpenStreetMap) turns place names into coordinates for the map.
    # Its usage policy asks for an identifying User-Agent, at most one request a
    # second, and caching -- all three are enforced in app/geo/geocode.py.
    GEOCODING_ENABLED: bool = True
    GEOCODER_URL: str = "https://nominatim.openstreetmap.org/search"
    GEOCODER_USER_AGENT: str = "AITravelPlanner/0.4 (student project)"
    # A place further than this from the destination is treated as a wrong match
    # (another "City Palace" in another city) and left off the map.
    GEOCODE_MAX_KM_FROM_DESTINATION: float = 150.0

    # --- external APIs ---
    OPENWEATHER_API_KEY: str = ""
    AMADEUS_CLIENT_ID: str = ""
    AMADEUS_CLIENT_SECRET: str = ""
    DATA_GOV_API_KEY: str = ""

    # --- email ---
    # With SMTP_HOST empty, emails are printed to the backend console instead of
    # sent -- including the verification link, so sign-up still works locally.
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASS: str = ""
    SMTP_FROM: str = ""  # defaults to SMTP_USER

    EMAIL_VERIFY_EXPIRE_HOURS: int = 24
    PASSWORD_RESET_EXPIRE_MINUTES: int = 30
    REMINDER_DAYS_AHEAD: int = 2

    # --- cors ---
    FRONTEND_URL: str = "http://localhost:5173"

    @field_validator("DATABASE_URL")
    @classmethod
    def _db_driver(cls, v: str) -> str:
        """Hosts like Supabase hand out postgres:// or postgresql:// links; the
        app talks to Postgres through psycopg 3, so name that driver."""
        v = v.strip()
        for prefix in ("postgres://", "postgresql://"):
            if v.startswith(prefix):
                return "postgresql+psycopg://" + v[len(prefix):]
        return v

    @field_validator("JWT_SECRET_KEY")
    @classmethod
    def _strong_secret(cls, v: str) -> str:
        if len(v.strip()) < 32 or v.strip() == "change-me-in-env":
            raise ValueError(
                "JWT_SECRET_KEY in .env is missing or too short (needs 32+ characters). Generate one with: "
                'python -c "import secrets; print(secrets.token_urlsafe(48))"'
            )
        return v.strip()

    @property
    def cors_origins(self) -> list[str]:
        """Explicit origins only -- never '*', per the document's security notes."""
        return [o.strip() for o in self.FRONTEND_URL.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
