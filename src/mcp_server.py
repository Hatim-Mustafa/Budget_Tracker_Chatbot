from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any, Literal, cast
import calendar

from sqlalchemy.engine import CursorResult
from fastmcp import FastMCP
from fastmcp.server.dependencies import get_http_request
from sqlalchemy import and_, func, or_, select, text

from .db_backend import build_engine, build_session_factory
from .budget_db_backend import Budget, Category, Transaction
from .settings import AppSettings
import re

settings = AppSettings()
engine = build_engine(settings.database_url)
SessionFactory = build_session_factory(engine)

server = FastMCP("budget-tools")


def _current_user_id() -> int:
    request = get_http_request()
    raw_user_id = request.headers.get("x-current-user-id")
    if raw_user_id is None:
        raise RuntimeError("Missing x-current-user-id header on MCP request.")
    try:
        return int(raw_user_id)
    except ValueError as error:
        raise RuntimeError(f"Invalid x-current-user-id header: {raw_user_id!r}") from error


def _period_bounds(period: Literal["today", "this_week", "last_week", "this_month", "last_month"]) -> tuple[date, date]:
    today = date.today()
    if period == "today":
        return today, today
    if period == "this_week":
        start = today - timedelta(days=today.weekday())
        return start, today
    if period == "last_week":
        this_week_start = today - timedelta(days=today.weekday())
        start = this_week_start - timedelta(days=7)
        return start, this_week_start - timedelta(days=1)
    if period == "this_month":
        return today.replace(day=1), today
    if period == "last_month":
        first_of_this_month = today.replace(day=1)
        last_month_end = first_of_this_month - timedelta(days=1)
        return last_month_end.replace(day=1), last_month_end
    raise ValueError(f"Unknown period: {period}")


@server.tool
def resolve_category(category_name: str) -> dict[str, Any]:
    """Look up a category by (fuzzy) name for the current user, including global categories."""
    current_user_id = _current_user_id()
    with SessionFactory() as db:
        stmt = select(Category).where(
            and_(
                or_(Category.user_id == current_user_id, Category.user_id.is_(None)),
                Category.name.ilike(f"%{category_name}%"),
            )
        )
        matches = db.execute(stmt).scalars().all()
        return {
            "status": "success",
            "matches": [{"category_id": c.category_id, "name": c.name, "type": c.type} for c in matches],
        }


@server.tool
def create_transaction(
    amount: float,
    transaction_type: Literal["income", "expense"],
    category_id: int | None = None,
    description: str | None = None,
    transaction_date: str | None = None,
) -> dict[str, Any]:
    """Create a new transaction. category_id should come from resolve_category.

    If this is an expense against a category with a budget, the response includes
    a budget_warning field (null if not applicable) telling you whether this
    transaction pushes the user's spending to or past their alert_threshold for
    the current month — relay that to the user after confirming the log.
    """
    current_user_id = _current_user_id()
    with SessionFactory() as db:
        try:
            parsed_date = datetime.strptime(transaction_date, "%Y-%m-%d") if transaction_date else datetime.now()

            budget_warning = None
            if transaction_type == "expense" and category_id is not None:
                budget = db.execute(
                    select(Budget).where(
                        Budget.user_id == current_user_id,
                        Budget.category_id == category_id,
                    )
                ).scalar_one_or_none()

                if budget is not None:
                    month_start = date.today().replace(day=1)
                    spent_so_far = float(
                        db.execute(
                            select(func.coalesce(func.sum(Transaction.amount), 0)).where(
                                Transaction.user_id == current_user_id,
                                Transaction.category_id == category_id,
                                Transaction.transaction_type == "expense",
                                Transaction.transaction_date >= month_start,
                            )
                        ).scalar_one()
                    )
                    limit = float(budget.monthly_limit)
                    threshold = float(budget.alert_threshold)
                    projected_spent = spent_so_far + amount
                    projected_pct = projected_spent / limit if limit else 0.0

                    if projected_pct >= threshold:
                        budget_warning = {
                            "category_id": category_id,
                            "monthly_limit": limit,
                            "spent_before_this_transaction": spent_so_far,
                            "projected_spent_after_this_transaction": projected_spent,
                            "projected_pct_of_budget_used": round(projected_pct, 3),
                            "alert_threshold": threshold,
                            "over_limit": projected_spent > limit,
                        }

            txn = Transaction(
                user_id=current_user_id,
                category_id=category_id,
                amount=Decimal(str(amount)),
                transaction_type=transaction_type,
                description=description,
                transaction_date=parsed_date,
            )
            db.add(txn)
            db.commit()
            db.refresh(txn)
            return {
                "status": "success",
                "transaction_id": txn.transaction_id,
                "budget_warning": budget_warning,
            }
        except Exception as e:
            db.rollback()
            return {"status": "error", "error_details": str(e)}


