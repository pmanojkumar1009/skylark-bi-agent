import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from typing import Dict, Any, List

# Enterprise Color Palette
COLOR_WON = "#10B981"      # Emerald green
COLOR_OPEN = "#3B82F6"     # Slate blue
COLOR_DEAD = "#EF4444"     # Soft red
COLOR_HOLD = "#F59E0B"     # Amber yellow
COLOR_MISSING = "#9CA3AF"  # Cool gray

STATUS_COLORS_MAP = {
    "Won": COLOR_WON,
    "Open": COLOR_OPEN,
    "Dead": COLOR_DEAD,
    "On Hold": COLOR_HOLD,
    "Unknown / Missing": COLOR_MISSING
}


def _format_inr_short(val) -> str:
    """Format numeric values as Indian rupees (Cr, L) for axes and tooltips."""
    try:
        v = float(val)
        if abs(v) >= 1_00_00_000:
            return f"₹{v / 1_00_00_000:.2f}Cr"
        elif abs(v) >= 1_00_000:
            return f"₹{v / 1_00_000:.1f}L"
        elif abs(v) >= 1_000:
            return f"₹{v:,.0f}"
        else:
            return f"₹{v:.2f}"
    except Exception:
        return str(val)


def _apply_inr_axis_formatting(fig: go.Figure, values: List[float], is_y_axis: bool = True):
    """Dynamically applies clean Indian Rupee tick intervals to axes."""
    try:
        clean_vals = [float(v) for v in values if pd.notna(v)]
        if not clean_vals or max(clean_vals) <= 0:
            return
        max_val = max(clean_vals)
        ticks = [i * (max_val / 4) for i in range(5)]
        tick_labels = [_format_inr_short(t) for t in ticks]
        
        if is_y_axis:
            fig.update_layout(yaxis=dict(tickmode="array", tickvals=ticks, ticktext=tick_labels))
        else:
            fig.update_layout(xaxis=dict(tickmode="array", tickvals=ticks, ticktext=tick_labels))
    except Exception:
        pass


def _apply_plotly_theme(fig: go.Figure, title: str = ""):
    """Helper to apply a clean modern enterprise BI theme to a figure."""
    fig.update_layout(
        title={
            "text": title,
            "y": 0.95,
            "x": 0.5,
            "xanchor": "center",
            "yanchor": "top",
            "font": {"size": 13, "family": "Inter, sans-serif", "color": "#FFFFFF", "weight": "bold"}
        },
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=40, r=30, t=50, b=45),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.3,
            xanchor="center",
            x=0.5,
            font=dict(size=9, color="#94A3B8")
        ),
        font=dict(family="Inter, sans-serif", size=10, color="#94A3B8")
    )
    fig.update_xaxes(
        gridcolor="#1B2840",
        zerolinecolor="#1B2840",
        tickfont=dict(size=9, color="#94A3B8")
    )
    fig.update_yaxes(
        gridcolor="#1B2840",
        zerolinecolor="#1B2840",
        tickfont=dict(size=9, color="#94A3B8")
    )


def apply_plotly_theme(fig: go.Figure, title: str = ""):
    """Public helper to apply the dashboard Plotly styling to any figure."""
    return _apply_plotly_theme(fig, title)


# ============================================================
# SALES / PIPELINE CHARTS
# ============================================================

def plot_pipeline_by_status(deals_df: pd.DataFrame, use_value: bool = True) -> go.Figure:
    """Renders a donut chart showing Deal Status distribution by value or count."""
    df = deals_df.copy()
    if df.empty:
        return go.Figure()
        
    df["status_clean"] = df["deal_status"].fillna("Unknown / Missing").apply(lambda x: str(x).title())
    df["deal_value_clean"] = df["deal_value"].fillna(0.0)
    
    # Filter out header row
    df = df[df["status_clean"] != "Deal Status"]
    
    if use_value:
        agg = df.groupby("status_clean")["deal_value_clean"].sum().reset_index()
        values_col = "deal_value_clean"
        title_text = "Portfolio Contract Value by Status"
    else:
        agg = df.groupby("status_clean").size().reset_index(name="count")
        values_col = "count"
        title_text = "Deal Count by Status"
        
    colors = [STATUS_COLORS_MAP.get(st, COLOR_MISSING) for st in agg["status_clean"]]
    
    # Custom hover text
    hover_labels = [_format_inr_short(v) if use_value else f"{int(v)} deals" for v in agg[values_col]]
    
    fig = go.Figure(data=[go.Pie(
        labels=agg["status_clean"],
        values=agg[values_col],
        hole=0.45,
        marker=dict(colors=colors),
        textinfo="percent",
        customdata=hover_labels,
        hovertemplate="<b>%{label}</b><br>Value: %{customdata}<br>Share: %{percent}<extra></extra>"
    )])
    
    _apply_plotly_theme(fig, title_text)
    return fig


