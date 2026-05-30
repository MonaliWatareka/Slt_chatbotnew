import json
import re
import pandas as pd
import plotly.express as px
from langchain_ollama import OllamaLLM
from analysis.excel_reader import get_column_summary

def build_chart(user_request: str, df: pd.DataFrame, model: str = "llama3.2"):
    df = df.copy()
    df["Count"] = 1

    if any(w in user_request.lower() for w in ["correlation", "heatmap", "corr"]):
        return _build_correlation_heatmap(df)

    if "distribution" in user_request.lower():
        return _build_distribution(df, user_request)

    col_summary = get_column_summary(df)
    spec        = _ask_llm_for_chart_spec(user_request, col_summary, model)

    if spec is None:
        return "⚠️ Could not understand. Try: 'Bar chart of Churn by Contract'", None

    chart_type = spec.get("chart_type", "bar").lower()
    x_col      = _resolve_column(spec.get("x_col", ""), user_request, df)
    y_col      = _resolve_column(spec.get("y_col", ""), user_request, df, exclude=x_col)
    title      = spec.get("title") or user_request

    if chart_type == "pie":
        if not x_col or x_col not in df.columns:
            x_col = _fallback_column(df, "text")
        if y_col and y_col in df.columns and pd.api.types.is_numeric_dtype(df[y_col]):
            fig = px.pie(df, names=x_col, values=y_col, title=title,
                         template="plotly_white", hole=0.35)
        else:
            counts = df[x_col].value_counts().reset_index()
            counts.columns = [x_col, "Count"]
            fig = px.pie(counts, names=x_col, values="Count", title=title,
                         template="plotly_white", hole=0.35)
        fig.update_traces(textposition="inside", textinfo="percent+label")
        _style(fig, title)
        summary = _generate_pie_summary(df, x_col, model)
        reply   = f"**Pie chart**: *{title}*"
        if summary:
            reply += f"\n\n📊 **Insight:** {summary}"
        return reply, fig

    if chart_type == "bar":
        if not x_col or x_col not in df.columns:
            x_col = _fallback_column(df, "text")
        if y_col and y_col in df.columns and df[y_col].dtype == object:
            agg = df.groupby([x_col, y_col]).size().reset_index(name="Count")
            fig = px.bar(agg, x=x_col, y="Count", color=y_col, title=title,
                         template="plotly_white", barmode="group", text_auto=True)
        elif y_col and y_col in df.columns and pd.api.types.is_numeric_dtype(df[y_col]):
            fig = px.bar(df, x=x_col, y=y_col, title=title,
                         template="plotly_white", text_auto=True)
        else:
            counts = df[x_col].value_counts().reset_index()
            counts.columns = [x_col, "Count"]
            fig = px.bar(counts, x=x_col, y="Count", title=title,
                         template="plotly_white", text_auto=True)
        fig.update_traces(textposition="outside")
        _style(fig, title, x_col, "Count")
        summary = _generate_summary(df, x_col, y_col, chart_type, title, model)
        return f"**Bar chart**: *{title}*\n\n📊 {summary}", fig

    # Line / Scatter / Area / Histogram
    if not x_col or x_col not in df.columns:
        x_col = _fallback_column(df, "text")
    if not y_col or y_col not in df.columns:
        y_col = _fallback_column(df, "number", x_col)

    fig = _build_generic(df, chart_type, x_col, y_col, title)
    summary = _generate_summary(df, x_col, y_col, chart_type, title, model)
    return f"**{chart_type} chart**: *{title}*\n\n📊 {summary}", fig

def _build_correlation_heatmap(df):
    num = df.select_dtypes(include="number")
    if num.shape[1] < 2:
        return "⚠️ Need at least 2 numeric columns for heatmap.", None
    fig = px.imshow(num.corr().round(2), text_auto=True,
                    color_continuous_scale="RdBu_r",
                    title="Correlation Heatmap", template="plotly_white")
    _style(fig, "Correlation Heatmap")
    return "**Correlation heatmap** — values near ±1 show strong relationships.", fig

def _build_distribution(df, user_request):
    numeric = df.select_dtypes(include="number").columns.tolist()
    col = next((c for c in numeric if c.lower() in user_request.lower()), None)
    col = col or (numeric[0] if numeric else None)
    if not col:
        return "⚠️ No numeric column found.", None
    fig = px.histogram(df, x=col, marginal="box", nbins=30,
                       title=f"Distribution of {col}", template="plotly_white")
    _style(fig, f"Distribution of {col}")
    return f"**Distribution of {col}** with box plot.", fig

