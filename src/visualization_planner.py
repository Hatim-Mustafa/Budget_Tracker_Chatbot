"""LLM-powered Visualization Planner — a tool available to the sub-agents.

The planner is **not** a top-level agent and it is **not** a post-processing
stage. It is exposed to the sub-agents (transactions, analytics, advisor) as a
tool named `visualize_data`: the sub-agent decides — based on the user query and
the structured data it just fetched — whether charts would help, and if so it
calls the tool. The tool runs an LLM to turn the structured data into typed
`VisualizationSpec` objects.

Constraints (mirrored from the architecture doc):
- Never executes SQL and never touches the database.
- Never generates React/HTML/JS or ECharts config — it only produces typed
  `VisualizationSpec` objects that the frontend turns into ECharts options.
- Returns an empty list when a visualization adds little value.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from pydantic_ai import Agent
from pydantic_ai.models.google import GoogleModel

from .models import VisualizationResponse, VisualizationSpec
from .settings import AppSettings

logger = logging.getLogger(__name__)

#: Name of the LLM-powered tool registered on the sub-agents.
VISUALIZE_DATA_TOOL_NAME = "visualize_data"

PLANNER_SYSTEM_PROMPT = """
You are the Visualization Planner tool for a personal finance assistant. A
sub-agent calls you after fetching structured data, and your job is to decide
which charts would genuinely help the user understand those results.

You receive:
- the user's original query,
- the structured data the sub-agent fetched (JSON tool outputs),
- optionally, a short draft of the reply the charts would accompany.

Pick zero or more visualizations. Use these selection rules:

| Data                          | Chart            |
| ----------------------------- | ---------------- |
| Time series                   | line             |
| Category comparison           | bar              |
| Proportions                   | pie / donut      |
| Rankings                      | bar (sorted)     |
| Correlation                   | scatter          |
| Hierarchy                     | treemap          |
| Calendar activity             | heatmap          |
| Single KPI / single row       | no chart         |

Guidelines:
- Return an EMPTY list if no chart adds value: single values, single rows,
  plain confirmations ("transaction logged"), or tiny datasets (fewer than ~3
  data points) usually need no chart. When in doubt, return an empty list.
- Max 3 visualizations per reply; never duplicate the same data twice.
- The reply text should make sense without the charts — charts are decoration.
- Data hygiene: if a result row contains fields like `status`, `message`, or
  `error_details`, exclude them from chart data unless they are the values being
  compared. Prefer rows that carry actual numeric values.
- If the structured result is a single dict rather than a list, use its list-
  valued keys (e.g. "transactions", "budgets", "summary") as the chart data, or
  extract the series you need. Never chart a bare status/error dict.

For each visualization you emit:
- `chart_type`: one of "line", "bar", "pie", "donut", "scatter", "heatmap",
  "treemap". Use "donut" for proportions with a hole in the middle.
- `title`: short, specific (e.g. "Spending by category — July").
- `description`: one sentence explaining what the chart shows (e.g. "Groceries
  and dining are the two largest expense categories this month.").
- `x_field` / `y_field`: names of the columns used for the x axis and y axis
  (line/bar/scatter).
- `category_field` / `value_field`: names of the columns used for slice/label
  names and values (pie/donut/treemap).
- For heatmap: `x_field` and `y_field` name the row/column grouping columns and
  `value_field` the cell value column.
- `data`: a JSON array of plain row objects containing ONLY the fields referenced
  by the chart (plus anything needed to distinguish rows). Keep numbers as
  numbers — do not stringify amounts.
- Every field name you reference in x_field/y_field/category_field/value_field
  MUST exist in your `data` rows. If the source uses different names, rename the
  keys in `data` to match your chosen fields.

Never invent data: chart only numbers that are present in the structured query
results. Do not describe SQL, database calls, or implementation details.
""".strip()


class VisualizationPlanner:
    """LLM engine behind the `visualize_data` tool registered on the sub-agents."""

    def __init__(self, settings: AppSettings | None = None) -> None:
        effective_settings = settings or AppSettings()
        self._agent = Agent(
            GoogleModel(effective_settings.gemini_model),
            name="visualization_planner",
            description=(
                "Decides which charts would help the user understand a finance "
                "query result and emits typed visualization specifications."
            ),
            system_prompt=PLANNER_SYSTEM_PROMPT,
            output_type=VisualizationResponse,
        )

    async def plan(
        self,
        *,
        user_query: str,
        structured_data: list[dict[str, Any]],
        assistant_message: str = "",
    ) -> list[VisualizationSpec]:
        """Return zero or more visualization specs for the given structured data.

        Called from the `visualize_data` tool with the data the sub-agent
        fetched. Any failure degrades to an empty list — charts must never
        break the conversation.
        """
        prompt = (
            "User query:\n"
            f"{user_query}\n\n"
            "Assistant reply (draft):\n"
            f"{assistant_message or '(no draft provided)'}\n\n"
            "Structured query results:\n"
            f"{json.dumps(structured_data, default=str)}"
        )
        try:
            result = await self._agent.run(prompt)
        except Exception:
            logger.exception("Visualization planner failed; returning no charts")
            return []
        return result.output.visualizations
