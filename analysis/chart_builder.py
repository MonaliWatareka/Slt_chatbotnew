import json
import re
import pandas as pd
import plotly.express as px
from langchain_ollama import OllamaLLM
from analysis.excel_reader import get_column_summary


def build_chart(user_request: str, df: pd.DataFrame, model: str = "llama3.2"):
    df      = df.copy()
    df["Count"] = 1

    col_summary = get_column_summary(df)
    spec        = _ask_llm_for_chart_spec(user_request, col_summary, model)

    if spec is None:
        return (
            "⚠️ Could not understand the chart request. "
            "Try: 'Bar chart of Churn by InternetService'",
            None,
        )

    chart_type = spec.get("chart_type", "bar").lower()
    x_col      = spec.get("x_col") or ""
    y_col      = spec.get("y_col") or ""
    title      = spec.get("title") or user_request
    color_col  = spec.get("color_col") or None

    if color_col and (color_col == "null" or color_col not in df.columns):
        color_col = None

    x_col = _resolve_column(x_col, user_request, df)
    y_col = _resolve_column(y_col, user_request, df, exclude=x_col)

    # ── Pie chart ──────────────────────────────────────────────────────────────
    if chart_type == "pie":
        if not x_col or x_col not in df.columns:
            x_col = _fallback_column(df, prefer="text")

        if y_col and y_col in df.columns and pd.api.types.is_numeric_dtype(df[y_col]):
            fig = px.pie(df, names=x_col, values=y_col,
                         title=title, template="plotly_white", hole=0.3)
        else:
            counts         = df[x_col].value_counts().reset_index()
            counts.columns = [x_col, "Count"]
            fig = px.pie(counts, names=x_col, values="Count",
                         title=title, template="plotly_white", hole=0.3)

        fig.update_traces(textposition="inside", textinfo="percent+label")
        fig.update_layout(title_font_size=18, margin=dict(t=60, b=40, l=40, r=40))
        summary    = _generate_chart_summary(df, x_col, y_col, chart_type, title, model)
        reply_text = f"Here is your **pie chart**: *{title}*"
        if summary:
            reply_text += f"\n\n📊 **Summary:** {summary}"
        return (reply_text, fig)

    # ── Bar chart ──────────────────────────────────────────────────────────────
    if chart_type == "bar":
        if not x_col or x_col not in df.columns:
            x_col = _fallback_column(df, prefer="text")

        # Categorical Y (e.g. Yes/No) — group and count
        if y_col and y_col in df.columns and df[y_col].dtype == object:
            agg_df = df.groupby([x_col, y_col]).size().reset_index(name="Count")
            fig = px.bar(
                agg_df, x=x_col, y="Count", color=y_col,
                title=title, template="plotly_white",
                barmode="group", text_auto=True,
            )
            fig.update_traces(textposition="outside")
            fig.update_layout(
                title_font_size=18,
                margin=dict(t=60, b=40, l=40, r=40),
                xaxis_title=x_col,
                yaxis_title="Count",
            )
            summary    = _generate_chart_summary(df, x_col, y_col, chart_type, title, model)
            reply_text = f"Here is your **bar chart**: *{title}*"
            if summary:
                reply_text += f"\n\n📊 **Summary:** {summary}"
            return (reply_text, fig)

        # Numeric Y — plot directly
        if y_col and y_col in df.columns and pd.api.types.is_numeric_dtype(df[y_col]):
            fig = px.bar(df, x=x_col, y=y_col, title=title,
                         template="plotly_white", text_auto=True)
            fig.update_traces(textposition="outside")
            fig.update_layout(title_font_size=18, margin=dict(t=60, b=40, l=40, r=40))
            summary    = _generate_chart_summary(df, x_col, y_col, chart_type, title, model)
            reply_text = f"Here is your **bar chart**: *{title}*"
            if summary:
                reply_text += f"\n\n📊 **Summary:** {summary}"
            return (reply_text, fig)

        # Fallback — count by x_col
        counts         = df[x_col].value_counts().reset_index()
        counts.columns = [x_col, "Count"]
        fig = px.bar(counts, x=x_col, y="Count", title=title,
                     template="plotly_white", text_auto=True)
        fig.update_traces(textposition="outside")
        fig.update_layout(title_font_size=18, margin=dict(t=60, b=40, l=40, r=40))
        summary    = _generate_chart_summary(df, x_col, y_col, chart_type, title, model)
        reply_text = f"Here is your **bar chart**: *{title}*"
        if summary:
            reply_text += f"\n\n📊 **Summary:** {summary}"
        return (reply_text, fig)

    # ── All other chart types ──────────────────────────────────────────────────
    if not x_col or x_col not in df.columns:
        x_col = _fallback_column(df, prefer="text")
    if not y_col or y_col not in df.columns:
        y_col = _fallback_column(df, prefer="number", exclude=x_col)

    missing = [c for c in [x_col, y_col] if c and c not in df.columns]
    if missing:
        return (
            f"⚠️ Column(s) not found: {missing}\n"
            f"Available columns: {list(df.columns)}",
            None,
        )

    fig        = _build_plotly_chart(df, chart_type, x_col, y_col, title, color_col)
    summary    = _generate_chart_summary(df, x_col, y_col, chart_type, title, model)
    reply_text = f"Here is your **{chart_type} chart**: *{title}*"
    if summary:
        reply_text += f"\n\n📊 **Summary:** {summary}"
    return (reply_text, fig)


# ── Helpers ────────────────────────────────────────────────────────────────────