def plot_pipeline_by_sector(deals_df: pd.DataFrame) -> go.Figure:
    """Renders a vertical bar chart of total deal portfolio value by sector."""
    from app.analytics import normalize_sector, clean_deals_df
    
    df = clean_deals_df(deals_df)
    if df.empty:
        return go.Figure()
        
    df["normalized_sector"] = df["sector_service"].apply(normalize_sector)
    df["deal_value_clean"] = df["deal_value"].fillna(0.0)
    
    agg = df.groupby("normalized_sector")["deal_value_clean"].sum().reset_index()
    agg = agg.sort_values(by="deal_value_clean", ascending=False)
    
    formatted_vals = [_format_inr_short(v) for v in agg["deal_value_clean"]]
    
    fig = px.bar(
        agg,
        x="normalized_sector",
        y="deal_value_clean",
        labels={"normalized_sector": "Sector / Service", "deal_value_clean": "Portfolio Value"},
        color_discrete_sequence=["#3B82F6"]
    )
    fig.update_traces(
        customdata=formatted_vals,
        hovertemplate="<b>%{x}</b><br>Value: %{customdata}<extra></extra>"
    )
    
    _apply_plotly_theme(fig, "Portfolio Value by Sector")
    _apply_inr_axis_formatting(fig, agg["deal_value_clean"].tolist(), is_y_axis=True)
    return fig


def plot_pipeline_by_stage(deals_df: pd.DataFrame) -> go.Figure:
    """Renders a horizontal bar chart of pipeline value by stage."""
    from app.analytics import clean_deals_df, normalize_text
    
    df = clean_deals_df(deals_df)
    if df.empty:
        return go.Figure()
        
    df["stage_clean"] = df["deal_stage"].apply(lambda x: normalize_text(x) or "Unknown / Missing")
    df["deal_value_clean"] = df["deal_value"].fillna(0.0)
    
    agg = df.groupby("stage_clean")["deal_value_clean"].sum().reset_index()
    agg = agg.sort_values(by="deal_value_clean", ascending=True)
    
    formatted_vals = [_format_inr_short(v) for v in agg["deal_value_clean"]]
    
    fig = px.bar(
        agg,
        y="stage_clean",
        x="deal_value_clean",
        orientation="h",
        labels={"stage_clean": "Deal Stage", "deal_value_clean": "Pipeline Value"},
        color_discrete_sequence=["#64748B"]
    )
    fig.update_traces(
        customdata=formatted_vals,
        hovertemplate="<b>%{y}</b><br>Pipeline: %{customdata}<extra></extra>"
    )
    
    _apply_plotly_theme(fig, "Portfolio Value by Deal Stage")
    _apply_inr_axis_formatting(fig, agg["deal_value_clean"].tolist(), is_y_axis=False)
    return fig


def plot_weighted_pipeline_by_sector(deals_df: pd.DataFrame) -> go.Figure:
    """Renders a side-by-side bar chart showing Open vs. Weighted Pipeline by Sector."""
    from app.analytics import clean_deals_df, normalize_sector, CLOSURE_PROBABILITY_MAPPING
    
    df = clean_deals_df(deals_df)
    if df.empty:
        return go.Figure()
        
    df["normalized_sector"] = df["sector_service"].apply(normalize_sector)
    df["deal_value_clean"] = df["deal_value"].fillna(0.0)
    
    status_lower = df["deal_status"].fillna("").str.lower()
    df["is_open"] = status_lower.isin(["open", "open deal"]) | df["deal_status"].isna()
    df["is_hold"] = status_lower == "on hold"
    df["is_active"] = df["is_open"] | df["is_hold"]
    
    df["prob_num"] = df["closure_probability"].fillna("").str.lower().apply(
        lambda x: CLOSURE_PROBABILITY_MAPPING.get(x, 0.0)
    )
    df["open_pipeline"] = df["deal_value_clean"].where(df["is_active"], 0.0)
    df["weighted_pipeline"] = df["open_pipeline"] * df["prob_num"]
    
    agg = df.groupby("normalized_sector").agg(
        open_pipeline=("open_pipeline", "sum"),
        weighted_pipeline=("weighted_pipeline", "sum")
    ).reset_index()
    
    agg = agg.sort_values(by="open_pipeline", ascending=False)
    
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=agg["normalized_sector"],
        y=agg["open_pipeline"],
        name="Active Open Pipeline",
        marker_color="#3B82F6",
        customdata=[_format_inr_short(v) for v in agg["open_pipeline"]],
        hovertemplate="<b>%{x}</b><br>Open Pipeline: %{customdata}<extra></extra>"
    ))
    fig.add_trace(go.Bar(
        x=agg["normalized_sector"],
        y=agg["weighted_pipeline"],
        name="Weighted Pipeline (Est.)",
        marker_color="#10B981",
        customdata=[_format_inr_short(v) for v in agg["weighted_pipeline"]],
        hovertemplate="<b>%{x}</b><br>Weighted Pipeline: %{customdata}<extra></extra>"
    ))
    
    fig.update_layout(barmode="group")
    _apply_plotly_theme(fig, "Open vs. Weighted Pipeline by Sector")
    _apply_inr_axis_formatting(fig, agg["open_pipeline"].tolist(), is_y_axis=True)
    return fig


