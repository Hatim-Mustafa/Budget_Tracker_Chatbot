from typing import Union

import pandas as pd


def summarize_dataframe(df: pd.DataFrame, threshold: int = 30) -> str:
    """
    Summarizes a Pandas DataFrame if row count exceeds threshold.
    Returns markdown-formatted output ready for LLM processing.
    """
    if len(df) <= threshold:
        return df.to_markdown(index=False)

    summary_parts = []

    # 1. Header & Dataset Size
    summary_parts.append(
        f"⚠️ **Query returned {len(df)} records** (exceeding context limit of {threshold}). "
        f"Providing summarized statistics below:"
    )

    # Convert numeric and datetime types safely
    if "amount" in df.columns:
        df["amount"] = pd.to_numeric(df["amount"], errors="coerce")
    if "transaction_date" in df.columns:
        df["transaction_date"] = pd.to_datetime(df["transaction_date"], errors="coerce")

    # 2. Time Range (if transaction_date exists)
    if "transaction_date" in df.columns and not df["transaction_date"].dropna().empty:
        min_date = df["transaction_date"].min().strftime("%Y-%m-%d")
        max_date = df["transaction_date"].max().strftime("%Y-%m-%d")
        summary_parts.append(f"**Date Range:** {min_date} to {max_date}")

    # 3. Financial Totals (if transaction_type & amount exist)
    if "amount" in df.columns:
        if "transaction_type" in df.columns:
            income_mask = df["transaction_type"] == "income"
            expense_mask = df["transaction_type"] == "expense"

            total_income = df.loc[income_mask, "amount"].sum()
            total_expense = df.loc[expense_mask, "amount"].sum()
            net_flow = total_income - total_expense

            summary_parts.append(
                f"### 💵 Financial Totals\n"
                f"- **Total Income:** ${total_income:,.2f} ({income_mask.sum()} items)\n"
                f"- **Total Expenses:** ${total_expense:,.2f} ({expense_mask.sum()} items)\n"
                f"- **Net Cash Flow:** ${net_flow:,.2f}"
            )
        else:
            total_val = df["amount"].sum()
            avg_val = df["amount"].mean()
            summary_parts.append(
                f"### 💵 Financial Totals\n"
                f"- **Total Sum:** ${total_val:,.2f}\n"
                f"- **Average:** ${avg_val:,.2f}"
            )

    # 4. Grouping by Category (if category column exists)
    category_col = next(
        (c for c in ["category_name", "category", "category_id"] if c in df.columns), None
    )
    if category_col and "amount" in df.columns:
        cat_summary = (
            df.groupby(category_col)["amount"]
            .agg(["sum", "count"])
            .sort_values(by="sum", ascending=False)
            .head(5)
        )
        cat_lines = [
            f"- **{cat}**: ${row['sum']:,.2f} ({int(row['count'])} transactions)"
            for cat, row in cat_summary.iterrows()
        ]
        summary_parts.append("### 🏷 Top 5 Categories by Total Volume\n" + "\n".join(cat_lines))

    # 5. Outliers / Highest Transactions
    if "amount" in df.columns:
        top_3 = df.nlargest(3, "amount")
        cols_to_show = [
            c
            for c in ["transaction_date", "description", "category_name", "amount"]
            if c in df.columns
        ]
        summary_parts.append(
            "### 🔝 Top 3 Largest Transactions\n" + top_3[cols_to_show].to_markdown(index=False)
        )

    # 6. Sample Rows (First 2 + Last 2)
    sample_df = pd.concat([df.head(2), df.tail(2)]).drop_duplicates()
    summary_parts.append("### 🔍 Row Samples (Start & End)\n" + sample_df.to_markdown(index=False))

    return "\n\n".join(summary_parts)
