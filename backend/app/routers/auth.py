"""Authentication endpoints -- §4.1 and §6 of the project document."""
import secrets
import uuid

from fastapi import APIRouter, BackgroundTasks, Cookie, Depends, File, Header, HTTPException, Request, Response, UploadFile, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.security import (
    InvalidTokenError,
    create_access_token,
    decode_email_verification_token,
    decode_password_reset_token,
    hash_password,
    password_fingerprint,
    verify_password,
)
from app.models.business import BusinessProfile
from app.models.user import User
from app.schemas.business import BusinessSignupRequest
from app.schemas.user import (
    ChangePasswordRequest,
    ForgotPasswordRequest,
    ProfileUpdate,
    LoginRequest,
    ResetPasswordRequest,
    SignupRequest,
    TokenResponse,
    UserRead,
)
from app.fraud import events
from app.services import business_service, google_auth, session_service, user_service
from app.tasks import jobs
from app.tasks.dispatch import enqueue

router = APIRouter(prefix="/auth", tags=["auth"])


class VerifyEmailRequest(BaseModel):
    token: str


def _token_response(user: User) -> TokenResponse:
    return TokenResponse(
        access_token=create_access_token(subject=str(user.id), role=user.role),
        user=UserRead.model_validate(user),
    )


def _set_refresh_cookie(response: Response, raw: str) -> None:
    response.set_cookie(
        key=settings.REFRESH_COOKIE_NAME,
        value=raw,
        max_age=settings.REFRESH_TOKEN_DAYS * 24 * 3600,
        path=settings.REFRESH_COOKIE_PATH,
        httponly=True,  # page scripts can never read it -- the point of the cookie
        secure=settings.REFRESH_COOKIE_SECURE,
        samesite=settings.REFRESH_COOKIE_SAMESITE,
    )


def _clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(
        key=settings.REFRESH_COOKIE_NAME,
        path=settings.REFRESH_COOKIE_PATH,
        httponly=True,
        secure=settings.REFRESH_COOKIE_SECURE,
        samesite=settings.REFRESH_COOKIE_SAMESITE,
    )


def _signed_in(response: Response, db: Session, user: User) -> TokenResponse:
    _set_refresh_cookie(response, session_service.issue(db, user))
    return _token_response(user)


# Browsers only attach this header to a request from our own page -- a form on
# another site cannot set it -- so requiring it stops cross-site requests from
# spending the cookie.
REFRESH_HEADER = "X-Requested-With"


@router.post("/signup", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def signup(
    payload: SignupRequest,
    background: BackgroundTasks,
    response: Response,
    request: Request,
    db: Session = Depends(get_db),
) -> TokenResponse:
    """Create an account, sign the user straight in, and send the verification
    email in the background. Nothing is blocked on verifying; only emails about
    trips wait for it."""
    try:
        user = user_service.create_user(
            db,
            name=payload.name,
            email=payload.email,
            password=payload.password,
            date_of_birth=payload.date_of_birth,
            home_town=payload.home_town,
            phone=payload.phone,
            gender=payload.gender,
            travel_interests=payload.travel_interests,
        )
    except user_service.EmailAlreadyRegistered:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists",
        ) from None

    enqueue(background, jobs.send_verification_email, str(user.id))
    ip = events.client_ip(request)
    events.record(db, "signup", user_id=user.id, ip=ip)
    enqueue(background, jobs.score_activity, str(user.id), ip or "")
    return _signed_in(response, db, user)


@router.post("/signup-business", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def signup_business(
    payload: BusinessSignupRequest,
    background: BackgroundTasks,
    response: Response,
    request: Request,
    db: Session = Depends(get_db),
) -> TokenResponse:
    """Register an agency or business. The account can sign in straight away
    and set things up, but nothing it publishes is shown to travellers until
    an admin approves the business."""
    try:
        user = user_service.create_user(
            db, name=payload.name, email=payload.email, password=payload.password,
            home_town=payload.city, phone=payload.phone,
        )
    except user_service.EmailAlreadyRegistered:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists",
        ) from None
    user.role = "business"
    profile = BusinessProfile(
        user_id=user.id, slug=business_service.unique_slug(db, payload.business_name),
        business_name=payload.business_name, city=payload.city, phone=payload.business_phone,
    )
    business_service.apply_fields(profile, payload)
    db.add(profile)
    db.commit()
    db.refresh(user)

    enqueue(background, jobs.send_verification_email, str(user.id))
    ip = events.client_ip(request)
    events.record(db, "signup", user_id=user.id, ip=ip)
    enqueue(background, jobs.score_activity, str(user.id), ip or "")
    return _signed_in(response, db, user)