def _style(fig, title, x="", y=""):
    fig.update_layout(
        title_font_size=18,
        margin=dict(t=60, b=40, l=40, r=40),
        xaxis_title=x, yaxis_title=y,
        font=dict(family="Arial"),
    )

def _build_generic(df, chart_type, x_col, y_col, title):
    kwargs = dict(x=x_col, y=y_col, title=title, template="plotly_white")
    if chart_type == "line":
        fig = px.line(df, **kwargs, markers=True)
    elif chart_type == "scatter":
        fig = px.scatter(df, **kwargs)
    elif chart_type == "area":
        fig = px.area(df, **kwargs)
    else:
        fig = px.histogram(df, x=x_col, title=title, template="plotly_white", nbins=30)
    _style(fig, title, x_col, y_col)
    return fig

def _resolve_column(col, message, df, exclude=""):
    if col and col in df.columns:
        return col
    msg = message.lower()
    for c in df.columns:
        if c == exclude:
            continue
        if c.lower() in msg:
            return c
    return col

def _fallback_column(df, prefer="text", exclude=""):
    cols = (df.select_dtypes(include="object" if prefer == "text" else "number")
            .columns.tolist())
    return next((c for c in cols if c != exclude), "")

def _ask_llm_for_chart_spec(user_request, col_summary, model):
    try:
        llm    = OllamaLLM(model=model, temperature=0)
        prompt = f"""Return ONLY a JSON object. No explanation.

Columns:
{col_summary}

User: "{user_request}"

Format:
{{"chart_type": "bar", "x_col": "col_name", "y_col": "col_name_or_null", "color_col": null, "title": "Chart Title"}}

chart_type options: bar, pie, line, scatter, histogram, area
Return ONLY JSON."""

        raw = llm.invoke(prompt)
        try:
            return _sanitize(json.loads(raw.strip()))
        except Exception:
            pass
        match = re.search(r'\{[^{}]+\}', raw, re.DOTALL)
        if match:
            return _sanitize(json.loads(match.group()))
    except Exception:
        pass
    return None

def _sanitize(spec):
    for k in ("color_col", "y_col"):
        if spec.get(k) in ("null", "", "none", "None", "NULL"):
            spec[k] = None
    return spec

def _generate_summary(df, x_col, y_col, chart_type, title, model):
    try:
        llm = OllamaLLM(model=model, temperature=0.3)
        if y_col and y_col in df.columns and pd.api.types.is_numeric_dtype(df[y_col]):
            data = df[[x_col, y_col]].dropna().to_string(index=False, max_rows=15)
        else:
            counts = df[x_col].value_counts().reset_index()
            counts.columns = [x_col, "count"]
            data = counts.to_string(index=False, max_rows=15)
        return llm.invoke(
            f"Write 2 sentences of insight about this {chart_type} chart titled '{title}'.\n"
            f"Data:\n{data}\nBe factual and concise."
        )
    except Exception:
        return ""

def _generate_pie_summary(df: pd.DataFrame, x_col: str, model: str = "llama3.2") -> str:
    try:
        llm            = OllamaLLM(model=model, temperature=0.3)
        counts         = df[x_col].value_counts().reset_index()
        counts.columns = [x_col, "Count"]
        total          = counts["Count"].sum()
        counts["Pct"]  = (counts["Count"] / total * 100).round(1)
        data_str       = counts.to_string(index=False)
        top            = counts.iloc[0]
        second         = counts.iloc[1] if len(counts) > 1 else None
        stats          = f"Largest: {top[x_col]} ({top['Pct']}%)"
        if second is not None:
            stats += f" | Second: {second[x_col]} ({second['Pct']}%)"

        return llm.invoke(
            f"Write 2 sentences of insight about this pie chart for column '{x_col}'.\n"
            f"Data:\n{data_str}\nStats: {stats}\nTotal: {total:,}\n"
            f"Mention the dominant category. Be factual and concise."
        )
    except Exception:
        # LLM fallback — still shows a basic summary without LLM
        try:
            counts         = df[x_col].value_counts().reset_index()
            counts.columns = [x_col, "Count"]
            total          = counts["Count"].sum()
            top            = counts.iloc[0]
            pct            = round(top["Count"] / total * 100, 1)
            return (
                f"{top[x_col]} is the largest category at {pct}% of {total:,} records. "
                f"There are {len(counts)} unique values in the {x_col} column."
            )
        except Exception:
            return ""
