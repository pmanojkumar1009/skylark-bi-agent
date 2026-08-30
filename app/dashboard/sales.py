import streamlit as st
import pandas as pd
import plotly.express as px
import datetime
from app.dashboard.components import (
    kpi_card, section_header, page_header,
    status_badge, html_table, empty_state, format_inr, format_pct,
    C_BG_SURFACE, C_BORDER, C_EMERALD, C_RED, C_AMBER, C_BLUE, C_TEXT_MUTED, C_TEXT_PRIMARY, C_TEXT_BODY
)
from app.dashboard.charts import (
    plot_pipeline_by_status,
    plot_pipeline_by_stage,
    plot_weighted_pipeline_by_sector,
    apply_plotly_theme
)
from app.analytics import (
    clean_deals_df,
    get_pipeline_summary,
    get_owner_performance,
    get_stale_deals,
    get_top_opportunities,
    normalize_sector
)


def _prob_to_float(prob) -> float:
    """Safely convert a probability value (str, int, float) to float 0-100."""
    try:
        return float(str(prob).replace("%", "").strip())
    except Exception:
        return 50.0


def render_sales_page(deals_df: pd.DataFrame, agent=None):
    """Renders Page 2: Sales & Pipeline Intelligence."""

    page_header(
        "Sales & Pipeline Intelligence",
        "Track active deals, pipeline value, close rates, owner performance, and at-risk accounts.",
        "💼"
    )

    # ── CLEAN DATA ──
    df = clean_deals_df(deals_df).copy()
    df["normalized_sector"]   = df["sector_service"].apply(normalize_sector)
    df["stage_clean"]         = df["deal_stage"].fillna("Unknown / Missing")
    df["deal_value_clean"]    = df["deal_value"].fillna(0.0)

    # ── FILTERS ──
    with st.expander("Filters", expanded=True):
        f1, f2 = st.columns(2)
        with f1:
            sectors = sorted(df["normalized_sector"].unique())
            sel_sectors = st.multiselect("Sector", sectors, default=sectors, key="sales_sec")
        with f2:
            stages = sorted(df["stage_clean"].unique())
            sel_stages = st.multiselect("Deal Stage", stages, default=stages, key="sales_stg")

    filtered = df[df["normalized_sector"].isin(sel_sectors) & df["stage_clean"].isin(sel_stages)]
    if filtered.empty:
        empty_state("No deals match the selected filters.", "🔍", "Try adjusting sector or stage filters.")
        return

    # ── KPIs ──
    kpis = get_pipeline_summary(filtered)
    total_deals   = kpis.get("total_deals", 0)
    total_val     = kpis.get("total_portfolio_value", 0.0)
    open_val      = kpis.get("open_pipeline_value", 0.0)
    weighted_val  = kpis.get("weighted_pipeline_value", 0.0)
    won_val       = kpis.get("won_deals_value", 0.0)
    dead_val      = kpis.get("dead_deals_value", 0.0)
    open_count    = kpis.get("open_deals_count", 0)
    won_count     = kpis.get("won_deals_count", 0)
    closed_total  = won_val + dead_val
    win_rate      = (won_val / closed_total * 100) if closed_total > 0 else 0.0
    avg_prob      = kpis.get("avg_closure_probability", 0.0) * 100

    # Row 1 — 5 KPIs
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        kpi_card("Total Deals", total_deals, f"{open_count} open · {won_count} won")
    with c2:
        kpi_card("Total Portfolio", format_inr(total_val), "All deal values")
    with c3:
        kpi_card("Open Pipeline", format_inr(open_val), "Active open deals", is_positive=open_val > 0)
    with c4:
        kpi_card("Weighted Est.", format_inr(weighted_val), "Probability-adjusted", is_warning=True)
    with c5:
        kpi_card("Won Revenue", format_inr(won_val), "Closed Won total", is_positive=True)

    st.markdown("<div style='margin-top:6px;'></div>", unsafe_allow_html=True)

    # Row 2 — 3 KPIs
    c6, c7, c8 = st.columns(3)
    with c6:
        kpi_card(
            "Win Rate", format_pct(win_rate), "Won / (Won + Dead)",
            is_positive=win_rate >= 50,
            is_warning=0 < win_rate < 50,
            is_risk=win_rate == 0 and closed_total > 0
        )
    with c7:
        kpi_card(
            "Avg. Closure Prob.", format_pct(avg_prob),
            "Active deals with probability",
            is_positive=avg_prob >= 60,
            is_warning=avg_prob < 60
        )
    with c8:
        kpi_card("Lost Value", format_inr(dead_val), "Dead/lost deals")

    st.markdown("<div style='margin-top:8px;'></div>", unsafe_allow_html=True)

    # ── CHARTS ──
    section_header("Pipeline Analytics", "Distribution of deals by status, stage, and sector weighting.")
    left, right = st.columns(2)
    with left:
        st.plotly_chart(plot_pipeline_by_status(filtered), use_container_width=True)
        st.plotly_chart(plot_pipeline_by_stage(filtered), use_container_width=True)
    with right:
        # Funnel chart
        df_f = filtered.groupby("stage_clean")["deal_value_clean"].sum().reset_index()
        df_f = df_f.sort_values("deal_value_clean", ascending=False)
        if not df_f.empty:
            fig_f = px.funnel(
                df_f, y="stage_clean", x="deal_value_clean",
                labels={"stage_clean": "Stage", "deal_value_clean": "Value (₹)"}
            )
            apply_plotly_theme(fig_f, "Pipeline Funnel by Stage Value")
            st.plotly_chart(fig_f, use_container_width=True)

        st.plotly_chart(plot_weighted_pipeline_by_sector(filtered), use_container_width=True)

        # Owner performance bar
        owner_perf = get_owner_performance(filtered)
        if owner_perf:
            odf = pd.DataFrame(owner_perf)
            fig_o = px.bar(
                odf, x="owner", y="open_value",
                labels={"owner": "Sales Owner", "open_value": "Open Pipeline (₹)"},
                color_discrete_sequence=[C_BLUE]
            )
            apply_plotly_theme(fig_o, "Active Open Pipeline by Owner")
            st.plotly_chart(fig_o, use_container_width=True)

    st.markdown("<hr style='border-color:#1B2840; margin:20px 0;'>", unsafe_allow_html=True)

    # ── TOP OPPORTUNITIES TABLE ──
    section_header("Top Open Opportunities", "Highest-value open deals awaiting closure — ranked by pipeline value.")
    top_opps = get_top_opportunities(filtered, limit=10)
    if top_opps:
        rows = []
        for opp in top_opps:
            prob_val = _prob_to_float(opp.get("probability", 50))
            prob_sev = "success" if prob_val >= 75 else ("warning" if prob_val >= 40 else "critical")
            stage_val = str(opp.get("stage", ""))
            stage_sev = "success" if "proposal" in stage_val.lower() or "close" in stage_val.lower() else "info"
            rows.append({
                "Deal":        f"<span style='color:{C_TEXT_PRIMARY}; font-weight:600;'>{opp.get('name', '')}</span>",
                "Value":       f"<span style='color:{C_EMERALD}; font-weight:700;'>{format_inr(opp.get('value', 0))}</span>",
                "Stage":       f"<span style='color:#CBD5E1;'>{stage_val}</span>",
                "Sector":      f"<span style='color:{C_TEXT_MUTED};'>{opp.get('sector', '')}</span>",
                "Probability": status_badge(str(opp.get("probability", "")), prob_sev),
                "Owner":       f"<span style='color:#CBD5E1;'>{opp.get('owner', '')}</span>",
            })
        st.markdown(
            html_table(rows, ["Deal", "Value", "Stage", "Sector", "Probability", "Owner"]),
            unsafe_allow_html=True
        )
    else:
        empty_state("No open opportunities found in the current filter scope.", "💼")

    st.markdown("<div style='margin-top:20px;'></div>", unsafe_allow_html=True)

    # ── STALE / AT-RISK DEALS ──
    section_header("Stale & At-Risk Deals", "Deals with prolonged inactivity, missing probability, or low closure likelihood.")
    stale = get_stale_deals(filtered, reference_date=datetime.date.today())
    if stale:
        rows = []
        for sd in stale:
            prob_val = _prob_to_float(sd.get("probability", 50))
            prob_sev = "success" if prob_val >= 75 else ("warning" if prob_val >= 40 else "critical")
            risk_text = ", ".join(sd.get("reasons", []))
            rows.append({
                "Deal":   f"<span style='color:{C_TEXT_PRIMARY}; font-weight:600;'>{sd.get('name', '')}</span>",
                "Value":  f"<span style='color:{C_RED}; font-weight:700;'>{format_inr(sd.get('value', 0))}</span>",
                "Stage":  f"<span style='color:#CBD5E1;'>{sd.get('stage', '')}</span>",
                "Sector": f"<span style='color:{C_TEXT_MUTED};'>{sd.get('sector', '')}</span>",
                "Prob.":  status_badge(str(sd.get("probability", "")), prob_sev),
                "Owner":  f"<span style='color:#CBD5E1;'>{sd.get('owner', '')}</span>",
                "Risk":   status_badge(risk_text[:35] + "…" if len(risk_text) > 35 else risk_text, "critical"),
            })
        st.markdown(
            html_table(rows, ["Deal", "Value", "Stage", "Sector", "Prob.", "Owner", "Risk"]),
            unsafe_allow_html=True
        )
    else:
        st.success("✅ No stale or at-risk deals detected within the current filter parameters.")

    st.markdown("<hr style='border-color:#1B2840; margin:20px 0;'>", unsafe_allow_html=True)

    # ── AI PIPELINE ASSESSMENT (button-triggered only) ──
    section_header(
        "AI Pipeline Assessment",
        "On-demand AI analysis of the current sales pipeline — powered by Gemini and live data."
    )

    if agent is None:
        st.info("AI agent not available. Pass agent= to render_sales_page() to enable AI analysis.")
        return

    if st.button("🤖  Run AI Pipeline Assessment", key="ai_pipeline_btn", use_container_width=False):
        with st.spinner("Running Gemini analysis on live pipeline data…"):
            try:
                analysis = agent.ask(
                    "Give me a detailed pipeline assessment: open deals, weighted value, biggest opportunities, "
                    "at-risk deals, and your top recommendation for improving pipeline conversion."
                )
                st.markdown(analysis)
                provider = getattr(agent.llm_client, "provider", None)
                src_color = C_EMERALD if provider else C_AMBER
                src_label = f"Gemini AI ({agent.llm_client.model_name})" if provider else "Fallback Analytics"
                st.markdown(
                    f"<div style='font-size:10px; color:{C_TEXT_MUTED}; margin-top:6px; "
                    f"border-top:1px solid {C_BORDER}; padding-top:6px;'>"
                    f"<span style='color:{src_color}; font-weight:700;'>●</span> "
                    f"Source: {src_label} · Based on {len(filtered)} filtered deals"
                    f"</div>",
                    unsafe_allow_html=True
                )
            except Exception as e:
                st.error(f"AI assessment failed: {e}")
    else:
        st.markdown(
            f"<div style='font-size:12px; color:{C_TEXT_MUTED}; padding:10px 0;'>"
            f"Click the button above to trigger a Gemini-powered pipeline assessment based on your current filter selection."
            f"</div>",
            unsafe_allow_html=True
        )
