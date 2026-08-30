import streamlit as st
import pandas as pd
from app.dashboard.components import (
    kpi_card, section_header, page_header,
    insight_card, status_badge, html_table, empty_state, format_inr, format_pct,
    C_BG_SURFACE, C_BORDER, C_EMERALD, C_RED, C_AMBER, C_BLUE, C_TEXT_MUTED, C_TEXT_PRIMARY, C_TEXT_BODY
)
from app.dashboard.charts import (
    plot_wo_by_sector,
    plot_wo_execution_status,
    plot_wo_value_by_sector,
    plot_wo_billing_status
)
from app.analytics import clean_work_orders_df, normalize_sector


def render_operations_page(work_orders_df: pd.DataFrame):
    """Renders Page 3: Operations & Delivery Command Center."""

    page_header(
        "Operations & Delivery",
        "Monitor work order delivery, sector completion rates, billing status, and operational bottlenecks.",
        "⚙️"
    )

    # ── CLEAN DATA ──
    df = clean_work_orders_df(work_orders_df).copy()
    df["normalized_sector"] = df["sector"].apply(normalize_sector)
    df["status_clean"] = df["execution_status"].fillna("Unknown / Missing")
    df["amount_excl_gst_clean"] = df["amount_excl_gst"].fillna(0.0)

    # ── FILTERS ──
    with st.expander("Filters", expanded=True):
        c1, c2 = st.columns(2)
        with c1:
            sectors = sorted(df["normalized_sector"].unique())
            sel_sec = st.multiselect("Sector", sectors, default=sectors, key="ops_sec")
        with c2:
            statuses = sorted(df["status_clean"].unique())
            sel_stat = st.multiselect("Execution Status", statuses, default=statuses, key="ops_stat")

    fdf = df[df["normalized_sector"].isin(sel_sec) & df["status_clean"].isin(sel_stat)]
    if fdf.empty:
        empty_state("No work orders match the selected filters.", "🔍", "Try adjusting sector or status filters.")
        return

    # ── METRICS ──
    total_wos   = len(fdf)
    status_l    = fdf["status_clean"].str.lower()
    is_comp     = status_l.isin(["completed", "executed until current month"])
    completed   = int(is_comp.sum())
    ongoing     = int(status_l.isin(["ongoing"]).sum())
    not_started = int(status_l.isin(["not started"]).sum())
    stuck       = int(status_l.isin(["pause / struck", "stuck"]).sum())
    comp_rate   = (completed / total_wos * 100) if total_wos > 0 else 0.0
    total_val   = fdf["amount_excl_gst_clean"].sum()

    # Row 1
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        kpi_card("Total Work Orders", total_wos, "In current filter scope")
    with c2:
        kpi_card("Delivery Rate", format_pct(comp_rate),
                 f"{completed} of {total_wos} completed",
                 is_positive=comp_rate >= 75, is_warning=50 <= comp_rate < 75, is_risk=comp_rate < 50)
    with c3:
        kpi_card("Completed Orders", completed, "Delivered work orders", is_positive=True)
    with c4:
        kpi_card("Contract Value", format_inr(total_val), "Total value excl. GST", is_positive=True)

    # Row 2
    c5, c6, c7, c8 = st.columns(4)
    with c5:
        kpi_card("In Progress", ongoing, "Currently ongoing")
    with c6:
        kpi_card("Not Started", not_started, "Pending initiation")
    with c7:
        kpi_card("Stuck / Paused", stuck, "Requires intervention", is_risk=stuck > 0, is_positive=stuck == 0)
    with c8:
        kpi_card("Backlog Orders", total_wos - completed, "Outstanding uncompleted")

    st.markdown("<div style='margin-top:8px;'></div>", unsafe_allow_html=True)

    # ── OPERATIONAL RISK MATRIX & CRITICAL WORK ORDERS ──
    stuck_df = fdf[fdf["status_clean"].str.lower().isin(["pause / struck", "stuck"])]
    
    if stuck > 0:
        section_header("Operational Risk Matrix & Stuck Work Orders", "Individual work orders currently stalled or paused.")
        
        # High value stuck orders (excl GST >= 1 Lakh) are Critical risk, others are High risk
        stuck_rows = []
        for _, r in stuck_df.iterrows():
            val = float(r.get("amount_excl_gst_clean", 0.0))
            severity = "CRITICAL" if val >= 1_00_000 else "HIGH"
            sev_color = "critical" if severity == "CRITICAL" else "warning"
            
            stuck_rows.append({
                "Risk Level": status_badge(severity, sev_color),
                "Order Name": f"<span style='color:{C_TEXT_PRIMARY}; font-weight:600;'>{r.get('name', '')}</span>",
                "Sector":     f"<span style='color:{C_TEXT_BODY};'>{r.get('normalized_sector', '')}</span>",
                "Value":      f"<span style='color:{C_RED}; font-weight:700;'>{format_inr(val)}</span>",
                "Billing":    status_badge(str(r.get("billing_status", "Unknown")), "warning" if "billed" not in str(r.get("billing_status", "")).lower() else "success"),
            })
            
        st.markdown(
            html_table(stuck_rows,
                       ["Risk Level", "Order Name", "Sector", "Value", "Billing"],
                       ["Risk Level", "Order Name", "Sector", "Contract Value", "Billing Status"]),
            unsafe_allow_html=True
        )
        st.markdown("<div style='margin-top:12px;'></div>", unsafe_allow_html=True)
    else:
        st.success("✅ No stuck or paused work orders detected. Operations flow is healthy.")

    # ── CHARTS ──
    section_header("Delivery Analytics", "Visual breakdown of execution phases, billing stages, and sector workloads.")
    cl, cr = st.columns(2)
    with cl:
        st.plotly_chart(plot_wo_by_sector(fdf), use_container_width=True)
        st.plotly_chart(plot_wo_value_by_sector(fdf), use_container_width=True)
    with cr:
        st.plotly_chart(plot_wo_execution_status(fdf), use_container_width=True)
        st.plotly_chart(plot_wo_billing_status(fdf), use_container_width=True)

    st.markdown("<hr style='border-color:#1B2840; margin:20px 0;'>", unsafe_allow_html=True)

    # ── SECTOR WORKLOAD MATRIX ──
    section_header("Sector Workload & Completion Matrix", "Operational efficiency metrics indexed by business sector.")
    sector_rows = []
    tot_orders = 0
    tot_completed = 0
    tot_stuck = 0
    tot_value = 0.0

    for sec, grp in fdf.groupby("normalized_sector"):
        tot = len(grp)
        comp = int(grp["status_clean"].str.lower().isin(["completed", "executed until current month"]).sum())
        rate = (comp / tot * 100) if tot > 0 else 0.0
        stk  = int(grp["status_clean"].str.lower().isin(["pause / struck", "stuck"]).sum())
        val  = grp["amount_excl_gst_clean"].sum()

        tot_orders += tot
        tot_completed += comp
        tot_stuck += stk
        tot_value += val

        rate_sev = "success" if rate >= 75 else ("warning" if rate >= 50 else "critical")
        stk_sev  = "critical" if stk > 0 else "success"
        sector_rows.append({
            "Sector":      f"<span style='color:{C_TEXT_PRIMARY}; font-weight:600;'>{sec}</span>",
            "Orders":      f"<span style='color:{C_TEXT_BODY};'>{tot}</span>",
            "Completed":   f"<span style='color:{C_EMERALD}; font-weight:600;'>{comp}</span>",
            "Rate":        status_badge(format_pct(rate), rate_sev),
            "Value":       f"<span style='color:#CBD5E1;'>{format_inr(val)}</span>",
            "Stuck":       status_badge(str(stk), stk_sev),
        })

    # Add Summary Row at the bottom
    if sector_rows:
        overall_rate = (tot_completed / tot_orders * 100) if tot_orders > 0 else 0.0
        overall_rate_sev = "success" if overall_rate >= 75 else ("warning" if overall_rate >= 50 else "critical")
        sector_rows.append({
            "Sector":      f"<span style='color:{C_TEXT_PRIMARY}; font-weight:700;'>TOTAL / AVERAGE</span>",
            "Orders":      f"<span style='color:{C_TEXT_PRIMARY}; font-weight:700;'>{tot_orders}</span>",
            "Completed":   f"<span style='color:{C_TEXT_PRIMARY}; font-weight:700;'>{tot_completed}</span>",
            "Rate":        status_badge(format_pct(overall_rate), overall_rate_sev),
            "Value":       f"<span style='color:{C_TEXT_PRIMARY}; font-weight:700;'>{format_inr(tot_value)}</span>",
            "Stuck":       status_badge(str(tot_stuck), "critical" if tot_stuck > 0 else "success"),
        })

        st.markdown(
            html_table(sector_rows,
                       ["Sector", "Orders", "Completed", "Rate", "Value", "Stuck"],
                       ["Sector", "Work Orders", "Completed", "Completion Rate", "Contract Value", "Stuck/Paused"]),
            unsafe_allow_html=True
        )

    st.markdown("<hr style='border-color:#1B2840; margin:20px 0;'>", unsafe_allow_html=True)

    # ── WORK ORDER DETAIL LOG ──
    section_header("Work Order Detail Log", "Individual work order delivery states and contract valuations.")
    detail = fdf[["name", "normalized_sector", "type_of_work", "status_clean",
                   "amount_excl_gst_clean", "amount_incl_gst", "billing_status"]].copy()

    rows = []
    for _, r in detail.iterrows():
        stat_raw = str(r["status_clean"]).lower()
        if "completed" in stat_raw or "executed" in stat_raw:
            stat_sev = "success"
        elif "ongoing" in stat_raw:
            stat_sev = "info"
        elif "stuck" in stat_raw or "pause" in stat_raw:
            stat_sev = "critical"
        else:
            stat_sev = "muted"

        bill_raw = str(r.get("billing_status", "")).lower()
        bill_sev = "success" if "billed" in bill_raw or "collected" in bill_raw else "warning"

        val_excl = format_inr(r.get("amount_excl_gst_clean", 0))
        val_incl_raw = r.get("amount_incl_gst")
        val_incl = format_inr(val_incl_raw) if pd.notna(val_incl_raw) else "—"

        rows.append({
            "Name":     f"<span style='color:{C_TEXT_PRIMARY}; font-weight:600;'>{r.get('name', '')}</span>",
            "Sector":   f"<span style='color:{C_TEXT_BODY};'>{r.get('normalized_sector', '')}</span>",
            "Type":     f"<span style='color:{C_TEXT_MUTED};'>{r.get('type_of_work', '') or '—'}</span>",
            "Status":   status_badge(str(r.get("status_clean", "")), stat_sev),
            "Excl.GST": f"<span style='color:#CBD5E1; font-weight:600;'>{val_excl}</span>",
            "Incl.GST": f"<span style='color:{C_BLUE};'>{val_incl}</span>",
            "Billing":  status_badge(str(r.get("billing_status", "") or "Unknown"), bill_sev),
        })

    st.markdown(
        html_table(rows,
                   ["Name", "Sector", "Type", "Status", "Excl.GST", "Incl.GST", "Billing"],
                   ["Order Name", "Sector", "Type of Work", "Execution Status", "Value Excl.GST", "Value Incl.GST", "Billing Status"]),
        unsafe_allow_html=True
    )
