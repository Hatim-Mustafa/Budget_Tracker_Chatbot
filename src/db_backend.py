from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Engine, ForeignKey, String, create_engine
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    Session,
    mapped_column,
    relationship,
    sessionmaker,
)

from .models import ChatMessage, MessageRole


class Base(DeclarativeBase):
    """Base class for SQLAlchemy mappings in the course examples."""


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    conversation_id: Mapped[UUID] = mapped_column(ForeignKey("conversations.id"))
    role: Mapped[str] = mapped_column(String(20))
    content: Mapped[str] = mapped_column(String(4_000))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), default=datetime.now)

    conversations: Mapped[Conversation] = relationship(back_populates="messages")


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    title: Mapped[str] = mapped_column(String(200), default="New conversation")
    user_id: Mapped[int] = mapped_column(nullable=False)

    messages: Mapped[list[Message]] = relationship(
        back_populates="conversations",
        cascade="all, delete-orphan",
        order_by="Message.created_at",
    )


def build_engine(database_url: str) -> Engine:
    """Create a synchronous SQLAlchemy engine for the lesson code."""

    return create_engine(database_url, echo=False, future=True)


def build_session_factory(engine: Engine) -> sessionmaker[Session]:
    """Create a session factory bound to the given engine."""

    return sessionmaker(bind=engine, autoflush=True, expire_on_commit=False)


class ConversationHandler:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create_conversation(
        self, title: str = "New conversation", user_id: int | None = None
    ) -> Conversation:
        conversation = Conversation(title=title, user_id=user_id)
        self.session.add(conversation)
        self.session.flush()
        return conversation

    def append_message(self, convo_id: UUID, message: ChatMessage) -> Message:
        record = Message(conversation_id=convo_id, role=message.role.value, content=message.content)
        self.session.add(record)
        self.session.flush()
        return record

    def list_conversations(self, user_id: int) -> list[Conversation]:
        return (
            self.session.query(Conversation)
            .filter(Conversation.user_id == user_id)
            .order_by(Conversation.id)
            .all()
        )

    def rename_conversation(self, convo_id: UUID, title: str) -> Conversation | None:
        conversation = self.session.get(Conversation, convo_id)
        if conversation is None:
            return None
        conversation.title = title
        self.session.flush()
        return conversation

    def delete_conversation(self, convo_id: UUID) -> bool:
        conversation = self.session.get(Conversation, convo_id)
        if conversation is None:
            return False
        self.session.delete(conversation)
        self.session.flush()
        return True

    def load_messages(self, convo_id: UUID) -> list[ChatMessage]:
        messages = (
            self.session.query(Message)
            .filter_by(conversation_id=convo_id)
            .order_by(Message.created_at)
            .all()
        )
        chat_messages = [
            ChatMessage(
                id=msg.id,
                role=MessageRole(msg.role),
                content=msg.content,
                conversation_id=msg.conversation_id,
                created_at=msg.created_at,
            )
            for msg in messages
        ]
        return chat_messages
