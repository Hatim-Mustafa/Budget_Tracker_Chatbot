from typing import Any

from pydantic_ai import Agent
from pydantic_ai.messages import ModelMessage, ModelRequest, ModelResponse, SystemPromptPart, TextPart, UserPromptPart
from pydantic_ai.models.groq import GroqModel
from pydantic_ai.models.google import GoogleModel

from src.budget_db_backend import Category

from .models import ChatMessage, MessageRole
from .settings import AppSettings

from dataclasses import dataclass, field
from sqlalchemy import or_, select, text
from sqlalchemy.orm import Session
from pydantic_ai import RunContext
import re

from subagents_pydantic_ai import SubAgentCapability, SubAgentConfig
from pydantic_ai.mcp import MCPToolset


SYSTEM_PROMPT = """
You are the orchestrator for a conversational personal finance assistant. You talk to the
user directly and decide, on every turn, whether to answer yourself or delegate to a
specialized sub-agent.

Your job is classification and delegation, not database work. You do not know the
database schema and you must never attempt to write or reason about SQL yourself — that
belongs entirely to the sub-agent(s) you delegate to.

There are three sub-agents. Pick exactly one per user request — do not delegate the same
request to more than one sub-agent unless the user has clearly asked two distinct things
in the same message.

Delegate to `transactions_agent` when the user is:
- Logging or recording a new transaction in natural language (e.g. "put $45 down for gas
  on my credit card", "I got paid $2000 today", "log a $30 dinner expense").
- Asking to correct, delete, or update a specific transaction they already logged.
transactions_agent is the only sub-agent with write access to the database (it can
look up existing data too, e.g. to resolve a category name before inserting a row).
-It can also make changes to budgets and categories, but only if the user explicitly asks to do so. 
It cannot make any changes to budgets or categories on its own initiative.

Delegate to `analytics_agent` when the user is asking about their *current or past*
financial state — anything answerable by looking at data that already exists:
- Spending/income totals, category breakdowns, budget pacing or remaining balance
  (e.g. "how much have I spent on groceries this month", "am I over budget on dining",
  "what's my remaining balance").
- Historical trends or comparisons (e.g. "did I spend more on food this month than last
  month").
analytics_agent is read-only — it can never log, edit, or delete a transaction.

Delegate to `advisor_agent` when the user is asking a *forward-looking or hypothetical*
question that requires judgment or recommendation, not just a lookup:
- "Can I afford a $1,200 vacation next month?"
- "Should I cut back on dining out?"
- "What should I do to hit my savings goal?"
advisor_agent is also read-only — it can never log, edit, or delete a transaction.

If a request spans more than one of these (e.g. "how much have I spent on dining, and can
I still afford a $200 dinner this weekend?"), delegate each part to the right sub-agent
separately and combine both results in your reply.

When delegating, pass the sub-agent a self-contained task: rephrase the user's request in
full (amount, category/merchant if mentioned, account, date if relevant) since the
sub-agent does not see this conversation's history. Don't just forward the raw user
message if it depends on earlier turns — resolve pronouns and prior context yourself
first (e.g. "what about last week" -> "What did the user spend on dining last week?").
If a question needs analytics context to answer (e.g. advisor_agent needing current
spending pace), delegate to analytics_agent first, then pass that result into the task
you give advisor_agent.

Handle directly, without delegating:
- Small talk, clarifying questions, and general app/feature questions.
- If any of the subagents throw any sort of error, tell that to the user, the actual
  error and your understanding of it.
- Disambiguation: if the user's request is genuinely ambiguous (e.g. unclear whether
  they mean income or expense, which category, or whether they want a lookup vs. advice),
  ask one short clarifying question before delegating.

Always respond in the user's currency and phrasing where possible, keep responses
concise, and never fabricate transaction data, balances, or budget numbers yourself —
any figure you state must come from a sub-agent's result.
"""


@dataclass
class AgentState:
    db: Session
    current_user_id: int
    subagents: dict[str, Any] = field(default_factory=dict)

    def clone_for_subagent(self, max_depth: int = 0) -> "AgentState":
        """Create deps for a delegated sub-agent run.

        Shares the same db session and current_user_id (sub-agents need the
        same DB access and act on behalf of the same user). `subagents` is
        reset to empty since max_nesting_depth=0 in our SubAgentCapability
        config means sub-agents cannot themselves delegate further.
        """
        return AgentState(
            db=self.db,
            current_user_id=self.current_user_id,
            subagents={} if max_depth <= 0 else self.subagents,
        )


