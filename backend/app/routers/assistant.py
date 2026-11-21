"""The travel assistant: ask anything about where to go, what it costs and
what the weather will be like."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.assistant import service
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.assistant import AssistantReply, AssistantRequest

router = APIRouter(prefix="/assistant", tags=["assistant"])


@router.post("/chat", response_model=AssistantReply)
def chat(payload: AssistantRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> AssistantReply:
    return service.chat(db, user, payload.message.strip(), payload.history)
