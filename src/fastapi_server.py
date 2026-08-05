from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from src.auth import create_auth_router, get_current_user

from .models import ChatMessage, ConversationInfo, ConversationRenameRequest, MessageRole

from .agent import AgentState, chat_messages_to_model_messages, create_agent, summarize_chat
from .db_backend import ConversationHandler
from .budget_db_backend import User as UserTable
from sqlalchemy.orm import Session
from .db import get_session

def create_chat_router() -> APIRouter:
    resolved_agent_factory = create_agent
    
    chat_router = APIRouter(tags=["chat"])


    @chat_router.get("/conversations", response_model=list[ConversationInfo])
    async def list_conversations(
        session: Session = Depends(get_session),
        current_user: UserTable = Depends(get_current_user),
    ) -> list[ConversationInfo]:
        convo_handler = ConversationHandler(session)
        conversations = convo_handler.list_conversations(current_user.user_id)
        return [ConversationInfo(id=c.id, title=c.title) for c in conversations]

    @chat_router.get("/conversations/{convo_id}/messages", response_model=list[ChatMessage])
    async def get_conversation_messages(
        convo_id: UUID,
        session: Session = Depends(get_session),
        current_user: UserTable = Depends(get_current_user),
    ) -> list[ChatMessage]:
        convo_handler = ConversationHandler(session)
        return convo_handler.load_messages(convo_id)

    @chat_router.patch("/conversations/{convo_id}", response_model=ConversationInfo)
    async def rename_conversation(
        convo_id: UUID,
        body: ConversationRenameRequest,
        session: Session = Depends(get_session),
        current_user: UserTable = Depends(get_current_user),
    ) -> ConversationInfo:
        convo_handler = ConversationHandler(session)
        conversation = convo_handler.rename_conversation(convo_id, body.title)
        if conversation is None:
            raise HTTPException(status_code=404, detail="Conversation not found")
        return ConversationInfo(id=conversation.id, title=conversation.title)

    @chat_router.delete("/conversations/{convo_id}", status_code=204)
    async def delete_conversation(
        convo_id: UUID,
        session: Session = Depends(get_session),
        current_user: UserTable = Depends(get_current_user),
    ) -> None:
        convo_handler = ConversationHandler(session)
        deleted = convo_handler.delete_conversation(convo_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Conversation not found")
    
    @chat_router.get("/new_conversation", response_model=UUID)
    async def new_conversation(
        session: Session = Depends(get_session),
        current_user: UserTable = Depends(get_current_user),
    ) -> UUID:
        convo_handler = ConversationHandler(session)
        conversation = convo_handler.create_conversation(user_id=current_user.user_id)
        return conversation.id

    @chat_router.post("/chat", response_model=ChatMessage)
    async def chat(
        request: ChatMessage,
        session: Session = Depends(get_session),
        current_user: UserTable = Depends(get_current_user),
    ) -> ChatMessage:
        convo_handler = ConversationHandler(session)
        if request.conversation_id is None:
            conversation = convo_handler.create_conversation(user_id=current_user.user_id)
            request.conversation_id = conversation.id

        history = chat_messages_to_model_messages(convo_handler.load_messages(request.conversation_id))

        if len(history) > 10:
            history = await summarize_chat(history)

        convo_handler.append_message(request.conversation_id, request)
        result: Any = await resolved_agent_factory(current_user.user_id).run(
            request.content,
            message_history=history,
            deps=AgentState(db=session, current_user_id=current_user.user_id),
        )
        reply = ChatMessage(
            conversation_id=request.conversation_id,
            role=MessageRole.ASSISTANT,
            content=result.output
        )
        convo_handler.append_message(request.conversation_id, reply)
        return reply

    return chat_router


def create_app() -> FastAPI:
    app = FastAPI()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(create_chat_router())
    app.include_router(create_auth_router())

    return app

app = create_app()