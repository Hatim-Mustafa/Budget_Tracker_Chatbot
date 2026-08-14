from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ..budget_db_backend import User as UserTable
from ..db import get_session
from ..db_backend import ConversationHandler
from ..models import (
    ChatMessage,
    ConversationInfo,
    ConversationRenameRequest,
)

router = APIRouter(tags=["chat"])


@router.get("/conversations", response_model=list[ConversationInfo])
async def list_conversations(
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[UserTable, Depends(get_current_user)],
) -> list[ConversationInfo]:
    convo_handler = ConversationHandler(session)
    conversations = convo_handler.list_conversations(current_user.user_id)
    return [ConversationInfo(id=c.id, title=c.title) for c in conversations]


@router.get("/conversations/{convo_id}/messages", response_model=list[ChatMessage])
async def get_conversation_messages(
    convo_id: UUID,
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[UserTable, Depends(get_current_user)],
) -> list[ChatMessage]:
    convo_handler = ConversationHandler(session)
    return convo_handler.load_messages(convo_id)


@router.patch("/conversations/{convo_id}", response_model=ConversationInfo)
async def rename_conversation(
    convo_id: UUID,
    body: ConversationRenameRequest,
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[UserTable, Depends(get_current_user)],
) -> ConversationInfo:
    convo_handler = ConversationHandler(session)
    conversation = convo_handler.rename_conversation(convo_id, body.title)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return ConversationInfo(id=conversation.id, title=conversation.title)


@router.delete("/conversations/{convo_id}", status_code=204)
async def delete_conversation(
    convo_id: UUID,
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[UserTable, Depends(get_current_user)],
) -> None:
    convo_handler = ConversationHandler(session)
    deleted = convo_handler.delete_conversation(convo_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Conversation not found")


@router.get("/new_conversation", response_model=UUID)
async def new_conversation(
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[UserTable, Depends(get_current_user)],
) -> UUID:
    convo_handler = ConversationHandler(session)
    conversation = convo_handler.create_conversation(user_id=current_user.user_id)
    return conversation.id
