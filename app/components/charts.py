from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


COLOR_SALES = "#2563EB"
COLOR_HEALTHY = "#0F766E"
COLOR_WARNING = "#F59E0B"
COLOR_RISK = "#DC2626"
COLOR_SUCCESS = "#16A34A"
COLOR_NEUTRAL = "#64748B"
COLOR_SEQUENCE = [COLOR_SALES, COLOR_HEALTHY, COLOR_WARNING, COLOR_NEUTRAL, COLOR_SUCCESS, COLOR_RISK]
PERCENT_TERMS = ("pct", "percent", "_to_gross")
EMPTY_CHART_MESSAGE = (
    "No meaningful data available for this view. Try a larger dataset, upload transaction rows "
    "with sales activity, or review validation checks."
)


def _axis_format(column: str) -> str | None:
    return ".1f" if any(term in column for term in PERCENT_TERMS) or column.endswith("_index") else None


def _is_percent_metric(column: str) -> bool:
    return any(term in column for term in PERCENT_TERMS)


def _text_template(column: str) -> str:
    return "%{text:.1f}%" if _is_percent_metric(column) else "%{text:.1f}"


def _metric_color(column: str) -> str:
    lowered = column.lower()
    if "refund" in lowered or "negative" in lowered:
        return COLOR_RISK
    if any(term in lowered for term in ("risk", "review", "fee", "promotion")):
        return COLOR_WARNING
    if any(term in lowered for term in ("quality", "healthy", "net_to_gross", "margin_index", "profitability")):
        return COLOR_HEALTHY
    if any(term in lowered for term in ("sales", "units", "order", "index", "volume")):
        return COLOR_SALES
    return COLOR_NEUTRAL


def _category_color_map(series: pd.Series) -> dict[str, str]:
    values = series.dropna().astype(str).unique().tolist()
    color_map: dict[str, str] = {}
    for value in values:
        lowered = value.lower()
        if "high" in lowered or "fail" in lowered or "refund" in lowered:
            color_map[value] = COLOR_RISK
        elif any(term in lowered for term in ("medium", "warning", "review", "risk", "promotion", "fee")):
            color_map[value] = COLOR_WARNING
        elif any(term in lowered for term in ("pass", "low", "monitor", "healthy")):
            color_map[value] = COLOR_SUCCESS if "pass" in lowered else COLOR_NEUTRAL
        else:
            color_map[value] = COLOR_NEUTRAL
    return color_map


def has_meaningful_values(df: pd.DataFrame, value_col: str) -> bool:
    if df.empty or value_col not in df.columns:
        return False
    values = pd.to_numeric(df[value_col], errors="coerce").fillna(0.0)
    return bool((values.abs() > 0.000001).any())


def apply_chart_theme(fig: go.Figure, *, x: str | None = None, y: str | None = None, height: int = 390) -> go.Figure:
    fig.update_layout(
        height=height,
        margin=dict(l=10, r=10, t=58, b=70),
        title=dict(font=dict(size=16, color="#0f172a"), x=0.01, xanchor="left"),
        font=dict(color="#334155", size=12),
        paper_bgcolor="white",
        plot_bgcolor="white",
        legend_title="",
        hoverlabel=dict(bgcolor="white", font_size=12, font_color="#0f172a"),
    )
    fig.update_xaxes(showgrid=False, zeroline=False, title_font=dict(size=12), tickfont=dict(size=11))
    fig.update_yaxes(gridcolor="#e2e8f0", zeroline=False, title_font=dict(size=12), tickfont=dict(size=11))
    if x and _axis_format(x):
        fig.update_xaxes(tickformat=_axis_format(x))
        if _is_percent_metric(x):
            fig.update_xaxes(ticksuffix="%")
    if y and _axis_format(y):
        fig.update_yaxes(tickformat=_axis_format(y))
        if _is_percent_metric(y):
            fig.update_yaxes(ticksuffix="%")
    return fig


def empty_figure(message: str = EMPTY_CHART_MESSAGE) -> go.Figure:
    fig = go.Figure()
    fig.add_annotation(
        text=message,
        showarrow=False,
        x=0.5,
        y=0.5,
        xref="paper",
        yref="paper",
        align="center",
        font=dict(color="#64748b", size=13),
    )
    return apply_chart_theme(fig, height=340)


def grouped_metric(df: pd.DataFrame, group_col: str, value_col: str, top_n: int = 15, agg: str = "mean") -> pd.DataFrame:
    if df.empty or group_col not in df.columns or value_col not in df.columns:
        return pd.DataFrame(columns=[group_col, value_col])
    grouped = (
        df.assign(**{value_col: pd.to_numeric(df[value_col], errors="coerce").fillna(0.0)})
        .groupby(group_col, dropna=False)[value_col]
        .agg(agg)
        .reset_index()
        .sort_values(value_col, ascending=False)
        .head(top_n)
    )
    return grouped