@router.post("/login", response_model=TokenResponse)
def login(
    payload: LoginRequest,
    response: Response,
    request: Request,
    background: BackgroundTasks,
    db: Session = Depends(get_db),
) -> TokenResponse:
    ip = events.client_ip(request)
    try:
        user = user_service.authenticate(
            db, email=payload.email, password=payload.password
        )
    except user_service.InvalidCredentials:
        known = user_service.get_by_email(db, payload.email)
        events.record(db, "login_failed", user_id=known.id if known else None, ip=ip)
        if known:
            enqueue(background, jobs.score_activity, str(known.id), ip or "")
        # Deliberately the same message for an unknown email and a wrong
        # password -- otherwise this endpoint tells an attacker which emails
        # are registered. Returned rather than raised: a raised HTTPException
        # drops the background tasks, and then the login_failures rule would
        # never run on the very event it watches for.
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"detail": "Incorrect email or password"},
            background=background,
        )
    except user_service.AccountBlocked:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account has been blocked",
        ) from None

    user = user_service.sync_admin_role(db, user)
    events.record(db, "login_ok", user_id=user.id, ip=ip)
    enqueue(background, jobs.score_activity, str(user.id), ip or "")
    return _signed_in(response, db, user)


@router.post(
    "/refresh",
    response_model=TokenResponse,
    responses={401: {"description": "No valid session"}, 403: {"description": "Blocked, or header missing"}},
)
def refresh(
    response: Response,
    db: Session = Depends(get_db),
    refresh_cookie: str | None = Cookie(default=None, alias=settings.REFRESH_COOKIE_NAME),
    requested_with: str | None = Header(default=None, alias=REFRESH_HEADER),
):
    """Swap the refresh cookie for a new access token (and a new cookie).

    Called when the page loads, and whenever an access token has expired.
    """
    if requested_with is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail=f"Missing {REFRESH_HEADER} header")
    try:
        user, new_raw = session_service.rotate(db, refresh_cookie)
    except session_service.RefreshRejected as exc:
        # Returned, not raised, so the cookie-clearing header reaches the browser.
        rejected = JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN if exc.blocked else status.HTTP_401_UNAUTHORIZED,
            content={"detail": "This account has been blocked" if exc.blocked else "Session expired"},
        )
        _clear_refresh_cookie(rejected)
        return rejected
    _set_refresh_cookie(response, new_raw)
    return _token_response(user)


class GoogleLoginRequest(BaseModel):
    credential: str


@router.get("/providers")
def providers() -> dict[str, str | None]:
    """What the login page needs to draw the Google button. A client id is
    public by design -- it is in every page that shows the button."""
    return {"google_client_id": settings.GOOGLE_CLIENT_ID or None}


@router.post("/google", response_model=TokenResponse)
def google_login(
    payload: GoogleLoginRequest,
    response: Response,
    request: Request,
    background: BackgroundTasks,
    db: Session = Depends(get_db),
) -> TokenResponse:
    """Sign in (or sign up) with Google.

    1. Same Google account as before -> that user.
    2. Else an account with the same (Google-verified) email -> link it. If
       that account was never verified, whoever created it may not own the
       address, so its password is replaced and its sessions ended -- stops
       someone pre-registering your email and waiting for you to link it.
    3. Else a new traveller account, already verified.
    """
    try:
        g = google_auth.verify(payload.credential)
    except google_auth.GoogleAuthError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from None

    ip = events.client_ip(request)
    user = db.query(User).filter(User.google_sub == g.sub).one_or_none()
    created = False
    if user is None:
        user = user_service.get_by_email(db, g.email)
        if user is not None:
            if not user.is_verified:
                user.password_hash = hash_password(secrets.token_urlsafe(32))
                session_service.revoke_all_for_user(db, user.id, reason="google-link")
            user.google_sub = g.sub
            user.is_verified = True
        else:
            # No password the person knows: they sign in with Google, or set
            # one later through "Forgot password".
            user = user_service.create_user(
                db, name=g.name, email=g.email, password=secrets.token_urlsafe(32),
            )
            user.google_sub = g.sub
            user.is_verified = True
            created = True
        db.commit()
        db.refresh(user)

    if user.is_blocked:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="This account has been blocked")

    user = user_service.sync_admin_role(db, user)
    events.record(db, "signup" if created else "login_ok", user_id=user.id, ip=ip)
    enqueue(background, jobs.score_activity, str(user.id), ip or "")
    return _signed_in(response, db, user)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    response: Response,
    db: Session = Depends(get_db),
    refresh_cookie: str | None = Cookie(default=None, alias=settings.REFRESH_COOKIE_NAME),
) -> Response:
    """Ends this session everywhere it was refreshed to. Always succeeds."""
    session_service.revoke(db, refresh_cookie)
    _clear_refresh_cookie(response)
    response.status_code = status.HTTP_204_NO_CONTENT
    return response


@router.get("/me", response_model=UserRead)
def me(user: User = Depends(get_current_user)) -> User:
    """Used by the frontend to restore a session and to know the user's role."""
    return user


@router.post("/me/avatar", response_model=UserRead)
async def upload_avatar(
    file: UploadFile = File(...), user: User = Depends(get_current_user), db: Session = Depends(get_db),
) -> User:
    """Set or replace your profile picture. The photo is cropped, resized and
    re-encoded on the server -- see app/services/avatar.py."""
    from app.services import avatar

    data = await file.read(avatar.MAX_MB * 1024 * 1024 + 1)
    try:
        url = avatar.save(data)
    except avatar.AvatarError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from None
    old, user.avatar_url = user.avatar_url, url
    db.commit()
    db.refresh(user)
    avatar.remove(old)
    return user


