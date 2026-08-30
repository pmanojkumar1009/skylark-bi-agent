import streamlit as st
import pandas as pd
import plotly.express as px
from app.dashboard.components import (
    kpi_card, section_header, page_header,
    status_badge, html_table, empty_state, format_inr, format_pct,
    C_EMERALD, C_RED, C_AMBER, C_BLUE, C_TEXT_MUTED, C_TEXT_PRIMARY, C_TEXT_BODY, C_BG_SURFACE, C_BORDER
)
from app.dashboard.charts import plot_pipeline_by_status, apply_plotly_theme
from app.analytics import (
    normalize_sector,
    clean_deals_df,
    clean_work_orders_df,
    get_pipeline_summary,
    get_work_order_summary,
    get_billing_summary,
    get_data_quality_summary
)


def render_drilldown_page(deals_df: pd.DataFrame, work_orders_df: pd.DataFrame):
    """Renders Page 5: Sector Intelligence Drill-Down."""

    page_header(
        "Sector Intelligence",
        "Deep-dive analytics per business sector — sales, operations, finance, and data quality.",
        "🔍"
    )

    # ── CLEAN DATA ──
    deals = clean_deals_df(deals_df).copy()
    deals["normalized_sector"] = deals["sector_service"].apply(normalize_sector)
    wos = clean_work_orders_df(work_orders_df).copy()
    wos["normalized_sector"] = wos["sector"].apply(normalize_sector)
    wos["status_clean"] = wos["execution_status"].fillna("Unknown / Missing")

    # ── SECTOR SELECTOR ──
    all_sectors = sorted(set(deals["normalized_sector"].unique()) | set(wos["normalized_sector"].unique()))
    if not all_sectors:
        empty_state("No sectors found in the dataset.", "🔍")
        return

    sel = st.selectbox("Select Sector", all_sectors, key="sector_drill")
    sec_deals = deals[deals["normalized_sector"] == sel]
    sec_wos   = wos[wos["normalized_sector"] == sel]

    # ── SECTOR HEALTH SCORE CALCULATION ──
    if not sec_deals.empty:
        pipe = get_pipeline_summary(sec_deals)
        open_val = pipe.get("open_pipeline_value", 0.0)
        weighted_val = pipe.get("weighted_pipeline_value", 0.0)
        sales_score = (weighted_val / open_val * 100) if open_val > 0 else 50.0
    else:
        sales_score = 50.0

    if not sec_wos.empty:
        tot = len(sec_wos)
        comp = int(sec_wos["status_clean"].str.lower().isin(["completed", "executed until current month"]).sum())
        ops_score = (comp / tot * 100) if tot > 0 else 50.0
    else:
        ops_score = 50.0

    sector_health = (sales_score + ops_score) / 2
    health_color = C_EMERALD if sector_health >= 75 else (C_AMBER if sector_health >= 50 else C_RED)
    health_status = "HEALTHY" if sector_health >= 75 else ("ATTENTION REQUIRED" if sector_health >= 50 else "CRITICAL")

    # Display sector stats banner with health score
    st.markdown(
        f"""
        <div style="display:grid; grid-template-columns: 1fr auto; align-items:center; margin:14px 0;
             padding:16px 20px; background:{C_BG_SURFACE}; border:1px solid {C_BORDER}; border-radius:10px; gap:16px;">
          <div>
            <div style="font-size:11px; color:{C_TEXT_MUTED}; text-transform:uppercase; letter-spacing:1px; font-weight:700;">Active Sector Workspace</div>
            <div style="font-size:24px; font-weight:800; color:{C_BLUE}; margin-top:2px;">{sel}</div>
            <div style="font-size:12px; color:{C_TEXT_BODY}; margin-top:4px;">
              {len(sec_deals)} deals in pipeline · {len(sec_wos)} work orders active
            </div>
          </div>
          <div style="text-align:right; border-left:1px solid {C_BORDER}; padding-left:24px; min-width:140px;">
            <div style="font-size:10px; color:{C_TEXT_MUTED}; text-transform:uppercase; letter-spacing:0.8px; font-weight:700; margin-bottom:4px;">Sector Health Score</div>
            <span style="font-size:26px; font-weight:800; color:{health_color};">{sector_health:.0f}</span>
            <span style="font-size:12px; color:{C_TEXT_MUTED};">/100</span>
            <div style="font-size:9px; font-weight:700; color:{health_color}; letter-spacing:0.5px; margin-top:2px;">{health_status}</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    tab_sales, tab_ops, tab_finance, tab_dq = st.tabs([
        "Sales Pipeline", "Operations", "Finance", "Data Quality"
    ])

    # ── TAB: SALES ──
    with tab_sales:
        if not sec_deals.empty:
            pipe = get_pipeline_summary(sec_deals)
            c1, c2, c3, c4 = st.columns(4)
            with c1:
                kpi_card("Total Deals", pipe.get("total_deals", 0))
            with c2:
                kpi_card("Open Pipeline", format_inr(pipe.get("open_pipeline_value", 0)), is_positive=True)
            with c3:
                kpi_card("Won Value", format_inr(pipe.get("won_deals_value", 0)), is_positive=True)
            with c4:
                kpi_card("Weighted Est.", format_inr(pipe.get("weighted_pipeline_value", 0)), is_warning=True)

            st.markdown("<div style='margin-top:10px;'></div>", unsafe_allow_html=True)
            cl, cr = st.columns(2)
            with cl:
                st.plotly_chart(plot_pipeline_by_status(sec_deals), use_container_width=True)
            with cr:
                df_stage = sec_deals.groupby("deal_stage")["deal_value"].sum().reset_index()
                df_stage = df_stage.sort_values("deal_value", ascending=False)
                if not df_stage.empty:
                    fig_s = px.bar(
                        df_stage, x="deal_stage", y="deal_value",
                        labels={"deal_stage": "Stage", "deal_value": "Value (₹)"},
                        color_discrete_sequence=[C_BLUE]
                    )
                    apply_plotly_theme(fig_s, f"{sel} — Pipeline by Stage")
                    st.plotly_chart(fig_s, use_container_width=True)
            
            # List Individual Deal Names
            st.markdown("<div style='margin-top:12px;'></div>", unsafe_allow_html=True)
            section_header("Sector Deal Pipeline Log", f"Individual deal records mapped to {sel}.")
            deals_rows = []
            for _, r in sec_deals.iterrows():
                val = float(r.get("deal_value", 0.0))
                prob = str(r.get("closure_probability", "None"))
                prob_sev = "success" if prob.lower() == "high" else ("warning" if prob.lower() == "medium" else "critical")
                
                deals_rows.append({
                    "Deal Name": f"<span style='color:{C_TEXT_PRIMARY}; font-weight:600;'>{r.get('name', '')}</span>",
                    "Value": f"<span style='color:{C_EMERALD}; font-weight:700;'>{format_inr(val)}</span>",
                    "Stage": f"<span style='color:#CBD5E1;'>{r.get('deal_stage', '')}</span>",
                    "Status": f"<span style='color:#CBD5E1;'>{r.get('deal_status', 'Unknown')}</span>",
                    "Probability": status_badge(prob, prob_sev),
                    "Owner": f"<span style='color:#CBD5E1;'>{r.get('owner_code', 'Unassigned')}</span>"
                })
            st.markdown(
                html_table(deals_rows, ["Deal Name", "Value", "Stage", "Status", "Probability", "Owner"]),
                unsafe_allow_html=True
            )
        else:
            empty_state(f"No sales deals recorded for sector '{sel}'.", "💼")

    # ── TAB: OPERATIONS ──
    with tab_ops:
        if not sec_wos.empty:
            ops = get_work_order_summary(sec_wos)
            tot = ops.get("total_work_orders", 0)
            comp = ops.get("completed_count", 0)
            rate = (comp / tot * 100) if tot > 0 else 0.0

            c1, c2, c3 = st.columns(3)
            with c1:
                kpi_card("Work Orders", tot)
            with c2:
                kpi_card("Completed", comp, is_positive=True)
            with c3:
                kpi_card("Completion Rate", format_pct(rate),
                         is_positive=rate >= 75, is_warning=50 <= rate < 75, is_risk=rate < 50)

            stuck = sec_wos["execution_status"].fillna("").str.lower().isin(["pause / struck", "stuck"]).sum()
            if stuck > 0:
                st.warning(f"🚨 **{stuck}** work order(s) are stuck/paused in {sel}.")
            else:
                st.success(f"✅ No stuck work orders found in {sel}.")

            st.markdown("<div style='margin-top:10px;'></div>", unsafe_allow_html=True)
            df_status = sec_wos.groupby("execution_status").size().reset_index(name="count")
            if not df_status.empty:
                fig_pie = px.pie(
                    df_status, names="execution_status", values="count",
                    hole=0.45, color_discrete_sequence=[C_BLUE, C_EMERALD, C_AMBER, C_RED, "#8B5CF6", "#06B6D4"]
                )
                apply_plotly_theme(fig_pie, f"{sel} — Execution Status Distribution")
                st.plotly_chart(fig_pie, use_container_width=True)
        else:
            empty_state(f"No work orders found for sector '{sel}'.", "⚙️")

    # ── TAB: FINANCE ──
    with tab_finance:
        if not sec_wos.empty:
            bill = get_billing_summary(sec_wos)
            c1, c2, c3 = st.columns(3)
            with c1:
                kpi_card("Contract Value", format_inr(bill.get("total_order_value_excl_gst", 0)))
            with c2:
                bpct = bill.get("billed_percentage_excl", 0.0)
                kpi_card("Invoiced Billed", format_inr(bill.get("total_billed_value_excl_gst", 0)),
                         f"{format_pct(bpct)} billed",
                         is_positive=bpct >= 50, is_warning=bpct < 50)
            with c3:
                rv = bill.get("total_receivables", 0.0)
                kpi_card("Receivables", format_inr(rv), is_risk=rv > 0, is_positive=rv == 0)

            st.markdown(
                f"<div style='margin-top:10px; padding:12px 16px; background:rgba(59,130,246,0.06); border:1px solid rgba(59,130,246,0.15); border-radius:8px;'>"
                f"<span style='font-size:12px; color:{C_TEXT_MUTED};'>Cash Collected: </span>"
                f"<span style='font-size:12px; color:{C_EMERALD}; font-weight:600;'>{format_inr(bill.get('total_collected_amount', 0))}</span>"
                f"&nbsp;&nbsp;|&nbsp;&nbsp;"
                f"<span style='font-size:12px; color:{C_TEXT_MUTED};'>Collection Rate: </span>"
                f"<span style='font-size:12px; color:{C_TEXT_PRIMARY}; font-weight:600;'>{format_pct(bill.get('collected_percentage_of_billed', 0.0))}</span>"
                f"</div>",
                unsafe_allow_html=True
            )
        else:
            empty_state(f"No financial records found for sector '{sel}'.", "💰")

    # ── TAB: DATA QUALITY ──
    with tab_dq:
        dq = get_data_quality_summary(sec_deals, sec_wos)
        issues = []

        for col, d in dq.get("deals", {}).get("missing_fields", {}).items():
            issues.append({
                "Board": "Deals",
                "Field": col,
                "Issue": f"{d['count']} missing ({format_pct(d['percentage'])})",
                "Severity": "HIGH" if col in ["closure_probability", "deal_value"] else "MEDIUM"
            })
        for col, d in dq.get("work_orders", {}).get("missing_fields", {}).items():
            issues.append({
                "Board": "Work Orders",
                "Field": col,
                "Issue": f"{d['count']} missing ({format_pct(d['percentage'])})",
                "Severity": "CRITICAL" if d["percentage"] == 100 else "HIGH"
            })
        for a in dq.get("deals", {}).get("anomalies", []) + dq.get("work_orders", {}).get("anomalies", []):
            issues.append({
                "Board": "Audit",
                "Field": "Multiple",
                "Issue": a,
                "Severity": "HIGH" if "negative" in a.lower() else "MEDIUM"
            })

        if issues:
            severity_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
            issues.sort(key=lambda x: severity_order.get(x["Severity"].upper(), 99))
            rows = []
            for iss in issues:
                sev = iss["Severity"]
                sev_sev = "critical" if sev == "CRITICAL" else ("warning" if sev == "HIGH" else "info")
                rows.append({
                    "Severity": status_badge(sev, sev_sev),
                    "Board":    f"<span style='color:{C_TEXT_BODY}; font-weight:600;'>{iss['Board']}</span>",
                    "Field":    f"<code style='color:{C_BLUE}; font-size:11px;'>{iss['Field']}</code>",
                    "Issue":    f"<span style='color:{C_TEXT_MUTED};'>{iss['Issue']}</span>",
                })
            st.markdown(
                html_table(rows, ["Severity", "Board", "Field", "Issue"]),
                unsafe_allow_html=True
            )
        else:
            st.success(f"✅ All board records for '{sel}' are clean and complete.")
