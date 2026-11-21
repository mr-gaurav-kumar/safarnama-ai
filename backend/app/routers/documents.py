"""My documents: a traveller's own ID documents, encrypted.

Only the owner can reach these -- every route is scoped to the signed-in
user and there is no admin route. Files are streamed back decrypted with
no-store caching, never served as static files.
"""
import uuid
from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.document import UserDocument
from app.models.user import User
from app.services import document_vault as vault

router = APIRouter(prefix="/me/documents", tags=["documents"])

Kind = Literal["aadhaar", "pan", "driving_licence", "passport", "voter_id", "other"]


class DocumentOut(BaseModel):
    id: str
    kind: str
    title: str
    number_masked: str | None
    expires_on: date | None
    days_left: int | None
    has_file: bool
    file_type: str | None
    file_size: int | None
    updated_at: str


class Vault(BaseModel):
    enabled: bool
    items: list[DocumentOut]


def _out(d: UserDocument) -> DocumentOut:
    return DocumentOut(
        id=str(d.id), kind=d.kind, title=(d.label if d.kind == "other" and d.label else vault.LABELS[d.kind]),
        number_masked=vault.masked(d.kind, d.number_last4), expires_on=d.expires_on,
        days_left=vault.days_left(d.expires_on), has_file=bool(d.file_name), file_type=d.file_type,
        file_size=d.file_size, updated_at=d.updated_at.isoformat(),
    )


def _fail(exc: vault.VaultError) -> HTTPException:
    if isinstance(exc, vault.DocumentNotFound):
        return HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc))
    if isinstance(exc, vault.VaultDisabled):
        return HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc))
    return HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))


async def _read(upload: UploadFile | None) -> bytes | None:
    if upload is None or not upload.filename:
        return None
    data = await upload.read(vault.MAX_MB * 1024 * 1024 + 1)
    return data or None


def _no_store(resp: Response) -> None:
    resp.headers["Cache-Control"] = "no-store"
    resp.headers["Pragma"] = "no-cache"


@router.get("", response_model=Vault)
def list_documents(response: Response, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> Vault:
    _no_store(response)
    return Vault(enabled=vault.enabled(), items=[_out(d) for d in vault.list_for(db, user.id)])


@router.post("", response_model=DocumentOut, status_code=status.HTTP_201_CREATED)
async def add_document(
    kind: Kind = Form(...),
    number: str | None = Form(default=None),
    expires_on: date | None = Form(default=None),
    label: str | None = Form(default=None),
    file: UploadFile | None = File(default=None),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DocumentOut:
    try:
        d = vault.save(db, user.id, kind=kind, number=number, expires_on=expires_on, label=label, file=await _read(file))
    except vault.VaultError as exc:
        raise _fail(exc) from None
    return _out(d)


@router.put("/{doc_id}", response_model=DocumentOut)
async def update_document(
    doc_id: uuid.UUID,
    number: str | None = Form(default=None),
    expires_on: date | None = Form(default=None),
    label: str | None = Form(default=None),
    file: UploadFile | None = File(default=None),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DocumentOut:
    try:
        d = vault.get_own(db, user.id, doc_id)
        d = vault.save(db, user.id, kind=d.kind, number=number, expires_on=expires_on, label=label,
                       file=await _read(file), doc=d)
    except vault.VaultError as exc:
        raise _fail(exc) from None
    return _out(d)


@router.get("/{doc_id}/number")
def reveal_number(doc_id: uuid.UUID, response: Response, user: User = Depends(get_current_user),
                  db: Session = Depends(get_db)) -> dict[str, str | None]:
    _no_store(response)
    try:
        return {"number": vault.reveal_number(vault.get_own(db, user.id, doc_id))}
    except vault.VaultError as exc:
        raise _fail(exc) from None


@router.get("/{doc_id}/file")
def download_file(doc_id: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> Response:
    try:
        d = vault.get_own(db, user.id, doc_id)
        data = vault.read_file(d)
    except vault.VaultError as exc:
        raise _fail(exc) from None
    ext = {"application/pdf": "pdf", "image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}.get(d.file_type or "", "bin")
    return Response(
        content=data, media_type=d.file_type or "application/octet-stream",
        headers={
            "Content-Disposition": f'inline; filename="{d.kind}.{ext}"',
            "Cache-Control": "no-store", "Pragma": "no-cache", "X-Content-Type-Options": "nosniff",
            # A PDF opened from here can't run scripts or reach anything.
            "Content-Security-Policy": "default-src 'none'; img-src 'self' data:; style-src 'unsafe-inline'; sandbox",
        },
    )


@router.delete("/{doc_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(doc_id: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> Response:
    try:
        vault.delete(db, vault.get_own(db, user.id, doc_id))
    except vault.VaultError as exc:
        raise _fail(exc) from None
    return Response(status_code=status.HTTP_204_NO_CONTENT)