@server.tool
def update_transaction(
    transaction_id: int,
    amount: float | None = None,
    category_id: int | None = None,
    description: str | None = None,
    transaction_date: str | None = None,
) -> dict[str, Any]:
    """Update fields on an existing transaction owned by the current user."""
    current_user_id = _current_user_id()
    with SessionFactory() as db:
        try:
            txn = db.execute(
                select(Transaction).where(
                    Transaction.transaction_id == transaction_id,
                    Transaction.user_id == current_user_id,
                )
            ).scalar_one_or_none()
            if txn is None:
                return {"status": "error", "error_details": "Transaction not found."}
            if amount is not None:
                txn.amount = Decimal(str(amount))
            if category_id is not None:
                txn.category_id = category_id
            if description is not None:
                txn.description = description
            if transaction_date is not None:
                txn.transaction_date = datetime.strptime(transaction_date, "%Y-%m-%d")
            db.commit()
            return {"status": "success", "message": "Transaction updated."}
        except Exception as e:
            db.rollback()
            return {"status": "error", "error_details": str(e)}


@server.tool
def delete_transaction(transaction_id: int) -> dict[str, Any]:
    """Delete a transaction owned by the current user."""
    current_user_id = _current_user_id()
    with SessionFactory() as db:
        try:
            txn = db.execute(
                select(Transaction).where(
                    Transaction.transaction_id == transaction_id,
                    Transaction.user_id == current_user_id,
                )
            ).scalar_one_or_none()
            if txn is None:
                return {"status": "error", "error_details": "Transaction not found."}
            db.delete(txn)
            db.commit()
            return {"status": "success", "message": "Transaction deleted."}
        except Exception as e:
            db.rollback()
            return {"status": "error", "error_details": str(e)}


@server.tool
def create_category(name: str, type: Literal["income", "expense"]) -> dict[str, Any]:
    """Create a new personal category for the current user."""
    current_user_id = _current_user_id()
    with SessionFactory() as db:
        try:
            category = Category(user_id=current_user_id, name=name, type=type)
            db.add(category)
            db.commit()
            db.refresh(category)
            return {"status": "success", "category_id": category.category_id}
        except Exception as e:
            db.rollback()
            return {"status": "error", "error_details": str(e)}


@server.tool
def get_spending_summary(
    period: Literal["today", "this_week", "last_week", "this_month", "last_month"],
    category_id: int | None = None,
) -> dict[str, Any]:
    """Get total income/expense for the current user over a period."""
    current_user_id = _current_user_id()
    with SessionFactory() as db:
        start, end = _period_bounds(period)
        conditions = [
            Transaction.user_id == current_user_id,
            Transaction.transaction_date >= start,
            Transaction.transaction_date < end + timedelta(days=1),
        ]
        if category_id is not None:
            conditions.append(Transaction.category_id == category_id)
        stmt = (
            select(Transaction.transaction_type, func.sum(Transaction.amount))
            .where(and_(*conditions))
            .group_by(Transaction.transaction_type)
        )
        rows = db.execute(stmt).all()
        totals = {row[0]: float(row[1]) for row in rows}
        return {
            "status": "success",
            "period": period,
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
            "total_income": totals.get("income", 0.0),
            "total_expense": totals.get("expense", 0.0),
        }


@server.tool
def get_budget_status(category_id: int | None = None) -> dict[str, Any]:
    """Get budget vs. actual spending for the current calendar month."""
    current_user_id = _current_user_id()
    with SessionFactory() as db:
        today = date.today()
        month_start = today.replace(day=1)
        days_in_month = calendar.monthrange(today.year, today.month)[1]

        conditions = [Budget.user_id == current_user_id]
        if category_id is not None:
            conditions.append(Budget.category_id == category_id)
        budgets = db.execute(select(Budget).where(and_(*conditions))).scalars().all()
        if not budgets:
            return {"status": "success", "budgets": [], "message": "No budgets set."}

        results = []
        for b in budgets:
            spent = float(
                db.execute(
                    select(func.coalesce(func.sum(Transaction.amount), 0)).where(
                        Transaction.user_id == current_user_id,
                        Transaction.category_id == b.category_id,
                        Transaction.transaction_type == "expense",
                        Transaction.transaction_date >= month_start,
                    )
                ).scalar_one()
            )
            limit = float(b.monthly_limit)
            pct_spent = spent / limit if limit else 0.0
            pct_month_elapsed = today.day / days_in_month
            results.append({
                "category_id": b.category_id,
                "monthly_limit": limit,
                "spent_so_far": spent,
                "remaining": limit - spent,
                "pct_of_budget_used": round(pct_spent, 3),
                "pct_of_month_elapsed": round(pct_month_elapsed, 3),
                "pacing": "ahead" if pct_spent > pct_month_elapsed else "on_track_or_under",
                "alert_threshold_hit": pct_spent >= float(b.alert_threshold),
            })
        return {"status": "success", "budgets": results}