def plot_deal_value_distribution(deals_df: pd.DataFrame) -> go.Figure:
    """Renders a histogram of deal values to show typical deal sizes."""
    from app.analytics import clean_deals_df
    df = clean_deals_df(deals_df)
    if df.empty:
        return go.Figure()
    
    valid_deals = df[df["deal_value"].notna() & (df["deal_value"] > 0)].copy()
    
    # Custom hover labels
    formatted_vals = [_format_inr_short(v) for v in valid_deals["deal_value"]]
    
    fig = px.histogram(
        valid_deals,
        x="deal_value",
        nbins=20,
        labels={"deal_value": "Deal Value"},
        color_discrete_sequence=["#8B5CF6"]
    )
    fig.update_layout(yaxis_title="Count of Deals")
    fig.update_traces(
        hovertemplate="Value Range: %{x}<br>Deals: %{y}<extra></extra>"
    )
    
    _apply_plotly_theme(fig, "Distribution of Deal Values")
    _apply_inr_axis_formatting(fig, valid_deals["deal_value"].tolist(), is_y_axis=False)
    return fig


# ============================================================
# OPERATIONS / WORK ORDER CHARTS
# ============================================================

def plot_wo_by_sector(work_orders_df: pd.DataFrame) -> go.Figure:
    """Renders a vertical bar chart of work order count by sector."""
    from app.analytics import clean_work_orders_df, normalize_sector
    
    df = clean_work_orders_df(work_orders_df)
    if df.empty:
        return go.Figure()
        
    df["normalized_sector"] = df["sector"].apply(normalize_sector)
    
    agg = df.groupby("normalized_sector").size().reset_index(name="count")
    agg = agg.sort_values(by="count", ascending=False)
    
    fig = px.bar(
        agg,
        x="normalized_sector",
        y="count",
        labels={"normalized_sector": "Sector", "count": "Work Order Count"},
        color_discrete_sequence=["#10B981"]
    )
    fig.update_traces(
        hovertemplate="<b>%{x}</b><br>Work Orders: %{y}<extra></extra>"
    )
    
    _apply_plotly_theme(fig, "Work Orders Volume by Sector")
    return fig


def plot_wo_execution_status(work_orders_df: pd.DataFrame) -> go.Figure:
    """Renders a donut chart of work order execution status."""
    from app.analytics import clean_work_orders_df, normalize_text
    
    df = clean_work_orders_df(work_orders_df)
    if df.empty:
        return go.Figure()
        
    df["status_clean"] = df["execution_status"].apply(lambda x: normalize_text(x) or "Unknown / Missing")
    
    agg = df.groupby("status_clean").size().reset_index(name="count")
    
    fig = go.Figure(data=[go.Pie(
        labels=agg["status_clean"],
        values=agg["count"],
        hole=0.45,
        textinfo="percent",
        hovertemplate="<b>%{label}</b><br>Work Orders: %{value}<br>Share: %{percent}<extra></extra>"
    )])
    
    _apply_plotly_theme(fig, "Work Order Execution Status Distribution")
    return fig


