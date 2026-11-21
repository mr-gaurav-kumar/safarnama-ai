"""Profile pictures.

Every upload is opened with Pillow and re-drawn as a fresh 320x320 WebP:
  - centre-cropped to a square and turned the right way up (phone photos
    store their rotation in EXIF),
  - EXIF and every other bit of metadata dropped -- including the GPS
    position phones write into photos,
  - re-encoded from pixels, so nothing hidden in the original file survives.
A profile picture is meant to be seen, so it is saved under the public
/media folder -- with a random name, never the uploaded one.
"""
from __future__ import annotations

import io
import uuid

from PIL import Image, ImageOps, UnidentifiedImageError

from app.core.config import settings

MAX_MB = 5
SIZE = 320
FORMATS = {"JPEG", "PNG", "WEBP"}
# Refuse "decompression bombs": tiny files that unpack to huge images.
Image.MAX_IMAGE_PIXELS = 40_000_000


class AvatarError(Exception):
    pass


def process(data: bytes) -> bytes:
    if len(data) > MAX_MB * 1024 * 1024:
        raise AvatarError(f"Photos must be under {MAX_MB} MB.")
    try:
        img = Image.open(io.BytesIO(data))
        if img.format not in FORMATS:
            raise AvatarError("Use a JPG, PNG or WebP photo.")
        img.load()
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError):
        raise AvatarError("That file isn't a photo we can read. Use a JPG, PNG or WebP.") from None
    img = ImageOps.exif_transpose(img)
    img = ImageOps.fit(img.convert("RGB"), (SIZE, SIZE), method=Image.Resampling.LANCZOS)
    out = io.BytesIO()
    img.save(out, "WEBP", quality=85, method=6)  # no exif= argument: nothing carried over
    return out.getvalue()


def save(data: bytes) -> str:
    """Process and store; returns the public URL path."""
    clean = process(data)
    folder = settings.MEDIA_DIR / "avatars"
    folder.mkdir(parents=True, exist_ok=True)
    name = f"{uuid.uuid4().hex}.webp"
    (folder / name).write_bytes(clean)
    return f"/media/avatars/{name}"


def remove(url: str | None) -> None:
    """Delete a stored avatar. Only ever inside media/avatars -- the URL comes
    from our own database, but it is checked anyway."""
    if not url or not url.startswith("/media/avatars/"):
        return
    name = url.rsplit("/", 1)[-1]
    if "/" in name or "\\" in name or not name.endswith(".webp"):
        return
    (settings.MEDIA_DIR / "avatars" / name).unlink(missing_ok=True)
