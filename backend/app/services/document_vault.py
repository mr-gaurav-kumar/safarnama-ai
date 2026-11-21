"""The document vault: encrypt, check and store a traveller's ID documents.

Security choices, in one place:
  - Numbers and scans are encrypted with Fernet (AES-128-CBC + HMAC-SHA256)
    using DOCUMENT_ENCRYPTION_KEY from .env. Several keys, comma-separated,
    allow rotation: the first encrypts, all of them decrypt.
  - No key -> the vault is switched off. There is no built-in fallback key.
  - Scans are written under PRIVATE_DOCS_DIR with random names. That folder
    is never mounted as static files; the only way out is the owner's
    authenticated download route.
  - Files are checked by their first bytes (PDF / JPG / PNG / WebP), capped
    in size, and never keep the uploaded file name.
  - Every query is scoped by user_id: there is no admin route to these.
"""
from __future__ import annotations

import re
import uuid
from datetime import date

from cryptography.fernet import Fernet, InvalidToken, MultiFernet
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.document import KINDS, UserDocument

MAX_MB = 5

LABELS = {
    "aadhaar": "Aadhaar", "pan": "PAN card", "driving_licence": "Driving licence",
    "passport": "Passport", "voter_id": "Voter ID", "other": "Other document",
}
# One of each, except "other".
SINGLE = {"aadhaar", "pan", "driving_licence", "passport", "voter_id"}
EXPIRING = {"driving_licence", "passport", "other"}


class VaultError(Exception):
    """Something we refuse, with a sentence for the traveller."""


class VaultDisabled(VaultError):
    pass


class DocumentNotFound(VaultError):
    pass


# ---------------------------------------------------------------- crypto

def enabled() -> bool:
    return bool(settings.DOCUMENT_ENCRYPTION_KEY.strip())


def _fernet() -> MultiFernet:
    if not enabled():
        raise VaultDisabled("Document storage is not set up on this server yet.")
    keys = [k.strip() for k in settings.DOCUMENT_ENCRYPTION_KEY.split(",") if k.strip()]
    return MultiFernet([Fernet(k.encode()) for k in keys])


def encrypt(data: bytes) -> bytes:
    return _fernet().encrypt(data)


def decrypt(token: bytes) -> bytes:
    try:
        return _fernet().decrypt(token)
    except InvalidToken:
        raise VaultError("This document can't be opened — the server's encryption key has changed.") from None


# ---------------------------------------------------------------- numbers

# Verhoeff tables: Aadhaar's last digit is a Verhoeff check digit, so a typo
# in any one digit (or two swapped digits) is caught here.
_D = [[0, 1, 2, 3, 4, 5, 6, 7, 8, 9], [1, 2, 3, 4, 0, 6, 7, 8, 9, 5], [2, 3, 4, 0, 1, 7, 8, 9, 5, 6],
      [3, 4, 0, 1, 2, 8, 9, 5, 6, 7], [4, 0, 1, 2, 3, 9, 5, 6, 7, 8], [5, 9, 8, 7, 6, 0, 4, 3, 2, 1],
      [6, 5, 9, 8, 7, 1, 0, 4, 3, 2], [7, 6, 5, 9, 8, 2, 1, 0, 4, 3], [8, 7, 6, 5, 9, 3, 2, 1, 0, 4],
      [9, 8, 7, 6, 5, 4, 3, 2, 1, 0]]
_P = [[0, 1, 2, 3, 4, 5, 6, 7, 8, 9], [1, 5, 7, 6, 2, 8, 3, 0, 9, 4], [5, 8, 0, 3, 7, 9, 6, 1, 4, 2],
      [8, 9, 1, 6, 0, 4, 3, 5, 2, 7], [9, 4, 5, 3, 1, 2, 6, 8, 7, 0], [4, 2, 8, 6, 5, 7, 3, 9, 0, 1],
      [2, 7, 9, 3, 8, 0, 6, 4, 1, 5], [7, 0, 4, 6, 9, 1, 3, 2, 5, 8]]


def verhoeff_ok(digits: str) -> bool:
    c = 0
    for i, ch in enumerate(reversed(digits)):
        c = _D[c][_P[i % 8][int(ch)]]
    return c == 0


_RULES: dict[str, tuple[re.Pattern[str], str]] = {
    "aadhaar": (re.compile(r"[2-9]\d{11}"), "An Aadhaar number has 12 digits and doesn't start with 0 or 1."),
    "pan": (re.compile(r"[A-Z]{5}\d{4}[A-Z]"), "A PAN looks like ABCDE1234F."),
    "driving_licence": (re.compile(r"[A-Z]{2}\d{2}[A-Z0-9]{9,13}"), "A driving licence number looks like DL0420191234567."),
    "passport": (re.compile(r"[A-Z]\d{7}"), "An Indian passport number is one letter and 7 digits, like K1234567."),
    "voter_id": (re.compile(r"[A-Z]{3}\d{7}"), "A Voter ID (EPIC) number looks like ABC1234567."),
}


