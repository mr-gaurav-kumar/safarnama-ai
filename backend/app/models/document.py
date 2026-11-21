"""A traveller's ID documents (Aadhaar, PAN, driving licence, passport...).

Nothing sensitive is stored in the clear: the document number is encrypted
(only its last four characters are kept readable, for the masked display),
and an uploaded scan lives encrypted in a private folder that the web
server never serves directly. See app/services/document_vault.py.
"""
import datetime as dt
import uuid

from sqlalchemy import Date, ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin

KINDS = ("aadhaar", "pan", "driving_licence", "passport", "voter_id", "other")


class UserDocument(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "user_documents"

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    kind: Mapped[str] = mapped_column(String(20), nullable=False)
    label: Mapped[str | None] = mapped_column(String(60), nullable=True)  # for "other"
    number_enc: Mapped[str | None] = mapped_column(Text, nullable=True)
    number_last4: Mapped[str | None] = mapped_column(String(4), nullable=True)
    expires_on: Mapped[dt.date | None] = mapped_column(Date, nullable=True)
    # Encrypted scan: random file name in settings.PRIVATE_DOCS_DIR.
    file_name: Mapped[str | None] = mapped_column(String(80), nullable=True)
    file_type: Mapped[str | None] = mapped_column(String(40), nullable=True)
    file_size: Mapped[int | None] = mapped_column(Integer, nullable=True)
