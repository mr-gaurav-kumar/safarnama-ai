"""Image uploads for package photos.

Only the admin and approved businesses may upload. Files are checked by their
first bytes (not the name or the browser's claimed type), capped in size,
and stored under a random name -- the original filename is never used.
"""
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.business import BusinessProfile
from app.models.user import User

router = APIRouter(prefix="/uploads", tags=["uploads"])

_SIGNATURES = (
    (b"\xff\xd8\xff", "jpg"),
    (b"\x89PNG\r\n\x1a\n", "png"),
)


def _kind(head: bytes) -> str | None:
    for sig, ext in _SIGNATURES:
        if head.startswith(sig):
            return ext
    if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        return "webp"
    return None


def _may_publish(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> User:
    if user.role == "admin":
        return user
    if user.role == "business":
        p = db.get(BusinessProfile, user.id)
        if p is not None and p.status == "approved":
            return user
    raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Only the admin and approved businesses can upload photos")


@router.post("/package-image", status_code=status.HTTP_201_CREATED)
async def upload_package_image(file: UploadFile = File(...), _: User = Depends(_may_publish)) -> dict[str, str]:
    limit = settings.MAX_IMAGE_MB * 1024 * 1024
    data = await file.read(limit + 1)
    if len(data) > limit:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail=f"Photos must be under {settings.MAX_IMAGE_MB} MB")
    ext = _kind(data[:16])
    if ext is None:
        raise HTTPException(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail="Upload a JPG, PNG or WebP image")
    folder = settings.MEDIA_DIR / "packages"
    folder.mkdir(parents=True, exist_ok=True)
    name = f"{uuid.uuid4().hex}.{ext}"
    (folder / name).write_bytes(data)
    return {"url": f"/media/packages/{name}"}