def chat_messages_to_model_messages(messages: list[ChatMessage]) -> list[ModelMessage]:
    """Convert a stored conversation transcript into pydantic-ai's message_history format.

    Each ChatMessage becomes a ModelRequest (user/system turns) or ModelResponse
    (assistant turns) so the agent can be given prior conversation context via
    `agent.run(prompt, message_history=...)`.
    """
    history: list[ModelMessage] = []
    for msg in messages:
        if msg.role == MessageRole.USER:
            history.append(ModelRequest(parts=[UserPromptPart(content=msg.content)]))
        elif msg.role == MessageRole.ASSISTANT:
            history.append(ModelResponse(parts=[TextPart(content=msg.content)]))
        elif msg.role == MessageRole.SYSTEM:
            history.append(ModelRequest(parts=[SystemPromptPart(content=msg.content)]))
        # MessageRole.TOOL is intentionally skipped: ChatMessage doesn't carry the
        # tool_call_id/tool_name needed to reconstruct a valid ToolReturnPart.
    return history

async def summarize_chat(messages: list[ModelMessage], max_messages: int = 10) -> list[ModelMessage]:
    """Compress a long transcript into a lightweight summary string.

    This is a simplified version of the summarize_chat function in week05_analytics.py,
    returning just a string instead of a ConversationSummary dataclass. It can be used
    to provide context to the agent without storing the full transcript.
    """
    if len(messages) > max_messages:
        messages = messages[-6:]
        effective_settings = AppSettings()
        model = GoogleModel(effective_settings.gemini_model)
        agent = Agent(model, name="chat_summarizer", description="Summarizes a chat transcript into a concise summary.", output_type=str)
        summary = await agent.run("Please summarize the chat", message_history=messages[:-6])
        system_message = ModelRequest(
            parts=[SystemPromptPart(content=f"Summary of previous messages: {summary}")]
        )
        messages = [system_message] + messages[-6:]
        return messages
    return []


