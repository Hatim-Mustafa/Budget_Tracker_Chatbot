from typing import Annotated, Any

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..agent import AgentState, chat_messages_to_model_messages, create_agent, summarize_chat
from ..auth import get_current_user
from ..budget_db_backend import User as UserTable
from ..db import get_session
from ..db_backend import ConversationHandler
from ..models import (
    ChatMessage,
    ChatVisualizationResponse,
    MessageRole,
)

resolved_agent_factory = create_agent

router = APIRouter(tags=["chat"])


@router.post("/chat", response_model=ChatVisualizationResponse)
async def chat(
    request: ChatMessage,
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[UserTable, Depends(get_current_user)],
) -> ChatVisualizationResponse:
    convo_handler = ConversationHandler(session)
    if request.conversation_id is None:
        conversation = convo_handler.create_conversation(user_id=current_user.user_id)
        request.conversation_id = conversation.id

    history = chat_messages_to_model_messages(convo_handler.load_messages(request.conversation_id))

    if len(history) > 10:
        history = await summarize_chat(history)

    convo_handler.append_message(request.conversation_id, request)
    deps = AgentState(db=session, current_user_id=current_user.user_id)
    result: Any = await resolved_agent_factory(current_user.user_id).run(
        request.content,
        message_history=history,
        deps=deps,
    )

    # The sub-agents may have called the LLM-powered `visualize_data` tool
    # while answering; its specs were stored on the shared AgentState (the
    # delegation clones share the same list), and are attached to the reply.
    # The planner itself never touches the DB or SQL.
    visualizations = deps.visualizations

    reply = ChatMessage(
        conversation_id=request.conversation_id,
        role=MessageRole.ASSISTANT,
        content=result.output,
    )
    convo_handler.append_message(request.conversation_id, reply)
    return ChatVisualizationResponse(
        message=result.output,
        conversation_id=request.conversation_id,
        visualizations=visualizations,
    )