def bar_chart(
    df: pd.DataFrame,
    x: str,
    y: str,
    title: str,
    *,
    top_n: int = 15,
    agg: str | None = None,
    y_title: str | None = None,
) -> go.Figure:
    chart_df = grouped_metric(df, x, y, top_n, agg) if agg else df[[x, y]].dropna().sort_values(y, ascending=False).head(top_n)
    if chart_df.empty or not has_meaningful_values(chart_df, y):
        return empty_figure()
    labels = chart_df[x].astype(str)
    use_horizontal = x.endswith("_group") or x in {"product_group", "brand_group", "category_group", "subcategory_group"} or labels.str.len().mean() > 16
    if use_horizontal:
        plot_df = chart_df.sort_values(y, ascending=True)
        fig = px.bar(
            plot_df,
            x=y,
            y=x,
            orientation="h",
            title=title,
            color_discrete_sequence=[_metric_color(y)],
            text=y,
        )
        fig.update_traces(texttemplate=_text_template(y), textposition="outside", cliponaxis=False)
        fig.update_layout(xaxis_title=y_title or y.replace("_", " ").title(), yaxis_title="")
        return apply_chart_theme(fig, x=y, y=x, height=400)
    fig = px.bar(chart_df, x=x, y=y, title=title, color_discrete_sequence=[_metric_color(y)], text=y)
    fig.update_traces(texttemplate=_text_template(y), textposition="outside", cliponaxis=False)
    fig.update_layout(xaxis_title="", yaxis_title=y_title or y.replace("_", " ").title())
    fig.update_xaxes(tickangle=-20)
    return apply_chart_theme(fig, x=x, y=y, height=360)


def horizontal_bar_chart(df: pd.DataFrame, x: str, y: str, title: str, top_n: int = 15) -> go.Figure:
    if df.empty or x not in df.columns or y not in df.columns or not has_meaningful_values(df, x):
        return empty_figure()
    chart_df = df[[x, y]].dropna().assign(**{x: pd.to_numeric(df[x], errors="coerce").fillna(0.0)}).sort_values(x, ascending=True).tail(top_n)
    fig = px.bar(chart_df, x=x, y=y, orientation="h", title=title, color_discrete_sequence=[_metric_color(x)], text=x)
    fig.update_traces(texttemplate=_text_template(x), textposition="outside", cliponaxis=False)
    fig.update_layout(xaxis_title=x.replace("_", " ").title(), yaxis_title="")
    return apply_chart_theme(fig, x=x, y=y, height=400)


def horizontal_bar(df: pd.DataFrame, x: str, y: str, title: str, top_n: int = 15) -> go.Figure:
    return horizontal_bar_chart(df, x, y, title, top_n)


def donut_chart(df: pd.DataFrame, names: str, values: str, title: str) -> go.Figure:
    if df.empty or names not in df.columns or values not in df.columns or not has_meaningful_values(df, values):
        return empty_figure()
    fig = px.pie(
        df,
        names=names,
        values=values,
        title=title,
        hole=0.48,
        color_discrete_sequence=COLOR_SEQUENCE,
        color=names,
        color_discrete_map=_category_color_map(df[names]),
    )
    fig.update_traces(textposition="inside", textinfo="percent+label")
    return apply_chart_theme(fig)


def scatter_chart(
    df: pd.DataFrame,
    x: str,
    y: str,
    title: str,
    *,
    color: str | None = None,
    hover_name: str | None = None,
) -> go.Figure:
    if df.empty or x not in df.columns or y not in df.columns:
        return empty_figure()
    fig = px.scatter(
        df,
        x=x,
        y=y,
        color=color if color in df.columns else None,
        hover_name=hover_name if hover_name in df.columns else None,
        title=title,
        color_discrete_sequence=COLOR_SEQUENCE,
    )
    fig.update_traces(marker=dict(size=9, opacity=0.82, line=dict(width=0.8, color="white")))
    fig.update_layout(
        xaxis_title=x.replace("_", " ").title(),
        yaxis_title=y.replace("_", " ").title(),
    )
    if not has_meaningful_values(df, x) and not has_meaningful_values(df, y):
        return empty_figure()
    return apply_chart_theme(fig, x=x, y=y, height=400)


def line_chart(df: pd.DataFrame, x: str, y: str, title: str, *, color: str | None = None) -> go.Figure:
    if df.empty or x not in df.columns or y not in df.columns:
        return empty_figure()
    chart_df = df[[col for col in [x, y, color] if col and col in df.columns]].dropna()
    if chart_df.empty or not has_meaningful_values(chart_df, y):
        return empty_figure()
    if chart_df[x].nunique(dropna=True) <= 1 and color and color in chart_df.columns:
        single_period = (
            chart_df.groupby(color, dropna=False)[y]
            .mean()
            .reset_index()
            .sort_values(y, ascending=False)
            .head(15)
        )
        return bar_chart(single_period, color, y, title.replace("Trend", "by Marketplace"), top_n=15)
    fig = px.line(
        chart_df.sort_values(x),
        x=x,
        y=y,
        color=color if color in chart_df.columns else None,
        title=title,
        markers=True,
        color_discrete_sequence=COLOR_SEQUENCE,
    )
    fig.update_traces(line=dict(width=2.8), marker=dict(size=7))
    fig.update_layout(xaxis_title="", yaxis_title=y.replace("_", " ").title())
    return apply_chart_theme(fig, x=x, y=y, height=360)