@router.delete("/me/avatar", response_model=UserRead)
def delete_avatar(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> User:
    from app.services import avatar

    old, user.avatar_url = user.avatar_url, None
    db.commit()
    db.refresh(user)
    avatar.remove(old)
    return user


@router.put("/me", response_model=UserRead)
def update_me(
    payload: ProfileUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> User:
    """Edit your own profile. Email, role and password are not editable here."""
    changes = payload.model_dump(exclude_unset=True)
    if "name" in changes:
        if not changes["name"] or not changes["name"].strip():
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Name cannot be empty")
        changes["name"] = changes["name"].strip()
    if "travel_interests" in changes:
        changes["travel_interests"] = changes["travel_interests"] or None
    for field, value in changes.items():
        setattr(user, field, value)
    db.commit()
    db.refresh(user)
    return user


@router.post("/change-password")
def change_password(
    payload: ChangePasswordRequest,
    response: Response,
    background: BackgroundTasks,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    """Needs the current password. Every other session is signed out; this
    browser gets a fresh session so the user stays logged in here."""
    if not verify_password(payload.current_password, user.password_hash):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Your current password is incorrect")
    if payload.current_password == payload.new_password:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "The new password must be different")
    user.password_hash = hash_password(payload.new_password)
    db.commit()
    session_service.revoke_all_for_user(db, user.id, reason="pw_change")
    _set_refresh_cookie(response, session_service.issue(db, user))
    enqueue(background, jobs.send_password_changed_email, str(user.id))
    return {"detail": "Password changed. Other devices have been signed out."}


_BAD_LINK = HTTPException(
    status_code=status.HTTP_400_BAD_REQUEST,
    detail="This verification link is invalid or has expired",
)


@router.post("/verify", response_model=UserRead)
def verify_email(payload: VerifyEmailRequest, db: Session = Depends(get_db)) -> User:
    """No login needed -- the link is often opened on a different device from
    the one that signed up. The signed token is the proof."""
    try:
        claims = decode_email_verification_token(payload.token)
        user_id = uuid.UUID(claims["sub"])
        email = claims["email"]
    except (InvalidTokenError, KeyError, ValueError):
        raise _BAD_LINK from None

    user = user_service.get_by_id(db, user_id)
    # The address in the token must still be the account's address, so a link
    # sent to an old address cannot verify a new one.
    if user is None or user.email != email:
        raise _BAD_LINK

    if not user.is_verified:
        user.is_verified = True
        db.commit()
        db.refresh(user)
    return user_service.sync_admin_role(db, user)


@router.post("/resend-verification", status_code=status.HTTP_202_ACCEPTED)
def resend_verification(
    background: BackgroundTasks, user: User = Depends(get_current_user)
) -> dict[str, str]:
    if user.is_verified:
        return {"detail": "Your email is already verified"}
    enqueue(background, jobs.send_verification_email, str(user.id))
    return {"detail": "Verification email sent"}


# --- forgotten password ----------------------------------------------------------

FORGOT_REPLY = {
    "detail": "If an account exists for that email, a reset link is on its way. "
    "Check your inbox (and spam folder)."
}

_BAD_RESET_LINK = HTTPException(
    status_code=status.HTTP_400_BAD_REQUEST,
    detail="This reset link is invalid, expired or already used. Request a new one.",
)


@router.post("/forgot-password", status_code=status.HTTP_202_ACCEPTED)
def forgot_password(payload: ForgotPasswordRequest, background: BackgroundTasks) -> dict[str, str]:
    """Always the same answer, and no database work on this request: whether
    the address is registered is decided in the background job, so neither the
    reply nor its timing tells anyone which emails have accounts."""
    enqueue(background, jobs.send_password_reset_email, payload.email.lower())
    return FORGOT_REPLY


@router.post("/reset-password")
def reset_password(
    payload: ResetPasswordRequest,
    background: BackgroundTasks,
    db: Session = Depends(get_db),
) -> dict[str, str]:
    try:
        claims = decode_password_reset_token(payload.token)
        user_id = uuid.UUID(claims["sub"])
        fingerprint = claims["pwf"]
    except (InvalidTokenError, KeyError, ValueError):
        raise _BAD_RESET_LINK from None

    user = user_service.get_by_id(db, user_id)
    # The fingerprint of the current hash must match the one in the link: a
    # used link (password already changed) or an old one fails here.
    if user is None or user.is_blocked or password_fingerprint(user.password_hash) != fingerprint:
        raise _BAD_RESET_LINK

    user.password_hash = hash_password(payload.password)
    # Whoever could open the email has proved they own the address.
    user.is_verified = True
    db.commit()

    # Sign out every device -- if the old password leaked, its sessions go too.
    session_service.revoke_all_for_user(db, user.id, reason="pw_reset")
    enqueue(background, jobs.send_password_changed_email, str(user.id))
    return {"detail": "Your password has been changed. Log in with the new password."}
