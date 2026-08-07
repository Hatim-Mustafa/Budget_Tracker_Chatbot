"""Shared models used by the course reference code."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    user_message: str = Field(
        description="The user's message to the chatbot.",
        min_length=1,
        examples=["Explain dependency injection in FastAPI."],
    )


class ChatResponse(BaseModel):
    reply: str = Field(description="The chatbot's reply to the user's message.", min_length=1)
    model_name: str = Field(
        description="The name of the model used to generate the reply.", min_length=1
    )


class MessageRole(str, Enum):
    """Supported chat roles for the course chat application."""

    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


class ChatMessage(BaseModel):
    """A single chat message in a conversation transcript."""

    id: UUID | None = Field(
        default=None, description="The message's own identifier, set once persisted."
    )
    role: MessageRole
    content: str = Field(min_length=1)
    conversation_id: UUID = Field(
        default_factory=uuid4,
        description="The unique identifier for the conversation this message belongs to.",
    )
    created_at: datetime | None = Field(default=None, description="When the message was persisted.")


class ConversationInfo(BaseModel):
    """Summary of a conversation for listing in the sidebar."""

    id: UUID
    title: str = Field(min_length=1)


class ConversationRenameRequest(BaseModel):
    """Body for renaming an existing conversation."""

    title: str = Field(min_length=1, max_length=200)


class ConversationSummary(BaseModel):
    """Compressed memory that can be persisted alongside a transcript."""

    conversation_id: UUID = Field(default_factory=uuid4)
    summary: str = Field(min_length=1)
    open_questions: list[str] = Field(default_factory=list)
    recommended_next_actions: list[str] = Field(default_factory=list)


class PersonProfile(BaseModel):
    """Structured output used in Weeks 3 and 4."""

    name: str = Field(min_length=1)
    favorite_color: str = Field(min_length=1)
    birthday_iso: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")


class AuthenticatedUser(BaseModel):
    """JWT-derived user context used by secured endpoints and tools."""

    user_id: UUID
    email: str
    tenant_id: str = Field(min_length=1)


class DocumentChunk(BaseModel):
    """A single chunk that would later be embedded for retrieval."""

    document_id: UUID = Field(default_factory=uuid4)
    chunk_id: UUID = Field(default_factory=uuid4)
    source_name: str = Field(min_length=1)
    content: str = Field(min_length=1)
    metadata: dict[str, str] = Field(default_factory=dict)


class ChartSeries(BaseModel):
    """A named data series for frontend chart rendering."""

    label: str = Field(min_length=1)
    values: list[float] = Field(default_factory=list)


class ChartSpec(BaseModel):
    """Structured chart output returned by the visualization lesson."""

    title: str = Field(min_length=1)
    chart_type: str = Field(min_length=1)
    labels: list[str] = Field(default_factory=list)
    series: list[ChartSeries] = Field(default_factory=list)


ChartType = Literal["line", "bar", "pie", "donut", "scatter", "heatmap", "treemap"]


class VisualizationSpec(BaseModel):
    """A single chart specification produced by the Visualization Planner.

    The planner is exposed to the sub-agents as the LLM-powered `visualize_data`
    tool: it never executes SQL, never touches the database, and never generates
    frontend code — it only describes charts.
    """

    chart_type: ChartType
    title: str = Field(min_length=1)
    description: str = Field(default="")
    x_field: str | None = Field(default=None)
    y_field: str | None = Field(default=None)
    category_field: str | None = Field(default=None)
    value_field: str | None = Field(default=None)
    data: list[dict[str, Any]] = Field(default_factory=list)


class VisualizationResponse(BaseModel):
    """Structured output envelope returned by the Visualization Planner."""

    visualizations: list[VisualizationSpec] = Field(default_factory=list)


class ChatVisualizationResponse(BaseModel):
    """Response for the chat endpoint: the assistant message plus charts.

    The `visualizations` list is empty whenever the planner decided that no
    chart adds value to the reply.
    """

    message: str = Field(min_length=1)
    conversation_id: UUID
    visualizations: list[VisualizationSpec] = Field(default_factory=list)