def _resolve_column(col_name: str, user_message: str, df: pd.DataFrame,
                    exclude: str = "") -> str:
    if col_name and col_name in df.columns:
        return col_name
    message_lower = user_message.lower()
    for col in df.columns:
        if col == exclude:
            continue
        if col.lower() in message_lower:
            return col
    words = re.findall(r'\b\w+\b', message_lower)
    for word in words:
        if len(word) <= 3:
            continue
        for col in df.columns:
            if col == exclude:
                continue
            if word in col.lower():
                return col
    return col_name


def _fallback_column(df: pd.DataFrame, prefer: str = "text",
                     exclude: str = "") -> str:
    cols = (df.select_dtypes(include="object").columns.tolist()
            if prefer == "text"
            else df.select_dtypes(include="number").columns.tolist())
    for col in cols:
        if col != exclude:
            return col
    return ""


def _ask_llm_for_chart_spec(user_request: str, col_summary: str, model: str):
    llm    = OllamaLLM(model=model, temperature=0)
    prompt = f"""You are a data analyst. Return ONLY a JSON object, nothing else.

Available columns:
{col_summary}

User wants: "{user_request}"

Return this exact JSON format:
{{"chart_type": "bar", "x_col": "column_name", "y_col": "column_name_or_null", "color_col": null, "title": "Chart Title"}}

Rules:
- chart_type must be one of: bar, pie, line, scatter, histogram, area
- x_col and y_col must be EXACT column names from above
- For "bar chart of Churn by InternetService": x_col=InternetService, y_col=Churn
- color_col must always be null
- Return ONLY the JSON, no explanation"""

    raw = llm.invoke(prompt)
    print(f"[chart_builder] LLM raw: {raw}")

    try:
        return _sanitize(json.loads(raw.strip()))
    except Exception:
        pass

    match = re.search(r'\{[^{}]+\}', raw, re.DOTALL)
    if match:
        try:
            return _sanitize(json.loads(match.group()))
        except Exception:
            pass

    return _manual_spec(user_request, col_summary)


def _sanitize(spec: dict) -> dict:
    for key in ("color_col", "y_col"):
        if spec.get(key) in ("null", "", "none", "None", "NULL"):
            spec[key] = None
    return spec


def _manual_spec(user_request: str, col_summary: str) -> dict:
    req        = user_request.lower()
    chart_type = "bar"
    for ct in ["pie", "line", "scatter", "histogram", "area", "bar"]:
        if ct in req:
            chart_type = ct
            break

    col_names = re.findall(r"'([^']+)'", col_summary)
    x_col, y_col = "", ""

    match = re.search(r'of\s+(\w+)\s+by\s+(\w+)', req)
    if match:
        term1, term2 = match.group(1), match.group(2)
        for col in col_names:
            if term1 in col.lower() and not y_col:
                y_col = col
            if term2 in col.lower() and not x_col:
                x_col = col

    if not x_col:
        match = re.search(r'(\w+)\s+by\s+(\w+)', req)
        if match:
            term1, term2 = match.group(1), match.group(2)
            for col in col_names:
                if term2 in col.lower():
                    x_col = col
                if term1 in col.lower():
                    y_col = col

    if not x_col:
        x_col = col_names[0] if col_names else ""
    if not y_col and chart_type != "pie":
        y_col = col_names[-1] if col_names else ""

    return {
        "chart_type": chart_type,
        "x_col":      x_col,
        "y_col":      y_col,
        "color_col":  None,
        "title":      user_request.capitalize(),
    }


def _build_plotly_chart(df, chart_type, x_col, y_col, title, color_col=None):
    kwargs = dict(x=x_col, y=y_col, title=title, template="plotly_white")
    if color_col and color_col in df.columns:
        kwargs["color"] = color_col

    if chart_type == "line":
        fig = px.line(df, **kwargs, markers=True)
    elif chart_type == "scatter":
        fig = px.scatter(df, **kwargs)
    elif chart_type == "histogram":
        fig = px.histogram(df, x=x_col, title=title, template="plotly_white")
    elif chart_type == "area":
        fig = px.area(df, **kwargs)
    else:
        fig = px.bar(df, **kwargs)

    fig.update_layout(
        title_font_size=18,
        margin=dict(t=60, b=40, l=40, r=40),
        xaxis_title=x_col,
        yaxis_title=y_col,
    )
    return fig


def _generate_chart_summary(df: pd.DataFrame, x_col: str, y_col: str,
                              chart_type: str, title: str,
                              model: str = "llama3.2") -> str:
    llm = OllamaLLM(model=model, temperature=0.3)
    try:
        if y_col and y_col in df.columns and pd.api.types.is_numeric_dtype(df[y_col]):
            summary_df = df[[x_col, y_col]].dropna()
            data_str   = summary_df.to_string(index=False, max_rows=20)
            max_row    = summary_df.loc[summary_df[y_col].idxmax()]
            min_row    = summary_df.loc[summary_df[y_col].idxmin()]
            stats      = (f"Highest: {max_row[x_col]} ({max_row[y_col]:,}) | "
                          f"Lowest: {min_row[x_col]} ({min_row[y_col]:,})")
        else:
            counts         = df[x_col].value_counts().reset_index()
            counts.columns = [x_col, "count"]
            data_str       = counts.to_string(index=False, max_rows=20)
            stats          = f"Most common: {counts.iloc[0, 0]} ({counts.iloc[0, 1]:,})"
    except Exception:
        data_str = df.head(10).to_string(index=False)
        stats    = ""

    prompt = f"""You are a data analyst. Write a short 3-4 sentence summary of this chart.

Chart type: {chart_type}
Chart title: {title}
Data:
{data_str}
Key stats: {stats}

Write a clear, professional insight summary. Mention the highest value, lowest value,
and any notable patterns. Keep it concise and factual."""

    try:
        return llm.invoke(prompt)
    except Exception:
        return ""