def plot_wo_value_by_sector(work_orders_df: pd.DataFrame) -> go.Figure:
    """Renders a vertical bar chart of total contract value by sector."""
    from app.analytics import clean_work_orders_df, normalize_sector
    
    df = clean_work_orders_df(work_orders_df)
    if df.empty:
        return go.Figure()
        
    df["normalized_sector"] = df["sector"].apply(normalize_sector)
    df["amount_excl_gst"] = df["amount_excl_gst"].fillna(0.0)
    
    agg = df.groupby("normalized_sector")["amount_excl_gst"].sum().reset_index()
    agg = agg.sort_values(by="amount_excl_gst", ascending=False)
    
    formatted_vals = [_format_inr_short(v) for v in agg["amount_excl_gst"]]
    
    fig = px.bar(
        agg,
        x="normalized_sector",
        y="amount_excl_gst",
        labels={"normalized_sector": "Sector", "amount_excl_gst": "Contract Value"},
        color_discrete_sequence=["#F59E0B"]
    )
    fig.update_traces(
        customdata=formatted_vals,
        hovertemplate="<b>%{x}</b><br>Value: %{customdata}<extra></extra>"
    )
    
    _apply_plotly_theme(fig, "Contract Order Value by Sector")
    _apply_inr_axis_formatting(fig, agg["amount_excl_gst"].tolist(), is_y_axis=True)
    return fig


def plot_wo_billing_status(work_orders_df: pd.DataFrame) -> go.Figure:
    """Renders a bar chart of billing status count."""
    from app.analytics import clean_work_orders_df, normalize_text
    
    df = clean_work_orders_df(work_orders_df)
    if df.empty:
        return go.Figure()
        
    df["billing_status_clean"] = df["billing_status"].apply(lambda x: normalize_text(x) or "Unknown / Missing")
    
    agg = df.groupby("billing_status_clean").size().reset_index(name="count")
    agg = agg.sort_values(by="count", ascending=False)
    
    fig = px.bar(
        agg,
        x="billing_status_clean",
        y="count",
        labels={"billing_status_clean": "Billing Status", "count": "Count"},
        color_discrete_sequence=["#6B7280"]
    )
    fig.update_traces(
        hovertemplate="<b>%{x}</b><br>Work Orders: %{y}<extra></extra>"
    )
    
    _apply_plotly_theme(fig, "Billing Status Distribution")
    return fig


# ============================================================
# FINANCE / RECEIVABLES CHARTS
# ============================================================

def plot_receivables_by_sector(work_orders_df: pd.DataFrame) -> go.Figure:
    """Renders a horizontal bar chart of outstanding receivables by sector."""
    from app.analytics import clean_work_orders_df, normalize_sector
    
    df = clean_work_orders_df(work_orders_df)
    if df.empty:
        return go.Figure()
        
    df["normalized_sector"] = df["sector"].apply(normalize_sector)
    df["receivables"] = df["amount_receivable"].fillna(0.0)
    
    agg = df.groupby("normalized_sector")["receivables"].sum().reset_index()
    agg = agg.sort_values(by="receivables", ascending=True)
    
    formatted_vals = [_format_inr_short(v) for v in agg["receivables"]]
    
    fig = px.bar(
        agg,
        y="normalized_sector",
        x="receivables",
        orientation="h",
        labels={"normalized_sector": "Sector", "receivables": "Receivables"},
        color_discrete_sequence=["#EF4444"]
    )
    fig.update_traces(
        customdata=formatted_vals,
        hovertemplate="<b>%{y}</b><br>Outstanding: %{customdata}<extra></extra>"
    )
    
    _apply_plotly_theme(fig, "Outstanding Receivables by Sector")
    _apply_inr_axis_formatting(fig, agg["receivables"].tolist(), is_y_axis=False)
    return fig


def plot_billing_waterfall(work_orders_df: pd.DataFrame) -> go.Figure:
    """Renders a waterfall chart showing total contract progression to invoiced/uninvoiced."""
    from app.analytics import get_billing_summary
    billing = get_billing_summary(work_orders_df)
    
    cv = billing.get("total_order_value_excl_gst", 0.0)
    bv = billing.get("total_billed_value_excl_gst", 0.0)
    tb = billing.get("total_amount_to_bill_excl_gst", 0.0)
    
    fig = go.Figure(go.Waterfall(
        orientation="v",
        measure=["absolute", "relative", "total"],
        x=["Total Contract Value", "Invoiced Billed Value", "Uninvoiced Backlog"],
        textposition="outside",
        text=[_format_inr_short(cv), "-" + _format_inr_short(bv), _format_inr_short(tb)],
        y=[cv, -bv, tb],
        connector={"line": {"color": "rgba(255,255,255,0.15)"}},
        decreasing={"marker": {"color": "#EF4444"}},
        increasing={"marker": {"color": "#3B82F6"}},
        totals={"marker": {"color": "#10B981"}}
    ))
    
    _apply_plotly_theme(fig, "CFO Billing Progression Waterfall (Excl. GST)")
    return fig
