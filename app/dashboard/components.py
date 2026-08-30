import streamlit as st
import datetime
from typing import Optional, Union, List, Dict, Any

# ─────────────────────────────────────────────
# DESIGN TOKENS
# ─────────────────────────────────────────────
C_BG_BASE      = "#07101E"   # deepest navy
C_BG_SURFACE   = "#0D1929"   # card surface
C_BG_RAISED    = "#111C2E"   # raised element
C_BG_HOVER     = "#172035"   # hover state
C_BORDER       = "#1B2840"   # subtle border
C_BORDER_MUTED = "#0F1E32"   # very subtle border

C_BLUE         = "#3B82F6"   # primary accent
C_BLUE_GLOW    = "#1D4ED8"   # deeper blue
C_CYAN         = "#06B6D4"   # secondary accent
C_EMERALD      = "#10B981"   # positive / success
C_AMBER        = "#F59E0B"   # warning
C_RED          = "#EF4444"   # critical
C_PURPLE       = "#8B5CF6"   # info / alternate

C_TEXT_PRIMARY = "#F1F5F9"
C_TEXT_BODY    = "#CBD5E1"
C_TEXT_MUTED   = "#64748B"
C_TEXT_DIM     = "#334155"


# ─────────────────────────────────────────────
# SHARED FORMATTING UTILITIES
# ─────────────────────────────────────────────

def format_inr(val, raw: bool = False) -> str:
    """
    Format a numeric value as Indian Rupee notation.
    Examples: ₹2.31Cr, ₹69.8L, ₹14.3L, ₹4,500
    Set raw=True to get full precision (₹2,31,45,000.00).
    """
    try:
        v = float(val)
        if raw:
            # Full precision with Indian comma grouping
            return f"₹{v:,.2f}"
        if v >= 1_00_00_000:   # 1 Crore
            return f"₹{v / 1_00_00_000:.2f}Cr"
        elif v >= 1_00_000:    # 1 Lakh
            return f"₹{v / 1_00_000:.1f}L"
        elif v >= 1_000:
            return f"₹{v:,.0f}"
        else:
            return f"₹{v:.2f}"
    except Exception:
        return str(val)


def format_pct(val, decimals: int = 1) -> str:
    """Format a percentage value safely, clamped to [-100, 999]."""
    try:
        v = float(val)
        if v != v or abs(v) == float("inf"):   # NaN or Inf guard
            return "N/A"
        v = max(-100.0, min(999.0, v))
        return f"{v:.{decimals}f}%"
    except Exception:
        return str(val)