def create_agent(current_user_id: int, settings: AppSettings | None = None) -> Agent[AgentState]:
    effective_settings = settings or AppSettings()
    model = GroqModel(effective_settings.groq_model)

    budget_tools = MCPToolset(
        "http://localhost:8000/mcp",
        headers={"x-current-user-id": str(current_user_id)},
    )

    transactions_agent = Agent(
        model,
        deps_type=AgentState,
        name="transactions_agent",
        description="A sub-agent that can convert a user's natural language request into a database query and run it for the transactions database.",
        toolsets=[budget_tools],
    )

    analytics_agent = Agent(
        model,
        deps_type=AgentState,
        name="analytics_agent",
        description="A sub-agent that answers questions about the user's spending, income, and budget data by analyzing the transactions database.",
        toolsets=[budget_tools],
    )

    advisor_agent = Agent(
        model,
        deps_type=AgentState,
        name="advisor_agent",
        description="A sub-agent that provides financial advice and recommendations based on the user's spending, income, and budget data.",
        toolsets=[budget_tools],
    )

    orchestrator_agent = Agent(
        model,
        deps_type=AgentState,
        instructions=SYSTEM_PROMPT,
        capabilities=[
            SubAgentCapability(
                subagents=[
                    SubAgentConfig(
                        name="transactions_agent",
                        description="A sub-agent that can convert a user's natural language request into a database query and run it for the transactions database.",
                        instructions="",  # unused: `agent` below is a pre-built Agent, so this SubAgentConfig field is ignored by _compile_subagent, but the TypedDict still requires the key
                        agent=transactions_agent,
                    ),
                    SubAgentConfig(
                        name="analytics_agent",
                        description="A sub-agent that answers questions about the user's spending, income, and budget data by analyzing the transactions database.",
                        instructions="",  # unused: `agent` below is a pre-built Agent, so this SubAgentConfig field is ignored by _compile_subagent, but the TypedDict still requires the key
                        agent=analytics_agent,
                    ),
                    SubAgentConfig(
                        name="advisor_agent",
                        description="A sub-agent that provides financial advice and recommendations based on the user's spending, income, and budget data.",
                        instructions="",  # unused: `agent` below is a pre-built Agent, so this SubAgentConfig field is ignored by _compile_subagent, but the TypedDict still requires the key
                        agent=advisor_agent,
                    )
                ],
                default_model=model,  # otherwise defaults to "openai:gpt-4.1" and needs OPENAI_API_KEY
                include_general_purpose=False,  # we only want our own named sub-agents, not an auto general-purpose one
            )
        ],
    )

    

    @transactions_agent.instructions
    def budget_alert_instructions(ctx: RunContext[AgentState]) -> str:
        return (
            "When you call create_transaction for an expense, its response includes a "
            "budget_warning field. If budget_warning is not null, it means this "
            "transaction pushes the user's spending in that category to or past their "
            "alert_threshold for the current month (over_limit is true if it exceeds "
            "the limit entirely). Tell the user about this clearly — how much of their "
            "budget is now used and whether they've gone over — alongside confirming "
            "the transaction was logged. This is informational only; the transaction "
            "is already logged by the time you see this, do not ask the user for "
            "confirmation before logging.\n\n"
            "If budget_warning is null, no budget was crossed (or no budget exists for "
            "that category) — just confirm the transaction normally."
        )

    @transactions_agent.instructions
    @analytics_agent.instructions
    @advisor_agent.instructions
    def build_schema_context(ctx: RunContext[AgentState]) -> str:
        try:
            result = ctx.deps.db.execute(
                select(Category).where(
                    or_(
                        Category.user_id == ctx.deps.current_user_id,
                        Category.user_id.is_(None),
                    )
                )
            )
            categories = result.scalars().all()
        except Exception:
            raise

        if categories:
            category_lines = "\n".join(
                f"- id={c.category_id}, name={c.name!r}, type={c.type}"
                for c in categories
            )
        else:
            category_lines = "(no categories defined for this user yet)"

        return (
            f"{SCHEMA_CONTEXT}\n\n"
            "You have access to a set of structured tools for common operations — e.g. "
            "resolve_category, create_transaction, update_transaction, delete_transaction, "
            "create_category, get_spending_summary, get_budget_status, change_budget "
            "(availability depends on your role). ALWAYS prefer one of these structured "
            "tools over writing raw SQL. Only fall back to the dynamic SQL tools "
            "(execute_select_query / execute_write_query) when none of the structured "
            "tools can accomplish what's being asked — e.g. an unusual lookup or a "
            "combination of filters no existing tool supports.\n\n"
            "IMPORTANT — this next rule applies ONLY when you fall back to "
            "execute_select_query or execute_write_query (the structured tools already "
            "handle the current user internally, so it does not apply to them): never "
            "write a literal user_id value (e.g. 'user_id = 42') in the query text. You "
            "do not know the current user's actual id and must not guess it. Always "
            "filter user-scoped tables (transactions, categories, budgets) using the "
            "named bind parameter :current_user_id, e.g. "
            "'WHERE user_id = :current_user_id'. The real value is substituted by the "
            "system when the query runs.\n\n"
            "SPECIAL CASE for categories: some rows in the categories table have "
            "user_id = NULL. These are global default categories available to every "
            "user, not just the current one. If you fall back to execute_select_query "
            "on the categories table, you must match rows belonging to the current "
            "user AS WELL AS these global ones, e.g. "
            "'WHERE user_id = :current_user_id OR user_id IS NULL'. Do not filter "
            "categories by :current_user_id alone or you will miss valid global "
            "categories the user can still use.\n\n"
            f"Categories belonging to the current user:\n{category_lines}"
        )



    return orchestrator_agent


SCHEMA_CONTEXT = """
You are working with the following PostgreSQL schema:

TABLE users (
    user_id SERIAL PRIMARY KEY,
    email VARCHAR(100) UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    currency VARCHAR(3) DEFAULT 'USD'
)

TABLE categories (
    category_id SERIAL PRIMARY KEY,
    user_id INT REFERENCES users(user_id) ON DELETE CASCADE,  -- NULL = system global default
    name VARCHAR(50) NOT NULL,
    type VARCHAR(10) CHECK (type IN ('income', 'expense'))
)

TABLE transactions (
    transaction_id SERIAL PRIMARY KEY,
    user_id INT REFERENCES users(user_id) ON DELETE CASCADE,
    category_id INT REFERENCES categories(category_id) ON DELETE SET NULL,
    amount DECIMAL(12, 2) NOT NULL,
    transaction_type VARCHAR(10) CHECK (transaction_type IN ('income', 'expense', 'transfer')),
    description TEXT,
    transaction_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
)

TABLE budgets (
    budget_id SERIAL PRIMARY KEY,
    user_id INT REFERENCES users(user_id) ON DELETE CASCADE,
    category_id INT REFERENCES categories(category_id) ON DELETE CASCADE,
    monthly_limit DECIMAL(12, 2) NOT NULL,
    alert_threshold DECIMAL(3,2) DEFAULT 0.80
)
""".strip()
