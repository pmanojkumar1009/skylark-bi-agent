import streamlit as st
import pandas as pd
from app.dashboard.components import (
    kpi_card, section_header, page_header,
    insight_card, priority_card, status_badge,
    html_table, ai_briefing_card, empty_state, format_inr, format_pct,
    C_BG_BASE, C_BG_SURFACE, C_BG_RAISED, C_BORDER, C_BORDER_MUTED,
    C_BLUE, C_CYAN, C_EMERALD, C_AMBER, C_RED,
    C_TEXT_PRIMARY, C_TEXT_BODY, C_TEXT_MUTED
)
from app.dashboard.charts import (
    plot_pipeline_by_status,
    plot_pipeline_by_stage,
    plot_wo_execution_status,
    plot_wo_by_sector,
    plot_wo_billing_status,
    plot_receivables_by_sector
)
from app.analytics import (
    get_leadership_summary,
    get_business_health_summary,
    get_deterministic_insights,
    get_sector_performance,
    get_executive_recommendations,
    get_pipeline_summary,
    get_billing_summary,
    get_work_order_summary,
)


def _health_bar(label: str, score: float) -> str:
    """Returns a premium horizontal health bar HTML string."""
    if score >= 75:
        color = C_EMERALD
    elif score >= 50:
        color = C_AMBER
    else:
        color = C_RED
    pct = min(max(score, 0), 100)
    return (
        f'<div style="margin-bottom: 14px;">'
        f'<div style="display:flex; justify-content:space-between; margin-bottom:5px;">'
        f'<span style="font-size:12px; color:{C_TEXT_BODY}; font-weight:500;">{label}</span>'
        f'<span style="font-size:12px; color:{color}; font-weight:700;">{score:.0f}/100</span>'
        f'</div>'
        f'<div style="background:{C_BG_BASE}; height:5px; border-radius:3px; overflow:hidden;">'
        f'<div style="background:linear-gradient(90deg, {color}88, {color}); width:{pct}%; height:100%; border-radius:3px;"></div>'
        f'</div>'
        f'</div>'
    )


def _build_executive_briefing(deals_df: pd.DataFrame, work_orders_df: pd.DataFrame) -> dict:
    """
    Build a deterministic AI Executive Briefing from live analytics data.
    No Gemini call — 100% grounded in real data, zero hallucination risk.
    """
    pipe = get_pipeline_summary(deals_df)
    billing = get_billing_summary(work_orders_df)
    ops = get_work_order_summary(work_orders_df)
    sectors = get_sector_performance(deals_df, work_orders_df)

    # Top Opportunity: sector with highest open pipeline value
    top_opp_sector = None
    top_opp_val = 0.0
    for s in sectors:
        opv = s.get("deals", {}).get("open_pipeline_value", 0.0)
        if opv > top_opp_val:
            top_opp_val = opv
            top_opp_sector = s.get("sector", "Unknown")

    # Biggest Risk: sector with highest receivables OR business with lowest billing ratio
    risk_sector = None
    risk_rv = 0.0
    for s in sectors:
        rv = s.get("work_orders", {}).get("receivables", 0.0)
        if rv > risk_rv:
            risk_rv = rv
            risk_sector = s.get("sector", "Unknown")

    # Operational Concern: stuck work orders
    stuck_count = ops.get("execution_status_distribution", {}).get("Pause / struck", {}).get("count", 0)
    total_wos = ops.get("total_work_orders", 0)
    comp_rate = (ops.get("completed_count", 0) / total_wos * 100) if total_wos > 0 else 0.0

    # Financial Concern: collection rate vs receivables
    coll_rate = billing.get("collected_percentage_of_billed", 0.0)
    total_recv = billing.get("total_receivables", 0.0)
    billed_pct = billing.get("billed_percentage_excl", 0.0)

    return {
        "top_opp_sector": top_opp_sector,
        "top_opp_val": top_opp_val,
        "risk_sector": risk_sector,
        "risk_rv": risk_rv,
        "stuck_count": stuck_count,
        "total_wos": total_wos,
        "comp_rate": comp_rate,
        "coll_rate": coll_rate,
        "total_recv": total_recv,
        "billed_pct": billed_pct,
        "open_pipeline": pipe.get("open_pipeline_value", 0.0),
        "won_value": pipe.get("won_deals_value", 0.0),
        "total_deals": pipe.get("total_deals", 0),
        "open_deals": pipe.get("open_deals_count", 0),
    }