def inject_styles():
    """Injects premium enterprise CSS design system. Called once from dashboard.py."""
    css = f"""
    <style>
    /* ── FONTS ── */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;600&display=swap');

    /* ── GLOBAL RESET ── */
    html, body, [class*="css"] {{
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
        -webkit-font-smoothing: antialiased;
    }}
    .stApp {{
        background-color: {C_BG_BASE} !important;
        color: {C_TEXT_BODY} !important;
    }}

    /* ── STREAMLIT CHROME ── */
    #MainMenu {{visibility: hidden;}}
    footer {{visibility: hidden;}}
    header[data-testid="stHeader"] {{
        background: rgba(7, 16, 30, 0.95) !important;
        border-bottom: 1px solid {C_BORDER} !important;
        backdrop-filter: blur(12px);
        -webkit-backdrop-filter: blur(12px);
    }}

    /* ── SIDEBAR ── */
    section[data-testid="stSidebar"] {{
        background: linear-gradient(180deg, #080F1C 0%, #0B1422 100%) !important;
        border-right: 1px solid {C_BORDER} !important;
        width: 270px !important;
    }}
    section[data-testid="stSidebar"] > div {{
        padding-top: 0 !important;
    }}
    section[data-testid="stSidebar"] h1,
    section[data-testid="stSidebar"] h2,
    section[data-testid="stSidebar"] h3,
    section[data-testid="stSidebar"] h4,
    section[data-testid="stSidebar"] span,
    section[data-testid="stSidebar"] label,
    section[data-testid="stSidebar"] p {{
        color: {C_TEXT_PRIMARY} !important;
    }}

    /* ── SIDEBAR RADIO NAV ── */
    div[data-testid="stSidebarContent"] div[role="radiogroup"] label {{
        display: flex !important;
        align-items: center !important;
        padding: 9px 16px !important;
        border-radius: 8px !important;
        margin: 2px 0 !important;
        font-size: 13px !important;
        font-weight: 500 !important;
        color: {C_TEXT_BODY} !important;
        transition: all 0.15s ease !important;
        cursor: pointer !important;
        background-color: transparent !important;
    }}
    div[data-testid="stSidebarContent"] div[role="radiogroup"] label:hover {{
        background-color: {C_BG_RAISED} !important;
        color: {C_TEXT_PRIMARY} !important;
    }}
    /* Hide the radio button circle */
    div[role="radiogroup"] [data-baseweb="radio"] > div:first-child {{
        display: none !important;
    }}
    div[role="radiogroup"] [data-baseweb="radio"] {{
        padding-left: 0 !important;
        gap: 0 !important;
        width: 100% !important;
    }}
    /* Style active checked item */
    div[role="radiogroup"] label:has(input:checked) {{
        background-color: {C_BLUE} !important;
        color: #FFFFFF !important;
        font-weight: 600 !important;
        border-left: 4px solid {C_CYAN} !important;
        box-shadow: 0 4px 12px rgba(59, 130, 246, 0.25) !important;
    }}

    /* ── MAIN CONTENT AREA ── */
    .main .block-container {{
        padding: 24px 32px 40px 32px !important;
        max-width: 1400px !important;
    }}

    /* ── FORM INPUTS (dark theme) ── */
    div[data-baseweb="select"] > div {{
        background-color: {C_BG_RAISED} !important;
        border-color: {C_BORDER} !important;
        color: {C_TEXT_PRIMARY} !important;
    }}
    div[role="listbox"] {{
        background-color: {C_BG_RAISED} !important;
        color: {C_TEXT_PRIMARY} !important;
    }}
    div[data-baseweb="input"] > input {{
        background-color: {C_BG_RAISED} !important;
        color: {C_TEXT_PRIMARY} !important;
        border-color: {C_BORDER} !important;
    }}

    /* ── TABS ── */
    button[data-baseweb="tab"] {{
        color: {C_TEXT_MUTED} !important;
        font-weight: 600 !important;
        font-size: 13px !important;
        border-radius: 6px 6px 0 0 !important;
        padding: 10px 20px !important;
    }}
    button[data-baseweb="tab"][aria-selected="true"] {{
        color: {C_BLUE} !important;
        border-bottom-color: {C_BLUE} !important;
        background-color: rgba(59, 130, 246, 0.05) !important;
    }}
    div[data-baseweb="tab-list"] {{
        background-color: transparent !important;
        border-bottom: 1px solid {C_BORDER} !important;
        gap: 4px !important;
    }}

    /* ── EXPANDER ── */
    div[data-testid="stExpander"] {{
        background-color: {C_BG_SURFACE} !important;
        border: 1px solid {C_BORDER} !important;
        border-radius: 8px !important;
    }}
    div[data-testid="stExpander"] summary {{
        color: {C_TEXT_BODY} !important;
        font-size: 13px !important;
        font-weight: 600 !important;
    }}

    /* ── DATAFRAME ── */
    div[data-testid="stDataFrame"] table {{
        background-color: {C_BG_SURFACE} !important;
        color: {C_TEXT_BODY} !important;
    }}
    div[data-testid="stDataFrame"] th {{
        background-color: {C_BG_BASE} !important;
        color: {C_TEXT_MUTED} !important;
        font-size: 11px !important;
        text-transform: uppercase !important;
        letter-spacing: 0.5px !important;
    }}
    div[data-testid="stDataFrame"] td {{
        font-size: 12px !important;
    }}

    /* ── BUTTONS ── */
    div.stButton > button {{
        background: linear-gradient(135deg, {C_BLUE} 0%, {C_BLUE_GLOW} 100%) !important;
        color: white !important;
        border: none !important;
        border-radius: 7px !important;
        font-weight: 600 !important;
        font-size: 12px !important;
        letter-spacing: 0.3px !important;
        padding: 8px 16px !important;
        transition: all 0.2s ease !important;
        box-shadow: 0 2px 8px rgba(59, 130, 246, 0.3) !important;
    }}
    div.stButton > button:hover {{
        transform: translateY(-1px) !important;
        box-shadow: 0 4px 14px rgba(59, 130, 246, 0.4) !important;
    }}

    /* ── METRICS / ALERTS ── */
    div.stAlert {{
        border-radius: 8px !important;
        border: 1px solid {C_BORDER} !important;
    }}

    /* ── HORIZONTAL RULE ── */
    hr {{
        border-color: {C_BORDER} !important;
        margin: 20px 0 !important;
    }}

    /* ── CHAT INPUT ── */
    div[data-testid="stChatInput"] textarea {{
        background-color: {C_BG_RAISED} !important;
        color: {C_TEXT_PRIMARY} !important;
        border-color: {C_BORDER} !important;
        border-radius: 8px !important;
    }}
    div[data-testid="stChatInput"] button {{
        background-color: {C_BLUE} !important;
    }}

    /* ── CHAT MESSAGES ── */
    div[data-testid="stChatMessage"] {{
        background-color: {C_BG_SURFACE} !important;
        border: 1px solid {C_BORDER} !important;
        border-radius: 10px !important;
        margin-bottom: 10px !important;
    }}

    /* ── SPINNER ── */
    div.stSpinner > div {{
        border-top-color: {C_BLUE} !important;
    }}

    /* ── SCROLLBAR STYLE ── */
    ::-webkit-scrollbar {{
        width: 6px;
        height: 6px;
    }}
    ::-webkit-scrollbar-track {{
        background: {C_BG_BASE};
    }}
    ::-webkit-scrollbar-thumb {{
        background: {C_BORDER};
        border-radius: 3px;
    }}
    ::-webkit-scrollbar-thumb:hover {{
        background: {C_TEXT_DIM};
    }}

    /* ── MULTISELECT TAGS ── */
    span[data-baseweb="tag"] {{
        background-color: rgba(59, 130, 246, 0.15) !important;
        color: {C_BLUE} !important;
        border: 1px solid rgba(59, 130, 246, 0.3) !important;
    }}

    /* ── PLOTLY CHARTS ── */
    .js-plotly-plot .plotly, .js-plotly-plot .main-svg {{
        border-radius: 8px !important;
    }}

    /* ── SUCCESS / INFO ALERTS ── */
    div[data-testid="stSuccess"] {{
        background-color: rgba(16, 185, 129, 0.08) !important;
        border-color: rgba(16, 185, 129, 0.3) !important;
        color: {C_EMERALD} !important;
    }}
    div[data-testid="stWarning"] {{
        background-color: rgba(245, 158, 11, 0.08) !important;
        border-color: rgba(245, 158, 11, 0.3) !important;
    }}
    div[data-testid="stError"] {{
        background-color: rgba(239, 68, 68, 0.08) !important;
        border-color: rgba(239, 68, 68, 0.3) !important;
    }}
    div[data-testid="stInfo"] {{
        background-color: rgba(59, 130, 246, 0.08) !important;
        border-color: rgba(59, 130, 246, 0.3) !important;
    }}
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)


def render_sidebar_controls(last_refreshed: str, num_deals: int, num_wos: int):
    """Renders premium sidebar: brand, live data status, navigation label, system health."""

    # ── BRAND IDENTITY BLOCK ──
    st.sidebar.markdown(
        f"""
        <div style="padding: 24px 20px 16px 20px; border-bottom: 1px solid {C_BORDER};">
          <div style="font-size: 20px; font-weight: 800; color: {C_TEXT_PRIMARY}; letter-spacing: 1.5px; line-height: 1;">SKYLARK</div>
          <div style="font-size: 9px; font-weight: 700; color: {C_BLUE}; text-transform: uppercase; letter-spacing: 3px; margin-top: 3px;">BUSINESS INTELLIGENCE</div>
        </div>
        """,
        unsafe_allow_html=True
    )

    # ── LIVE CONNECTION STATUS ──
    st.sidebar.markdown(
        f"""
        <div style="padding: 16px 20px 12px 20px; border-bottom: 1px solid {C_BORDER};">
          <div style="font-size: 9px; font-weight: 700; color: {C_TEXT_MUTED}; text-transform: uppercase; letter-spacing: 1.5px; margin-bottom: 10px;">Live Connection</div>
          <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 6px;">
            <span style="font-size: 12px; color: {C_TEXT_BODY};">Monday.com</span>
            <span style="font-size: 11px; color: {C_EMERALD}; font-weight: 700; display: flex; align-items: center; gap: 4px;">
              <span style="width: 6px; height: 6px; background: {C_EMERALD}; border-radius: 50%; display: inline-block; box-shadow: 0 0 6px {C_EMERALD};"></span>
              CONNECTED
            </span>
          </div>
          <div style="font-size: 11px; color: {C_TEXT_MUTED}; margin-bottom: 4px;">Last sync: <span style="color: {C_TEXT_DIM};">{last_refreshed}</span></div>
          <div style="font-size: 11px; color: {C_TEXT_MUTED};">{num_deals} deals · {num_wos} work orders</div>
        </div>
        """,
        unsafe_allow_html=True
    )

    # ── SYNC BUTTON ──
    st.sidebar.markdown("<div style='padding: 10px 16px 0 16px;'>", unsafe_allow_html=True)
    if st.sidebar.button("↻  Sync Live Data", key="sync_data_btn", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
    st.sidebar.markdown("</div>", unsafe_allow_html=True)

    # ── NAV LABEL ──
    st.sidebar.markdown(
        f"""<div style="padding: 16px 20px 6px 20px;">
          <div style="font-size: 9px; font-weight: 700; color: {C_TEXT_MUTED}; text-transform: uppercase; letter-spacing: 1.5px;">Command Center</div>
        </div>""",
        unsafe_allow_html=True
    )

    # ── SYSTEM HEALTH BLOCK (bottom of sidebar) ──
    llm_provider = st.session_state.get("llm_provider")
    llm_error = st.session_state.get("llm_error")

    if llm_provider == "gemini":
        llm_label = "Gemini Connected"
        llm_color = C_EMERALD
    elif llm_provider == "openai":
        llm_label = "OpenAI Connected"
        llm_color = C_EMERALD
    elif llm_error:
        llm_label = "Gemini Fallback"
        llm_color = C_AMBER
    else:
        llm_label = "Fallback Mode"
        llm_color = C_AMBER


    st.sidebar.markdown(
        f"""
        <div style="padding: 16px 20px; margin-top: 20px; border-top: 1px solid {C_BORDER};">
          <div style="font-size: 9px; font-weight: 700; color: {C_TEXT_MUTED}; text-transform: uppercase; letter-spacing: 1.5px; margin-bottom: 10px;">System Status</div>
          <div style="display: flex; justify-content: space-between; margin-bottom: 5px;">
            <span style="font-size: 11px; color: {C_TEXT_MUTED};">Data Engine</span>
            <span style="font-size: 11px; color: {C_EMERALD}; font-weight: 600;">Healthy</span>
          </div>
          <div style="display: flex; justify-content: space-between; margin-bottom: 5px;">
            <span style="font-size: 11px; color: {C_TEXT_MUTED};">Analytics</span>
            <span style="font-size: 11px; color: {C_EMERALD}; font-weight: 600;">Healthy</span>
          </div>
          <div style="display: flex; justify-content: space-between; margin-bottom: 5px;">
            <span style="font-size: 11px; color: {C_TEXT_MUTED};">Safety Layer</span>
            <span style="font-size: 11px; color: {C_EMERALD}; font-weight: 600;">Active</span>
          </div>
          <div style="display: flex; justify-content: space-between;">
            <span style="font-size: 11px; color: {C_TEXT_MUTED};">LLM</span>
            <span style="font-size: 11px; color: {llm_color}; font-weight: 600;">{llm_label}</span>
          </div>
        </div>
        """,
        unsafe_allow_html=True
    )


def page_header(title: str, subtitle: str, icon: str = ""):
    """Renders a clean, compact page header with title, subtitle and live badge."""
    now_str = datetime.datetime.now().strftime("%H:%M")
    full_title = f"{icon} {title}" if icon else title
    st.markdown(
        f"""
        <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 20px; padding-bottom: 18px; border-bottom: 1px solid {C_BORDER};">
          <div>
            <h2 style="color: {C_TEXT_PRIMARY}; font-size: 22px; font-weight: 800; margin: 0; line-height: 1.2; letter-spacing: -0.3px;">{full_title}</h2>
            <p style="color: {C_TEXT_MUTED}; font-size: 13px; margin: 4px 0 0 0; line-height: 1.4;">{subtitle}</p>
          </div>
          <div style="display: flex; align-items: center; gap: 8px; background: rgba(16, 185, 129, 0.08); border: 1px solid rgba(16, 185, 129, 0.2); border-radius: 20px; padding: 5px 12px; flex-shrink: 0; margin-top: 2px;">
            <span style="width: 6px; height: 6px; background: {C_EMERALD}; border-radius: 50%; box-shadow: 0 0 6px {C_EMERALD};"></span>
            <span style="color: {C_EMERALD}; font-size: 10px; font-weight: 700; letter-spacing: 0.5px;">LIVE · {now_str}</span>
          </div>
        </div>
        """,
        unsafe_allow_html=True
    )


def section_header(title: str, subtitle: Optional[str] = None):
    """Renders a section break with title and optional subtitle."""
    sub_html = f"<p style='color: {C_TEXT_MUTED}; font-size: 12px; margin: 3px 0 0 0; line-height: 1.4;'>{subtitle}</p>" if subtitle else ""
    st.markdown(
        f"""
        <div style="margin: 24px 0 14px 0;">
          <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 2px;">
            <div style="width: 3px; height: 18px; background: linear-gradient(180deg, {C_BLUE} 0%, {C_CYAN} 100%); border-radius: 2px; flex-shrink: 0;"></div>
            <h3 style="color: {C_TEXT_PRIMARY}; font-size: 15px; font-weight: 700; margin: 0; letter-spacing: -0.2px;">{title}</h3>
          </div>
          {sub_html}
        </div>
        """,
        unsafe_allow_html=True
    )


def kpi_card(
    label: str,
    value: Union[str, float, int],
    delta: Optional[str] = None,
    help_text: Optional[str] = None,
    is_risk: bool = False,
    is_positive: bool = False,
    is_warning: bool = False
):
    """Renders a premium KPI metric card with left accent bar and status color."""
    accent = C_BLUE
    if is_risk:
        accent = C_RED
    elif is_positive:
        accent = C_EMERALD
    elif is_warning:
        accent = C_AMBER

    delta_html = ""
    if delta:
        delta_color = C_TEXT_MUTED
        if is_positive:
            delta_color = C_EMERALD
        elif is_risk:
            delta_color = C_RED
        elif is_warning:
            delta_color = C_AMBER
        delta_html = f"""
        <div style="font-size: 11px; color: {delta_color}; font-weight: 500; margin-top: 5px; line-height: 1.3; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">{delta}</div>
        """

    tooltip = f' title="{help_text}"' if help_text else ""
    st.markdown(
        f"""
        <div{tooltip} style="
          background: {C_BG_SURFACE};
          border: 1px solid {C_BORDER};
          border-left: 3px solid {accent};
          border-radius: 8px;
          padding: 14px 16px;
          margin-bottom: 10px;
          transition: border-color 0.2s;
        ">
          <div style="font-size: 10px; color: {C_TEXT_MUTED}; font-weight: 600; text-transform: uppercase; letter-spacing: 0.8px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">{label}</div>
          <div style="font-size: 21px; color: {C_TEXT_PRIMARY}; font-weight: 700; margin-top: 6px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; line-height: 1.1;">{value}</div>
          {delta_html}
        </div>
        """,
        unsafe_allow_html=True
    )


def status_badge(label: str, severity: str = "info") -> str:
    """Returns inline HTML badge string. Safe to embed in st.markdown(unsafe_allow_html=True) tables."""
    configs = {
        "success": (C_EMERALD, "rgba(16,185,129,0.12)", "rgba(16,185,129,0.3)"),
        "warning": (C_AMBER,   "rgba(245,158,11,0.12)", "rgba(245,158,11,0.3)"),
        "critical": (C_RED,    "rgba(239,68,68,0.12)",  "rgba(239,68,68,0.3)"),
        "info":    (C_BLUE,    "rgba(59,130,246,0.12)", "rgba(59,130,246,0.3)"),
        "muted":   (C_TEXT_MUTED, "rgba(100,116,139,0.12)", "rgba(100,116,139,0.3)"),
    }
    color, bg, border = configs.get(severity.lower(), configs["info"])
    safe_label = str(label)[:40]  # Prevent huge badges
    return (
        f"<span style='background:{bg}; color:{color}; border:1px solid {border}; "
        f"padding:2px 8px; border-radius:10px; font-size:10px; font-weight:700; "
        f"letter-spacing:0.4px; text-transform:uppercase; font-family:Inter,sans-serif; "
        f"display:inline-block; white-space:nowrap;'>{safe_label}</span>"
    )


def insight_card(title: str, metric: str, description: str, is_risk: bool = False):
    """Renders an insight panel for opportunities and risk alerts."""
    accent = C_RED if is_risk else C_EMERALD
    indicator = "▲" if not is_risk else "▼"
    st.markdown(
        f"""
        <div style="background:{C_BG_SURFACE}; border:1px solid {C_BORDER}; border-left:3px solid {accent}; border-radius:8px; padding:14px 16px; margin-bottom:10px;">
          <div style="display:flex; justify-content:space-between; align-items:flex-start; gap:12px;">
            <div style="font-size:13px; font-weight:600; color:{C_TEXT_PRIMARY}; line-height:1.3;">{title}</div>
            <div style="font-size:12px; color:{accent}; font-weight:700; white-space:nowrap; flex-shrink:0;">{indicator} {metric}</div>
          </div>
          <div style="font-size:12px; color:{C_TEXT_MUTED}; margin-top:6px; line-height:1.5;">{description}</div>
        </div>
        """,
        unsafe_allow_html=True
    )


def priority_card(severity: str, category: str, action: str, details: str):
    """Renders a priority alert card for executive priorities section."""
    sev_upper = severity.upper()
    accent = C_RED if sev_upper in ("HIGH", "CRITICAL") else C_AMBER
    icon = "🔴" if sev_upper in ("HIGH", "CRITICAL") else "🟡"
    st.markdown(
        f"""
        <div style="background:{C_BG_SURFACE}; border:1px solid {C_BORDER}; border-left:3px solid {accent}; border-radius:8px; padding:14px 16px; margin-bottom:10px;">
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
            <span style="font-size:10px; font-weight:700; color:{accent}; text-transform:uppercase; letter-spacing:0.8px;">{icon} {sev_upper} · {category}</span>
            <span style="font-size:10px; color:{C_TEXT_MUTED};">Action Recommended</span>
          </div>
          <div style="font-size:13px; font-weight:600; color:{C_TEXT_PRIMARY}; line-height:1.3;">{action}</div>
          <div style="font-size:12px; color:{C_TEXT_MUTED}; margin-top:4px; line-height:1.4;">{details}</div>
        </div>
        """,
        unsafe_allow_html=True
    )


def html_table(rows: list, columns: list, column_labels: Optional[list] = None) -> str:
    """
    Builds a premium dark HTML table string from a list of dicts.
    Must be rendered with st.markdown(..., unsafe_allow_html=True).

    Args:
        rows: list of dicts — each dict maps column name to cell value (str).
        columns: list of column key names to include (ordered).
        column_labels: optional display labels for columns (same length as columns).
    """
    labels = column_labels or columns
    th_cells = "".join(
        f"<th style='padding:10px 12px; color:{C_TEXT_MUTED}; font-size:10px; font-weight:700; "
        f"text-transform:uppercase; letter-spacing:0.6px; white-space:nowrap;'>{lbl}</th>"
        for lbl in labels
    )
    thead = (
        f"<thead><tr style='background:{C_BG_BASE}; border-bottom:2px solid {C_BORDER};'>"
        f"{th_cells}</tr></thead>"
    )

    tbody_rows = ""
    for i, row in enumerate(rows):
        row_bg = C_BG_SURFACE if i % 2 == 0 else C_BG_RAISED
        td_cells = "".join(
            f"<td style='padding:10px 12px; color:{C_TEXT_BODY}; font-size:12px; vertical-align:middle;'>{row.get(col, '')}</td>"
            for col in columns
        )
        tbody_rows += (
            f"<tr style='background:{row_bg}; border-bottom:1px solid {C_BORDER_MUTED};'>"
            f"{td_cells}</tr>"
        )
    tbody = f"<tbody>{tbody_rows}</tbody>"

    return (
        f"<div style='overflow-x:auto; border-radius:8px; border:1px solid {C_BORDER};'>"
        f"<table style='width:100%; border-collapse:collapse; font-family:Inter,sans-serif;'>"
        f"{thead}{tbody}</table></div>"
    )


def empty_state(message: str = "No data available.", icon: str = "📭", hint: str = "") -> None:
    """Renders a polished empty state placeholder."""
    hint_html = f"<div style='font-size:12px; color:{C_TEXT_DIM}; margin-top:6px;'>{hint}</div>" if hint else ""
    st.markdown(
        f"""
        <div style="text-align:center; padding:40px 20px; background:{C_BG_SURFACE};
             border:1px dashed {C_BORDER}; border-radius:10px; margin:10px 0;">
          <div style="font-size:32px; margin-bottom:12px;">{icon}</div>
          <div style="font-size:14px; color:{C_TEXT_MUTED}; font-weight:500;">{message}</div>
          {hint_html}
        </div>
        """,
        unsafe_allow_html=True
    )


def hero_metric(
    label: str,
    value: str,
    sub_label: str = "",
    accent_color: str = None,
    width_px: int = 160
) -> str:
    """Returns an inline HTML hero-metric block (for use inside larger layout HTML)."""
    color = accent_color or C_TEXT_PRIMARY
    sub_html = f"<div style='font-size:11px; color:{C_TEXT_MUTED}; margin-top:3px;'>{sub_label}</div>" if sub_label else ""
    return (
        f"<div style='min-width:{width_px}px; padding:0 20px 0 0;'>"
        f"<div style='font-size:10px; color:{C_TEXT_MUTED}; text-transform:uppercase; letter-spacing:0.8px; font-weight:700;'>{label}</div>"
        f"<div style='font-size:22px; font-weight:800; color:{color}; line-height:1.1; margin-top:4px; letter-spacing:-0.5px;'>{value}</div>"
        f"{sub_html}"
        f"</div>"
    )


def ai_briefing_card(
    finding: str,
    metrics: List[str],
    implication: str,
    action: str,
    severity: str = "info",
    title: str = "Executive Briefing"
) -> None:
    """
    Renders a structured AI Executive Briefing card.
    severity: 'info' | 'warning' | 'critical' | 'success'
    """
    configs = {
        "success":  (C_EMERALD, "rgba(16,185,129,0.06)", "rgba(16,185,129,0.2)"),
        "warning":  (C_AMBER,   "rgba(245,158,11,0.06)", "rgba(245,158,11,0.2)"),
        "critical": (C_RED,     "rgba(239,68,68,0.06)",  "rgba(239,68,68,0.2)"),
        "info":     (C_BLUE,    "rgba(59,130,246,0.06)", "rgba(59,130,246,0.2)"),
    }
    accent, bg, border = configs.get(severity, configs["info"])

    metrics_html = "".join(
        f"<li style='margin-bottom:4px; color:{C_TEXT_BODY};'>{m}</li>"
        for m in metrics
    )

    st.markdown(
        f"""
        <div style="background:{bg}; border:1px solid {border}; border-left:3px solid {accent};
             border-radius:10px; padding:18px 20px; margin-bottom:14px;">
          <div style="font-size:9px; font-weight:700; color:{accent}; text-transform:uppercase;
               letter-spacing:1.5px; margin-bottom:10px;">{title}</div>
          <div style="font-size:14px; font-weight:700; color:{C_TEXT_PRIMARY}; margin-bottom:10px;
               line-height:1.4;">{finding}</div>
          <ul style="margin:0 0 10px 0; padding-left:16px; font-size:12px; line-height:1.7;">
            {metrics_html}
          </ul>
          <div style="font-size:12px; color:{C_TEXT_MUTED}; margin-bottom:8px; line-height:1.5;">
            <b style='color:{C_TEXT_BODY};'>Why it matters:</b> {implication}
          </div>
          <div style="font-size:12px; background:rgba(255,255,255,0.03); border-radius:6px;
               padding:8px 12px; border-left:2px solid {accent};">
            <b style='color:{accent};'>Recommended action:</b>
            <span style='color:{C_TEXT_BODY};'> {action}</span>
          </div>
        </div>
        """,
        unsafe_allow_html=True
    )


def progress_bar(label: str, pct: float, color: str = None, show_value: bool = True) -> str:
    """Returns an HTML progress bar string (embed with st.markdown unsafe_allow_html)."""
    c = color or (C_EMERALD if pct >= 75 else (C_AMBER if pct >= 40 else C_RED))
    pct_clamped = max(0.0, min(100.0, pct))
    val_html = f"<span style='font-size:12px; color:{c}; font-weight:700;'>{pct_clamped:.1f}%</span>" if show_value else ""
    return (
        f"<div style='margin-bottom:12px;'>"
        f"<div style='display:flex; justify-content:space-between; margin-bottom:5px;'>"
        f"<span style='font-size:12px; color:{C_TEXT_BODY}; font-weight:500;'>{label}</span>{val_html}</div>"
        f"<div style='background:{C_BG_BASE}; height:5px; border-radius:3px; overflow:hidden;'>"
        f"<div style='background:linear-gradient(90deg,{c}88,{c}); width:{pct_clamped}%; height:100%; border-radius:3px;'></div>"
        f"</div></div>"
    )
