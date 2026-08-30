import streamlit as st
import pandas as pd
from app.dashboard.components import (
    kpi_card, section_header, page_header,
    status_badge, html_table, empty_state, format_inr, format_pct,
    C_EMERALD, C_RED, C_AMBER, C_BLUE, C_TEXT_MUTED, C_TEXT_PRIMARY, C_TEXT_BODY, C_BG_SURFACE, C_BORDER
)
from app.analytics import get_data_quality_summary, get_business_health_summary


def render_data_quality_page(deals_df: pd.DataFrame, work_orders_df: pd.DataFrame):
    """Renders Page 6: Data Governance & Integrity Console."""

    page_header(
        "Data Governance",
        "Enterprise data quality audit — completeness, anomalies, and board integrity status.",
        "🛡️"
    )

    # ── HEALTH SCORES ──
    health    = get_business_health_summary(deals_df, work_orders_df)
    dq_health = health.get("dimensions", {}).get("data_quality", {})
    overall   = float(dq_health.get("score", 0))

    dq = get_data_quality_summary(deals_df, work_orders_df)
    deals_audit = dq["deals"]
    wos_audit = dq["work_orders"]

    # ── CALCULATE COMPLETENESS DETERMINISTICALLY (ROBUST LOGIC) ──
    deals_critical = ["deal_value", "deal_status", "closure_probability", "deal_stage", "sector_service"]
    wos_critical = ["amount_excl_gst", "billed_value_excl_gst", "collected_amount", "amount_receivable", "execution_status", "sector"]

    deals_comp = 100.0
    if deals_audit["total_records"] > 0:
        missing_sum = sum([deals_audit["missing_fields"].get(c, {}).get("percentage", 0.0) for c in deals_critical])
        deals_comp = max(0.0, 100.0 - (missing_sum / len(deals_critical)))

    wos_comp = 100.0
    if wos_audit["total_records"] > 0:
        missing_sum = sum([wos_audit["missing_fields"].get(c, {}).get("percentage", 0.0) for c in wos_critical])
        wos_comp = max(0.0, 100.0 - (missing_sum / len(wos_critical)))

    # ── SCORE VISUALIZATION ──
    score_color = C_EMERALD if overall >= 75 else (C_AMBER if overall >= 50 else C_RED)
    score_status = "HEALTHY" if overall >= 75 else ("ATTENTION REQUIRED" if overall >= 50 else "CRITICAL RISK")

    score_html = f"""
    <div style="display:grid; grid-template-columns:auto 1fr; gap:24px; background:{C_BG_SURFACE}; border:1px solid {C_BORDER}; border-radius:10px; padding:20px 24px; margin-bottom:20px; align-items:center;">
      <div style="text-align:center; padding-right:24px; border-right:1px solid {C_BORDER}; min-width:145px;">
        <div style="font-size:9px; font-weight:700; color:{C_TEXT_MUTED}; text-transform:uppercase; letter-spacing:1.5px; margin-bottom:8px;">Governance Score</div>
        <div style="font-size:52px; font-weight:800; color:{score_color}; line-height:1; letter-spacing:-2px;">{overall:.0f}</div>
        <div style="font-size:11px; color:{C_TEXT_MUTED}; margin-top:2px;">/100</div>
        <div style="margin-top:10px; font-size:10px; font-weight:700; color:{score_color}; letter-spacing:0.5px;">{score_status}</div>
      </div>
      <div>
        <div style="margin-bottom:14px;">
          <div style="display:flex; justify-content:space-between; margin-bottom:5px;">
            <span style="font-size:12px; color:{C_TEXT_BODY}; font-weight:500;">Deals Board Column Completeness</span>
            <span style="font-size:12px; color:{C_EMERALD if deals_comp>=75 else (C_AMBER if deals_comp>=50 else C_RED)}; font-weight:700;">{format_pct(deals_comp)}</span>
          </div>
          <div style="background:#07101E; height:5px; border-radius:3px; overflow:hidden;">
            <div style="background:{C_EMERALD if deals_comp>=75 else (C_AMBER if deals_comp>=50 else C_RED)}; width:{max(0.0, min(100.0, deals_comp))}%; height:100%; border-radius:3px;"></div>
          </div>
        </div>
        <div>
          <div style="display:flex; justify-content:space-between; margin-bottom:5px;">
            <span style="font-size:12px; color:{C_TEXT_BODY}; font-weight:500;">Work Orders Column Completeness</span>
            <span style="font-size:12px; color:{C_EMERALD if wos_comp>=75 else (C_AMBER if wos_comp>=50 else C_RED)}; font-weight:700;">{format_pct(wos_comp)}</span>
          </div>
          <div style="background:#07101E; height:5px; border-radius:3px; overflow:hidden;">
            <div style="background:{C_EMERALD if wos_comp>=75 else (C_AMBER if wos_comp>=50 else C_RED)}; width:{max(0.0, min(100.0, wos_comp))}%; height:100%; border-radius:3px;"></div>
          </div>
        </div>
      </div>
    </div>
    """
    st.markdown(score_html, unsafe_allow_html=True)

    # ── CAVEAT ──
    st.info(
        "**Board Integrity Notice**: Missing `closure_probability` fields reduce weighted pipeline "
        "accuracy. Missing financial fields disable cash flow tracking. Resolve data gaps directly "
        "on the Monday.com boards to improve analytics fidelity."
    )

    st.markdown("<hr style='border-color:#1B2840; margin:20px 0;'>", unsafe_allow_html=True)

    # ── DATA GOVERNANCE LOG ──
    section_header("Unified Data Governance Audit Log", "Detected completeness and anomaly issues across all Monday.com boards.")
    
    # Critical field descriptions mapping
    field_metadata = {
        "closure_probability": {
            "impact": "Disables weighted pipeline forecasting.",
            "fix": "Set probability ('High', 'Medium', 'Low') based on sales stage."
        },
        "deal_value": {
            "impact": "Distorts total open/won sales valuation.",
            "fix": "Input the estimated or contract deal amount in INR."
        },
        "deal_stage": {
            "impact": "Breaks conversion funnel visualization.",
            "fix": "Select a valid deal stage (e.g. Lead, Proposal, Close)."
        },
        "deal_status": {
            "impact": "Prevents accurate win/loss metrics.",
            "fix": "Update status to 'Won', 'Dead', 'On Hold' or 'Open'."
        },
        "sector_service": {
            "impact": "Disables sector-level segmentation and intelligence.",
            "fix": "Map the deal to its primary business sector."
        },
        "amount_excl_gst": {
            "impact": "Hinders milestone billing tracking.",
            "fix": "Enter order contract value excluding GST."
        },
        "billed_value_excl_gst": {
            "impact": "Prevents calculation of billing realization percentage.",
            "fix": "Enter total amount invoiced excluding GST."
        },
        "collected_amount": {
            "impact": "Disables cash collections tracking.",
            "fix": "Enter cash received amount to date."
        },
        "amount_receivable": {
            "impact": "Disables outstanding debt risk controls.",
            "fix": "Enter outstanding receivable balance based on invoices."
        },
        "execution_status": {
            "impact": "Distorts backlog and delivery analysis.",
            "fix": "Set correct status (e.g. Ongoing, Completed, Stuck)."
        },
        "sector": {
            "impact": "Distorts sector workload matrices.",
            "fix": "Assign order to the correct business sector."
        }
    }

    issues = []

    # Deals missing fields
    for col, d in deals_audit.get("missing_fields", {}).items():
        if col in deals_critical:
            meta = field_metadata.get(col, {"impact": "Hinders sales metrics.", "fix": "Fill column value on Monday.com."})
            issues.append({
                "Severity": "HIGH" if col in ["closure_probability", "deal_value"] else "MEDIUM",
                "Board": "Deals Board",
                "Field": col,
                "Issue": f"{d['count']} missing ({format_pct(d['percentage'])})",
                "Impact": meta["impact"],
                "Fix": meta["fix"]
            })

    # Deals anomalies
    for anomaly in deals_audit.get("anomalies", []):
        issues.append({
            "Severity": "HIGH" if "negative" in anomaly.lower() else "MEDIUM",
            "Board": "Deals Board",
            "Field": "Multiple",
            "Issue": anomaly,
            "Impact": "Distorts sales performance values.",
            "Fix": "Review and correct negative balances."
        })

    # Work Orders missing fields
    for col, d in wos_audit.get("missing_fields", {}).items():
        if col in wos_critical:
            is_all_missing = d["percentage"] == 100.0
            sev = "CRITICAL" if is_all_missing else ("HIGH" if col in ["amount_excl_gst", "billed_value_excl_gst", "amount_receivable"] else "MEDIUM")
            meta = field_metadata.get(col, {"impact": "Hinders operations metrics.", "fix": "Fill column value on Monday.com."})
            issues.append({
                "Severity": sev,
                "Board": "Work Orders Board",
                "Field": col,
                "Issue": f"{d['count']} missing ({format_pct(d['percentage'])})",
                "Impact": "Invoicing tracking disabled" if is_all_missing else meta["impact"],
                "Fix": meta["fix"]
            })

    # Work Orders anomalies
    for anomaly in wos_audit.get("anomalies", []):
        issues.append({
            "Severity": "HIGH" if "negative" in anomaly.lower() else "MEDIUM",
            "Board": "Work Orders Board",
            "Field": "Multiple",
            "Issue": anomaly,
            "Impact": "Distorts receivables and cash calculations.",
            "Fix": "Review and correct negative balances."
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
                "Field":    f"<code style='color:{C_BLUE}; font-size:11px; font-family:\"JetBrains Mono\",monospace;'>{iss['Field']}</code>",
                "Issue":    f"<span style='color:{C_TEXT_MUTED};'>{iss['Issue']}</span>",
                "Impact":   f"<span style='color:{C_TEXT_MUTED}; font-size:11px;'>{iss['Impact']}</span>",
                "Recommended Fix": f"<span style='color:{C_TEXT_BODY}; font-size:11px;'>{iss['Fix']}</span>"
            })
        st.markdown(
            html_table(rows,
                       ["Severity", "Board", "Field", "Issue", "Impact", "Recommended Fix"],
                       ["Severity", "Board", "Field / Column", "Issue Description", "Operational Impact", "Recommended Fix"]),
            unsafe_allow_html=True
        )

        # Summary counts
        crit_count = sum(1 for i in issues if i["Severity"] == "CRITICAL")
        high_count = sum(1 for i in issues if i["Severity"] == "HIGH")
        med_count  = sum(1 for i in issues if i["Severity"] == "MEDIUM")
        st.markdown(
            f"<div style='margin-top:12px; font-size:12px; color:{C_TEXT_MUTED};'>"
            f"Total issues: <b style='color:{C_TEXT_BODY};'>{len(issues)}</b> &nbsp;·&nbsp; "
            f"Critical: <b style='color:{C_RED};'>{crit_count}</b> &nbsp;·&nbsp; "
            f"High: <b style='color:{C_AMBER};'>{high_count}</b> &nbsp;·&nbsp; "
            f"Medium: <b style='color:{C_BLUE};'>{med_count}</b>"
            f"</div>",
            unsafe_allow_html=True
        )
    else:
        st.success("✅ All boards are clean — no data integrity issues detected.")