@server.tool
def change_budget(
    category_id: int,
    monthly_limit: float | None = None,
    alert_threshold: float | None = None,
) -> dict[str, Any]:
    """Create or update the monthly budget for a category.

    If no budget exists yet for this category, one is created (monthly_limit is
    required in that case). If a budget already exists, only the fields you pass
    are updated — pass only alert_threshold to change the alert rate without
    touching the limit, for example.
    """
    current_user_id = _current_user_id()
    with SessionFactory() as db:
        try:
            budget = db.execute(
                select(Budget).where(
                    Budget.user_id == current_user_id,
                    Budget.category_id == category_id,
                )
            ).scalar_one_or_none()

            if budget is None:
                if monthly_limit is None:
                    return {
                        "status": "error",
                        "error_details": (
                            "No budget exists yet for this category — monthly_limit "
                            "is required to create one."
                        ),
                    }
                budget = Budget(
                    user_id=current_user_id,
                    category_id=category_id,
                    monthly_limit=Decimal(str(monthly_limit)),
                    alert_threshold=Decimal(str(alert_threshold)) if alert_threshold is not None else Decimal("0.80"),
                )
                db.add(budget)
                db.commit()
                db.refresh(budget)
                return {"status": "success", "budget_id": budget.budget_id, "message": "Budget created."}

            if monthly_limit is not None:
                budget.monthly_limit = Decimal(str(monthly_limit))
            if alert_threshold is not None:
                budget.alert_threshold = Decimal(str(alert_threshold))
            db.commit()
            return {"status": "success", "budget_id": budget.budget_id, "message": "Budget updated."}
        except Exception as e:
            db.rollback()
            return {"status": "error", "error_details": str(e)}

USER_SCOPED_TABLES = {"transactions", "categories", "budgets"}


def _check_user_scoping(clean_query: str) -> dict[str, Any] | None:
    """Return an error dict if a user-scoped query doesn't filter by :current_user_id."""
    touches_scoped_table = any(
        re.search(rf"\b{table}\b", clean_query, re.IGNORECASE)
        for table in USER_SCOPED_TABLES
    )
    if touches_scoped_table and ":current_user_id" not in clean_query:
        return {
            "status": "error",
            "error_details": (
                "This query touches user-scoped data but does not filter by "
                "user_id using the :current_user_id bind parameter. Rewrite the "
                "query to include e.g. 'WHERE user_id = :current_user_id'."
            ),
        }
    return None

def execute_select_query(query: str) -> dict[str, Any]:
    """Run a read-only SELECT query against the database and return the results.

    Only SELECT statements are permitted here. To insert, update, or delete data,
    the transactions_agent must use execute_write_query instead.

    IMPORTANT: never hardcode a user_id value. Any filter on user_id must use the
    named bind parameter :current_user_id (e.g. "WHERE user_id = :current_user_id").
    The actual value is supplied by the system, not by you.
    """
    clean_query = query.strip().rstrip(";")

    first_word = clean_query.split(None, 1)[0].upper() if clean_query else ""
    if first_word != "SELECT":
        return {
            "status": "error",
            "error_details": (
                f"Statement type '{first_word}' is not permitted here — "
                "execute_select_query only accepts SELECT statements."
            ),
        }

    error = _check_user_scoping(clean_query)
    if error:
        return error

    with SessionFactory() as db:

        try:
            result = cast(
                CursorResult,
                db.execute(
                    text(clean_query),
                    {"current_user_id": _current_user_id()},
                ),
            )
            columns = list(result.keys())
            rows = [dict(zip(columns, row)) for row in result.fetchall()]
            return {"status": "success", "row_count": len(rows), "data": rows}
        except Exception as e:
            db.rollback()
            return {"status": "error", "error_details": str(e)}

def execute_write_query(query: str) -> dict[str, Any]:
    """Run a write (INSERT, UPDATE, or DELETE) query against the database.

    Only transactions_agent has access to this tool. For any read/lookup, use
    execute_select_query instead.

    IMPORTANT: never hardcode a user_id value. Any filter or inserted value for
    user_id must use the named bind parameter :current_user_id (e.g.
    "WHERE user_id = :current_user_id"). The actual value is supplied by the
    system, not by you.
    """
    clean_query = query.strip().rstrip(";")

    first_word = clean_query.split(None, 1)[0].upper() if clean_query else ""
    if first_word not in {"INSERT", "UPDATE", "DELETE"}:
        return {
            "status": "error",
            "error_details": (
                f"Statement type '{first_word}' is not permitted here — "
                "execute_write_query only accepts INSERT, UPDATE, or DELETE."
            ),
        }

    error = _check_user_scoping(clean_query)
    if error:
        return error

    with SessionFactory() as db:
        try:
            result = cast(
                CursorResult,
                db.execute(
                    text(clean_query),
                    {"current_user_id": _current_user_id()},
                ),
            )
            db.commit()
            return {
                "status": "success",
                "affected_rows": result.rowcount,
                "message": "Query executed successfully.",
            }
        except Exception as e:
            db.rollback()
            return {"status": "error", "error_details": str(e)}


if __name__ == "__main__":
    server.run(transport="streamable-http", host="127.0.0.1", port=8000, path="/mcp")