def render_overview_page(deals_df: pd.DataFrame, work_orders_df: pd.DataFrame):
    """Renders Page 1: Executive Intelligence Overview."""

    # ── PAGE HEADER ──
    page_header(
        "Executive Intelligence",
        "Real-time business performance, risk and opportunity intelligence — powered by Monday.com",
        "📊"
    )

    # ── 1. BUSINESS HEALTH INDEX ──
    health = get_business_health_summary(deals_df, work_orders_df)
    overall_score = float(health.get("overall_score", 0))
    dims = health.get("dimensions", {})

    if overall_score >= 75:
        h_status, h_color = "HEALTHY", C_EMERALD
    elif overall_score >= 50:
        h_status, h_color = "ATTENTION REQUIRED", C_AMBER
    else:
        h_status, h_color = "CRITICAL", C_RED

    sales_score = dims.get("sales", {}).get("score", 0)
    ops_score   = dims.get("operations", {}).get("score", 0)
    fin_score   = dims.get("finance", {}).get("score", 0)
    dq_score    = dims.get("data_quality", {}).get("score", 0)

    # Overall badge background
    h_bg = ("rgba(16,185,129,0.1)" if h_color == C_EMERALD
            else ("rgba(245,158,11,0.1)" if h_color == C_AMBER else "rgba(239,68,68,0.1)"))

    bars_html = (
        _health_bar("Sales Performance", sales_score) +
        _health_bar("Operations & Delivery", ops_score) +
        _health_bar("Finance & Collections", fin_score) +
        _health_bar("Data Governance", dq_score)
    )

    health_html = (
        f'<div style="background:{C_BG_SURFACE}; border:1px solid {C_BORDER}; border-radius:10px; padding:22px 24px; margin-bottom:22px;">'
        f'<div style="font-size:9px; font-weight:700; color:{C_TEXT_MUTED}; text-transform:uppercase; letter-spacing:1.5px; margin-bottom:16px;">Business Health Index</div>'
        f'<div style="display:grid; grid-template-columns:auto 1fr; gap:30px; align-items:start;">'
        f'<div style="padding-right:30px; border-right:1px solid {C_BORDER}; min-width:150px;">'
        f'<div style="font-size:52px; font-weight:800; color:{C_TEXT_PRIMARY}; line-height:1; letter-spacing:-2px;">{overall_score:.0f}<span style="font-size:18px; color:{C_TEXT_MUTED}; font-weight:400;">/100</span></div>'
        f'<div style="margin-top:10px; display:inline-flex; align-items:center; gap:6px; background:{h_bg}; border:1px solid {h_color}40; border-radius:6px; padding:5px 12px;">'
        f'<span style="width:6px; height:6px; border-radius:50%; background:{h_color}; box-shadow:0 0 6px {h_color}; display:inline-block;"></span>'
        f'<span style="font-size:10px; font-weight:700; color:{h_color}; letter-spacing:0.5px;">{h_status}</span>'
        f'</div>'
        f'<div style="margin-top:12px; font-size:11px; color:{C_TEXT_MUTED}; line-height:1.5;">'
        f'Composite of Sales, Operations, Finance &amp; Data Governance dimensions. Scores are deterministic — based on live Monday.com data.'
        f'</div>'
        f'</div>'
        f'<div style="padding-top:4px;">{bars_html}</div>'
        f'</div>'
        f'</div>'
    )
    st.markdown(health_html, unsafe_allow_html=True)

    # ── Health Score Explainability ──
    with st.expander("Health Score — Component Breakdown", expanded=False):
        cols = st.columns(2)
        dim_map = {
            "Sales Performance": ("sales", cols[0]),
            "Operations & Delivery": ("operations", cols[1]),
            "Finance & Collections": ("finance", cols[0]),
            "Data Governance": ("data_quality", cols[1]),
        }
        for name, (key, col) in dim_map.items():
            with col:
                d = dims.get(key, {})
                score_val = d.get("score", 0)
                score_color = C_EMERALD if score_val >= 75 else (C_AMBER if score_val >= 50 else C_RED)
                st.markdown(
                    f"<div style='font-size:13px; font-weight:700; color:{C_TEXT_PRIMARY}; margin-bottom:6px;'>"
                    f"{name} — <span style='color:{score_color};'>{score_val:.0f}/100</span></div>",
                    unsafe_allow_html=True
                )
                for f in d.get("factors", []):
                    icon = "🟢" if f.get("impact") == "+" else "🔴"
                    st.markdown(f"- {icon} **{f['factor']}**: `{f['value']}`")

    # ── 2. EXECUTIVE SNAPSHOT KPIs ──
    section_header("Executive Snapshot", "Key performance indicators across pipeline, operations and finance.")

    lead_sum = get_leadership_summary(deals_df, work_orders_df)
    pipe_kpis = lead_sum.get("pipeline_kpis", {})
    ops_kpis  = lead_sum.get("operations_kpis", {})
    bill_kpis = lead_sum.get("billing_kpis", {})

    comp_rate = ops_kpis.get("completion_rate_percentage", 0.0)
    coll_rate = bill_kpis.get("collected_percentage_of_billed", 0.0)
    total_recv = bill_kpis.get("total_receivables", 0.0)
    total_portfolio = pipe_kpis.get("total_portfolio_value", 0.0)
    open_deals = pipe_kpis.get("open_deals_count", 0)
    total_deals = pipe_kpis.get("total_deals_count", 0)
    open_wos = ops_kpis.get("open_work_orders", 0)

    # Row 1 — 5 primary KPIs
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        kpi_card("Total Portfolio", format_inr(total_portfolio),
                 f"{total_deals} total deals")
    with c2:
        kpi_card("Open Pipeline", format_inr(pipe_kpis.get("open_pipeline_value", 0)),
                 f"{open_deals} active deals", is_positive=True)
    with c3:
        kpi_card("Weighted Est.", format_inr(pipe_kpis.get("weighted_pipeline_value", 0)),
                 "Probability-adjusted", is_warning=True)
    with c4:
        kpi_card("Won Value", format_inr(pipe_kpis.get("won_deals_value", 0)),
                 "Closed Won revenue", is_positive=True)
    with c5:
        kpi_card("Delivery Rate", format_pct(comp_rate),
                 f"{ops_kpis.get('completed_work_orders', 0)}/{ops_kpis.get('total_work_orders', 0)} completed",
                 is_positive=comp_rate >= 75, is_warning=comp_rate < 75)

    st.markdown("<div style='margin-top:6px;'></div>", unsafe_allow_html=True)

    # Row 2 — 3 secondary KPIs
    c6, c7, c8 = st.columns(3)
    with c6:
        kpi_card("Receivables", format_inr(total_recv),
                 f"Collection rate: {format_pct(coll_rate)}",
                 is_risk=total_recv > 0, is_positive=total_recv == 0)
    with c7:
        kpi_card("Open Work Orders", open_wos,
                 "Work orders in progress")
    with c8:
        kpi_card("Collection Rate", format_pct(coll_rate),
                 "Cash collected vs billed",
                 is_positive=coll_rate >= 80, is_warning=60 <= coll_rate < 80, is_risk=coll_rate < 60)

    st.markdown("<div style='margin-top:8px;'></div>", unsafe_allow_html=True)

    # ── 3. AI EXECUTIVE BRIEFING (Deterministic — no Gemini cost, no hallucination) ──
    section_header("AI Executive Briefing", "Intelligence summary derived deterministically from live Monday.com board data.")

    try:
        briefing = _build_executive_briefing(deals_df, work_orders_df)

        b1, b2 = st.columns(2)
        with b1:
            # Top Opportunity
            if briefing["top_opp_sector"] and briefing["top_opp_val"] > 0:
                ai_briefing_card(
                    finding=f"{briefing['top_opp_sector']} holds the highest open pipeline opportunity",
                    metrics=[
                        f"Open pipeline: {format_inr(briefing['top_opp_val'])}",
                        f"Total open deals: {briefing['open_deals']}",
                        f"Won revenue to date: {format_inr(briefing['won_value'])}",
                    ],
                    implication=(
                        "Concentrating sales effort and executive attention on the highest-value open pipeline "
                        "sector maximises expected closure revenue."
                    ),
                    action=f"Prioritise closing {briefing['top_opp_sector']} deals; assign senior pursuit resources.",
                    severity="success",
                    title="🟢 Top Revenue Opportunity"
                )
            else:
                empty_state("No open pipeline data available for opportunity analysis.", "💼")

            # Operational Concern
            stuck = briefing["stuck_count"]
            comp_r = briefing["comp_rate"]
            if stuck > 0:
                ai_briefing_card(
                    finding=f"{stuck} work order(s) are stuck/paused and blocking delivery progress",
                    metrics=[
                        f"Stuck / Paused: {stuck} work orders",
                        f"Delivery completion rate: {format_pct(comp_r)}",
                        f"Total work orders: {briefing['total_wos']}",
                    ],
                    implication=(
                        "Stuck work orders delay milestone completions, block invoice generation, "
                        "and expose the business to contract penalty risk."
                    ),
                    action="Immediately investigate and resolve stuck orders. Escalate to sector leads where required.",
                    severity="critical" if stuck >= 3 else "warning",
                    title="⚙️ Operational Concern"
                )
            elif comp_r < 60:
                ai_briefing_card(
                    finding=f"Delivery completion rate is low at {format_pct(comp_r)}",
                    metrics=[
                        f"Completion rate: {format_pct(comp_r)}",
                        f"Completed: {briefing['total_wos'] - (briefing['total_wos'] - int(comp_r * briefing['total_wos'] / 100))} work orders",
                        f"Total work orders: {briefing['total_wos']}",
                    ],
                    implication="A completion rate below 60% signals delivery bottlenecks that may delay collections.",
                    action="Review backlog, accelerate ongoing orders, and investigate root causes of delays.",
                    severity="warning",
                    title="⚙️ Operational Concern"
                )
            else:
                ai_briefing_card(
                    finding=f"Operations are running smoothly — delivery rate is {format_pct(comp_r)}",
                    metrics=[
                        f"Completion rate: {format_pct(comp_r)}",
                        f"Total work orders: {briefing['total_wos']}",
                        f"Stuck orders: {stuck}",
                    ],
                    implication="Strong delivery rate reduces payment risk and supports healthy billing cycles.",
                    action="Maintain current delivery momentum and focus on pending orders nearing milestones.",
                    severity="success",
                    title="⚙️ Operational Status"
                )

        with b2:
            # Biggest Financial Risk
            if briefing["risk_sector"] and briefing["risk_rv"] > 0:
                ai_briefing_card(
                    finding=f"{briefing['risk_sector']} carries the highest outstanding receivables risk",
                    metrics=[
                        f"Sector receivables: {format_inr(briefing['risk_rv'])}",
                        f"Total receivables: {format_inr(briefing['total_recv'])}",
                        f"Overall billing realization: {format_pct(briefing['billed_pct'])}",
                    ],
                    implication=(
                        "High receivables concentration in a single sector creates cash-flow exposure "
                        "and increases collection risk."
                    ),
                    action=f"Accelerate collection effort in {briefing['risk_sector']}. Escalate to finance head.",
                    severity="critical" if briefing["risk_rv"] > 5_00_000 else "warning",
                    title="🔴 Biggest Financial Risk"
                )
            elif briefing["total_recv"] == 0:
                ai_briefing_card(
                    finding="No outstanding receivables — strong cash collection position",
                    metrics=[
                        f"Total receivables: ₹0",
                        f"Collection rate: {format_pct(briefing['coll_rate'])}",
                    ],
                    implication="Zero receivables indicates excellent cash collection discipline.",
                    action="Maintain current invoicing and collection cadence.",
                    severity="success",
                    title="💰 Financial Status"
                )
            else:
                ai_briefing_card(
                    finding=f"Total outstanding receivables: {format_inr(briefing['total_recv'])}",
                    metrics=[
                        f"Total receivables: {format_inr(briefing['total_recv'])}",
                        f"Collection rate: {format_pct(briefing['coll_rate'])}",
                    ],
                    implication="Monitor receivables closely to prevent cash-flow deterioration.",
                    action="Follow up on outstanding invoices with sector finance contacts.",
                    severity="warning",
                    title="💰 Financial Concern"
                )

            # Collection Rate
            coll_r = briefing["coll_rate"]
            if coll_r < 60:
                ai_briefing_card(
                    finding=f"Cash collection rate is critically low at {format_pct(coll_r)}",
                    metrics=[
                        f"Collection rate: {format_pct(coll_r)}",
                        f"Total receivables: {format_inr(briefing['total_recv'])}",
                        f"Billing realization: {format_pct(briefing['billed_pct'])}",
                    ],
                    implication="A collection rate below 60% represents a significant working capital risk.",
                    action="Initiate urgent collection review. Consider escalating long-overdue invoices.",
                    severity="critical",
                    title="💳 Collection Alert"
                )
            elif coll_r < 80:
                ai_briefing_card(
                    finding=f"Collection rate of {format_pct(coll_r)} is below optimal target",
                    metrics=[
                        f"Collection rate: {format_pct(coll_r)}",
                        f"Total receivables: {format_inr(briefing['total_recv'])}",
                    ],
                    implication="Collection below 80% leaves capital tied up in receivables.",
                    action="Increase collection frequency and prioritise high-value outstanding accounts.",
                    severity="warning",
                    title="💳 Collection Rate"
                )

    except Exception as e:
        st.warning(f"Executive briefing could not be generated: {e}")

    st.markdown("<hr style='border-color:#1B2840; margin:20px 0;'>", unsafe_allow_html=True)

    # ── 4. TODAY'S EXECUTIVE PRIORITIES ──
    section_header("Today's Executive Priorities", "AI-driven business intelligence flags requiring leadership attention.")
    recs = get_executive_recommendations(deals_df, work_orders_df)
    if recs:
        p_col, q_col = st.columns(2)
        high_recs = [r for r in recs if r.get("priority", "").upper() in ("HIGH", "CRITICAL")]
        med_recs  = [r for r in recs if r.get("priority", "").upper() not in ("HIGH", "CRITICAL")]
        with p_col:
            for r in high_recs[:4]:
                priority_card(r.get("priority", "HIGH"), r.get("category", ""), r.get("action", ""), r.get("details", ""))
        with q_col:
            for r in med_recs[:4]:
                priority_card(r.get("priority", "MEDIUM"), r.get("category", ""), r.get("action", ""), r.get("details", ""))
        if not high_recs and not med_recs:
            st.success("✅ No critical issues found. All performance indicators are within acceptable ranges.")
    else:
        st.success("✅ No critical issues found. All performance indicators are within acceptable ranges.")

    st.markdown("<hr style='border-color:#1B2840; margin:20px 0;'>", unsafe_allow_html=True)

    # ── 5. FACTUAL INSIGHTS ──
    section_header("Business Intelligence Findings", "Deterministic insights derived from live Monday.com board data.")
    insights = get_deterministic_insights(deals_df, work_orders_df)
    opps  = [i for i in insights if i.get("type") == "opportunity"]
    risks = [i for i in insights if i.get("type") in ("risk", "governance", "finance")]

    i_col1, i_col2 = st.columns(2)
    with i_col1:
        st.markdown(
            f"<p style='font-size:10px; font-weight:700; color:{C_EMERALD}; text-transform:uppercase; letter-spacing:1px; margin-bottom:10px;'>Opportunities &amp; Highlights</p>",
            unsafe_allow_html=True
        )
        if opps:
            for o in opps[:5]:
                insight_card(o.get("title", ""), o.get("metric", ""), o.get("description", ""), is_risk=False)
        else:
            empty_state("No opportunities identified from current data.", "💡")

    with i_col2:
        st.markdown(
            f"<p style='font-size:10px; font-weight:700; color:{C_RED}; text-transform:uppercase; letter-spacing:1px; margin-bottom:10px;'>Risks &amp; Attention Areas</p>",
            unsafe_allow_html=True
        )
        if risks:
            for r in risks[:5]:
                insight_card(r.get("title", ""), r.get("metric", ""), r.get("description", ""), is_risk=True)
        else:
            empty_state("No critical risks flagged from current data.", "✅")

    st.markdown("<hr style='border-color:#1B2840; margin:20px 0;'>", unsafe_allow_html=True)

    # ── 6. PULSE TABS ──
    section_header("Performance Pulse", "Cross-functional analytics overview.")
    tab_sales, tab_ops, tab_finance, tab_sectors = st.tabs([
        "Sales Pulse", "Operations Pulse", "Finance Pulse", "Sector Ranking"
    ])

    with tab_sales:
        l, r = st.columns(2)
        with l:
            st.plotly_chart(plot_pipeline_by_status(deals_df), use_container_width=True)
        with r:
            st.plotly_chart(plot_pipeline_by_stage(deals_df), use_container_width=True)

    with tab_ops:
        l, r = st.columns(2)
        with l:
            st.plotly_chart(plot_wo_execution_status(work_orders_df), use_container_width=True)
        with r:
            st.plotly_chart(plot_wo_by_sector(work_orders_df), use_container_width=True)

    with tab_finance:
        l, r = st.columns(2)
        with l:
            st.plotly_chart(plot_wo_billing_status(work_orders_df), use_container_width=True)
        with r:
            st.plotly_chart(plot_receivables_by_sector(work_orders_df), use_container_width=True)

    with tab_sectors:
        section_header("Sector Performance Matrix", "Joint sales + operations + finance ranking by business sector.")
        sector_perf = get_sector_performance(deals_df, work_orders_df)
        rows = []
        for s in sector_perf:
            deals_s = s.get("deals", {})
            wos_s   = s.get("work_orders", {})
            ov = wos_s.get("order_value_excl_gst", 0.0)
            bv = wos_s.get("billed_value_excl_gst", 0.0)
            billed_pct = (bv / ov * 100) if ov > 0 else 0.0
            # guard against impossible percentages
            billed_pct = max(0.0, min(200.0, billed_pct))
            rows.append({
                "Sector":        s.get("sector", ""),
                "Deals":         str(deals_s.get("count", 0)),
                "Open Pipeline": format_inr(deals_s.get("open_pipeline_value", 0)),
                "Won Value":     format_inr(deals_s.get("won_value", 0) if "won_value" in deals_s else 0),
                "Work Orders":   str(wos_s.get("count", 0)),
                "Receivables":   format_inr(wos_s.get("receivables", 0)),
                "Billed Ratio":  format_pct(billed_pct),
            })
        if rows:
            st.markdown(
                html_table(
                    rows,
                    columns=["Sector", "Deals", "Open Pipeline", "Won Value", "Work Orders", "Receivables", "Billed Ratio"],
                ),
                unsafe_allow_html=True
            )
        else:
            empty_state("No sector performance data available.", "📊")