def clean_number(kind: str, raw: str | None) -> str | None:
    if raw is None or not raw.strip():
        return None
    n = re.sub(r"[\s\-/]", "", raw).upper()
    if len(n) > 30:
        raise VaultError("That number is too long.")
    rule = _RULES.get(kind)
    if rule is not None:
        pattern, msg = rule
        if not pattern.fullmatch(n):
            raise VaultError(msg)
        if kind == "aadhaar" and not verhoeff_ok(n):
            raise VaultError("That Aadhaar number doesn't add up — please check the digits.")
    elif not re.fullmatch(r"[A-Z0-9]{3,30}", n):
        raise VaultError("Use letters and numbers only.")
    return n


def masked(kind: str, last4: str | None) -> str | None:
    if not last4:
        return None
    return {"aadhaar": f"XXXX XXXX {last4}", "pan": f"XXXXXX{last4}"}.get(kind, f"•••• {last4}")


# ---------------------------------------------------------------- files

def _kind_of(head: bytes) -> str | None:
    if head.startswith(b"%PDF-"):
        return "application/pdf"
    if head.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if head.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        return "image/webp"
    return None


def _write(data: bytes) -> tuple[str, str, int]:
    if len(data) > MAX_MB * 1024 * 1024:
        raise VaultError(f"Files must be under {MAX_MB} MB.")
    ftype = _kind_of(data[:16])
    if ftype is None:
        raise VaultError("Upload a photo (JPG, PNG, WebP) or a PDF.")
    folder = settings.PRIVATE_DOCS_DIR
    folder.mkdir(parents=True, exist_ok=True)
    name = f"{uuid.uuid4().hex}.bin"
    (folder / name).write_bytes(encrypt(data))
    return name, ftype, len(data)


def _remove(name: str | None) -> None:
    if name:
        (settings.PRIVATE_DOCS_DIR / name).unlink(missing_ok=True)


def read_file(doc: UserDocument) -> bytes:
    if not doc.file_name:
        raise DocumentNotFound("No file saved for this document")
    path = settings.PRIVATE_DOCS_DIR / doc.file_name
    if not path.is_file():
        raise DocumentNotFound("The file is missing")
    return decrypt(path.read_bytes())


# ---------------------------------------------------------------- records

def list_for(db: Session, user_id: uuid.UUID) -> list[UserDocument]:
    return list(db.scalars(select(UserDocument).where(UserDocument.user_id == user_id).order_by(UserDocument.created_at)))


def get_own(db: Session, user_id: uuid.UUID, doc_id: uuid.UUID) -> UserDocument:
    doc = db.get(UserDocument, doc_id)
    if doc is None or doc.user_id != user_id:  # same answer for "missing" and "not yours"
        raise DocumentNotFound("Document not found")
    return doc


def save(
    db: Session, user_id: uuid.UUID, *, kind: str, number: str | None, expires_on: date | None,
    label: str | None, file: bytes | None, doc: UserDocument | None = None,
) -> UserDocument:
    """Create, or update `doc`. Only the parts given change; a new file
    replaces the old one, which is deleted."""
    _fernet()  # refuse early when the vault is off
    if kind not in KINDS:
        raise VaultError("Unknown document type")
    clean = clean_number(kind, number)
    if doc is None:
        if kind in SINGLE and db.scalar(select(UserDocument.id).where(
                UserDocument.user_id == user_id, UserDocument.kind == kind)):
            raise VaultError(f"You already saved a {LABELS[kind]}. Edit that one instead.")
        if clean is None and not file:
            raise VaultError("Add the number, a photo or PDF, or both.")
        doc = UserDocument(user_id=user_id, kind=kind)
        db.add(doc)
    if clean is not None:
        doc.number_enc = encrypt(clean.encode()).decode()
        doc.number_last4 = clean[-4:]
    if expires_on is not None:
        doc.expires_on = expires_on
    if label is not None and kind == "other":
        doc.label = " ".join(label.split())[:60] or None
    old_file = None
    if file:
        old_file = doc.file_name
        doc.file_name, doc.file_type, doc.file_size = _write(file)
    db.commit()
    db.refresh(doc)
    _remove(old_file)
    return doc


def reveal_number(doc: UserDocument) -> str | None:
    return decrypt(doc.number_enc.encode()).decode() if doc.number_enc else None


def delete(db: Session, doc: UserDocument) -> None:
    name = doc.file_name
    db.delete(doc)
    db.commit()
    _remove(name)


def delete_all_for_user(db: Session, user_id: uuid.UUID) -> None:
    """Files first-class: the database cascade removes rows, not files."""
    for doc in list_for(db, user_id):
        _remove(doc.file_name)


def days_left(expires_on: date | None, today: date | None = None) -> int | None:
    return None if expires_on is None else (expires_on - (today or date.today())).days
