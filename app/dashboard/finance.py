import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from app.dashboard.components import (
    kpi_card, section_header, page_header,
    status_badge, html_table, empty_state, format_inr, format_pct, progress_bar,
    C_EMERALD, C_RED, C_AMBER, C_BLUE, C_TEXT_MUTED, C_TEXT_PRIMARY, C_TEXT_BODY, C_BORDER
)
from app.dashboard.charts import plot_receivables_by_sector, plot_billing_waterfall, apply_plotly_theme
from app.analytics import get_billing_summary, get_sector_performance, clean_work_orders_df, normalize_sector


def render_finance_page(deals_df: pd.DataFrame, work_orders_df: pd.DataFrame):
    """Renders Page 4: Finance & Receivables — CFO-style dashboard."""

    page_header(
        "Finance & Receivables",
        "Track contract values, invoicing milestones, cash collections, and outstanding receivable risks.",
        "💰"
    )

    # ── CLEAN DATA ──
    df = clean_work_orders_df(work_orders_df).copy()
    df["normalized_sector"] = df["sector"].apply(normalize_sector)
    df["receivables"]  = df["amount_receivable"].fillna(0.0)
    df["billed_incl"]  = df["billed_value_incl_gst"].fillna(0.0)
    df["collected"]    = df["collected_amount"].fillna(0.0)

    billing = get_billing_summary(work_orders_df)

    # ── KPI STRIP (Top-Level) ──
    section_header("Financial KPIs — At a Glance")

    excl_order  = billing.get("total_order_value_excl_gst", 0.0)
    excl_billed = billing.get("total_billed_value_excl_gst", 0.0)
    excl_to_bill = billing.get("total_amount_to_bill_excl_gst", 0.0)
    incl_order  = billing.get("total_order_value_incl_gst", 0.0)
    collected   = billing.get("total_collected_amount", 0.0)
    receivables = billing.get("total_receivables", 0.0)
    billed_excl_pct = billing.get("billed_percentage_excl", 0.0)
    coll_rate   = billing.get("collected_percentage_of_billed", 0.0)

    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        kpi_card("Contract Value", format_inr(excl_order), "Total Excl. GST")
    with c2:
        kpi_card("Invoiced Billed", format_inr(excl_billed),
                 f"{format_pct(billed_excl_pct)} of contract billed",
                 is_positive=billed_excl_pct >= 50, is_warning=billed_excl_pct < 50)
    with c3:
        kpi_card("Cash Collected", format_inr(collected), "Total received Incl. GST", is_positive=True)
    with c4:
        kpi_card("Receivables", format_inr(receivables), "Outstanding Incl. GST",
                 is_risk=receivables > 0, is_positive=receivables == 0)
    with c5:
        kpi_card("Collection Rate", format_pct(coll_rate),
                 "Collected / Billed Incl. GST",
                 is_positive=coll_rate >= 80, is_warning=60 <= coll_rate < 80, is_risk=coll_rate < 60)

    st.markdown("<div style='margin-top:8px;'></div>", unsafe_allow_html=True)

    # ── SECONDARY KPIs ──
    c6, c7, c8 = st.columns(3)
    with c6:
        kpi_card("Contract Value Incl. GST", format_inr(incl_order, raw=True), "Gross contract total")
    with c7:
        kpi_card("Amount to be Billed", format_inr(excl_to_bill), "Uninvoiced backlog Excl. GST")
    with c8:
        neg_r = df[df["receivables"] < 0]
        kpi_card("Anomalous Records", len(neg_r),
                 "Negative receivables found",
                 is_risk=len(neg_r) > 0, is_positive=len(neg_r) == 0)

    st.markdown("<hr style='border-color:#1B2840; margin:20px 0;'>", unsafe_allow_html=True)

    # ── PROGRESS & RISK ANALYSIS ──
    l_col, r_col = st.columns(2)
    with l_col:
        section_header("Billing & Realization Progress", "Visual realization of contracted and billed revenue.")
        # Billing progress bar
        st.markdown(progress_bar("Billed Realization Rate (Billed / Contract Excl. GST)", billed_excl_pct, C_BLUE), unsafe_allow_html=True)
        # Collection progress bar
        st.markdown(progress_bar("Collection Realization Rate (Collected / Billed Incl. GST)", coll_rate, C_EMERALD), unsafe_allow_html=True)

    with r_col:
        section_header("Receivables Concentration Risk", "Highlighting single-sector concentration exposures.")
        sector_perf = get_sector_performance(deals_df, work_orders_df)
        
        highest_sec, highest_val = None, 0.0
        concentration_rows = []
        for sp in sector_perf:
            wos = sp.get("work_orders", {})
            v = wos.get("receivables", 0.0)
            if v > 0:
                pct = (v / receivables * 100) if receivables > 0 else 0.0
                concentration_rows.append((sp.get("sector", ""), v, pct))
                if v > highest_val:
                    highest_val = v
                    highest_sec = sp.get("sector", "")
        
        # Sort concentration rows descending
        concentration_rows.sort(key=lambda x: x[1], reverse=True)
        
        if concentration_rows:
            html_rows = []
            for sec, val, pct in concentration_rows:
                badge_type = "critical" if pct >= 25 else ("warning" if pct >= 10 else "info")
                html_rows.append({
                    "Sector": f"<span style='color:{C_TEXT_PRIMARY}; font-weight:600;'>{sec}</span>",
                    "Receivables Value": f"<span style='color:#CBD5E1;'>{format_inr(val)}</span>",
                    "Exposure Share": status_badge(format_pct(pct), badge_type)
                })
            st.markdown(
                html_table(html_rows, ["Sector", "Receivables Value", "Exposure Share"]),
                unsafe_allow_html=True
            )
            
            # Show concentration alert if one sector holds >= 25% of receivables
            if highest_sec and highest_val > 0 and receivables > 0:
                conc = highest_val / receivables * 100
                if conc >= 25:
                    st.warning(
                        f"⚠️ **Concentration Alert**: **{highest_sec}** holds "
                        f"**{format_pct(conc)}** of total receivables. "
                        f"Please diversify follow-up activities to mitigate exposure."
                    )
        else:
            empty_state("No outstanding receivables detected. Risk is minimal.", "✅")

    # ── ANOMALIES ──
    neg_r  = df[df["receivables"] < 0]
    neg_b  = df[df.get("amount_to_bill_excl_gst", pd.Series(dtype=float)).fillna(0) < 0] if "amount_to_bill_excl_gst" in df.columns else pd.DataFrame()

    if len(neg_r) > 0 or len(neg_b) > 0:
        st.markdown(f"<div style='margin-top:12px;'></div>", unsafe_allow_html=True)
        section_header("Financial Data Anomalies", "Records with mathematically impossible or suspicious balances.")
        if len(neg_r) > 0:
            st.error(
                f"• **{len(neg_r)}** records with negative receivables — total anomalous balance: {format_inr(neg_r['receivables'].sum())}"
            )
        if len(neg_b) > 0:
            st.error(
                f"• **{len(neg_b)}** records with negative unbilled balances — total: {format_inr(neg_b['amount_to_bill_excl_gst'].sum())}"
            )

    st.markdown("<hr style='border-color:#1B2840; margin:20px 0;'>", unsafe_allow_html=True)

    # ── CHARTS ──
    section_header("Financial Analytics Charts", "Progression waterfall and billing vs collection comparison.")
    cl, cr = st.columns(2)
    with cl:
        st.plotly_chart(plot_billing_waterfall(work_orders_df), use_container_width=True)

    with cr:
        agg = df.groupby("normalized_sector").agg(
            billed_incl=("billed_incl", "sum"),
            collected=("collected", "sum")
        ).reset_index().sort_values("billed_incl", ascending=False)

        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=agg["normalized_sector"], y=agg["billed_incl"],
            name="Invoiced Billed (Incl. GST)", marker_color=C_BLUE,
            customdata=[format_inr(v) for v in agg["billed_incl"]],
            hovertemplate="<b>%{x}</b><br>Billed: %{customdata}<extra></extra>"
        ))
        fig.add_trace(go.Bar(
            x=agg["normalized_sector"], y=agg["collected"],
            name="Cash Collected (Incl. GST)", marker_color=C_EMERALD,
            customdata=[format_inr(v) for v in agg["collected"]],
            hovertemplate="<b>%{x}</b><br>Collected: %{customdata}<extra></extra>"
        ))
        fig.update_layout(barmode="group")
        apply_plotly_theme(fig, "Invoiced Billed vs. Collected by Sector")
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("<hr style='border-color:#1B2840; margin:20px 0;'>", unsafe_allow_html=True)

    # ── SECTOR FINANCE TABLE ──
    section_header("Sector Financial Breakdown", "Per-sector invoicing, collection, and receivables detail.")
    rows = []
    tot_ov = 0.0
    tot_bv = 0.0
    tot_rv = 0.0

    for sp in sector_perf:
        wos = sp.get("work_orders", {})
        ov = wos.get("order_value_excl_gst", 0.0)
        bv = wos.get("billed_value_excl_gst", 0.0)
        rv = wos.get("receivables", 0.0)

        tot_ov += ov
        tot_bv += bv
        tot_rv += rv

        bpct = (bv / ov * 100) if ov > 0 else 0.0
        # Clamp billing percentage to realistic boundaries
        bpct = max(0.0, min(200.0, bpct))
        bpct_sev = "success" if bpct >= 75 else ("warning" if bpct >= 40 else "critical")
        rv_sev = "critical" if rv > 5_00_000 else ("warning" if rv > 0 else "success")

        rows.append({
            "Sector":      f"<span style='color:{C_TEXT_PRIMARY}; font-weight:600;'>{sp.get('sector', '')}</span>",
            "Contract":    f"<span style='color:{C_TEXT_BODY};'>{format_inr(ov)}</span>",
            "Billed":      f"<span style='color:#CBD5E1;'>{format_inr(bv)}</span>",
            "Billed %":    status_badge(format_pct(bpct), bpct_sev),
            "Receivables": status_badge(format_inr(rv), rv_sev) if rv > 0 else status_badge("None", "success"),
        })

    # Summary row at the bottom
    if rows:
        overall_bpct = (tot_bv / tot_ov * 100) if tot_ov > 0 else 0.0
        overall_bpct_sev = "success" if overall_bpct >= 75 else ("warning" if overall_bpct >= 40 else "critical")
        rows.append({
            "Sector":      f"<span style='color:{C_TEXT_PRIMARY}; font-weight:700;'>TOTAL / AVERAGE</span>",
            "Contract":    f"<span style='color:{C_TEXT_PRIMARY}; font-weight:700;'>{format_inr(tot_ov)}</span>",
            "Billed":      f"<span style='color:{C_TEXT_PRIMARY}; font-weight:700;'>{format_inr(tot_bv)}</span>",
            "Billed %":    status_badge(format_pct(overall_bpct), overall_bpct_sev),
            "Receivables": status_badge(format_inr(tot_rv), "critical" if tot_rv > 5_00_000 else "warning") if tot_rv > 0 else status_badge("None", "success"),
        })

        st.markdown(
            html_table(rows,
                       ["Sector", "Contract", "Billed", "Billed %", "Receivables"],
                       ["Sector", "Contract Value (Excl. GST)", "Invoiced Billed", "Billing %", "Outstanding Receivables"]),
            unsafe_allow_html=True
        )
