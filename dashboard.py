import streamlit as st
import datetime

# ============================================================
# PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="Skylark Drones - Business Intelligence Dashboard",
    page_icon="🦅",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================
# IMPORTS
# ============================================================

from app.monday_client import MondayClient
from app.data_processor import (
    DEALS_COLUMNS,
    WORK_ORDER_COLUMNS,
    process_board,
    create_dataframe,
)
from app.ai_agent import SkylarkBIAgent, LLMClient
from app.dashboard.components import inject_styles, render_sidebar_controls
from app.dashboard.overview import render_overview_page
from app.dashboard.sales import render_sales_page
from app.dashboard.operations import render_operations_page
from app.dashboard.finance import render_finance_page
from app.dashboard.drilldown import render_drilldown_page
from app.dashboard.data_quality import render_data_quality_page
from app.dashboard.chat import render_chat_page


# ============================================================
# CONFIGURATION HELPERS
# ============================================================

def get_secret(name: str, default=None):
    """
    Read configuration from Streamlit Secrets first,
    then fall back to environment variables.

    This allows the same application to work both locally
    using .env and on Streamlit Cloud using Secrets.
    """
    import os

    # Streamlit Cloud / Streamlit secrets
    try:
        value = st.secrets.get(name)
        if value is not None and str(value).strip():
            return value
    except Exception:
        pass

    # Local environment / .env
    return os.getenv(name, default)


# ============================================================
# CORPORATE STYLING
# ============================================================

inject_styles()


# ============================================================
# MONDAY.COM DATA LOADING
# ============================================================

@st.cache_data(
    show_spinner="Syncing live data from Monday.com..."
)
def load_raw_monday_data():
    """
    Retrieve all Deals and Work Orders from Monday.com.

    Results are cached by Streamlit to avoid repeatedly hitting
    the Monday.com API during normal Streamlit reruns.
    """

    client = MondayClient()

    deals_items = client.get_deals()
    work_orders_items = client.get_work_orders()

    sync_time = datetime.datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    return deals_items, work_orders_items, sync_time


# ============================================================
# LOAD & PROCESS DATA
# ============================================================

try:

    deals_raw, wos_raw, last_sync_time = load_raw_monday_data()

    deals_df = create_dataframe(
        process_board(
            deals_raw,
            DEALS_COLUMNS
        )
    )

    work_orders_df = create_dataframe(
        process_board(
            wos_raw,
            WORK_ORDER_COLUMNS
        )
    )

except Exception as exc:

    st.error(
        "Failed to fetch data from Monday.com API."
    )

    st.code(
        str(exc),
        language="text"
    )

    st.info(
        "Please verify your MONDAY_API_TOKEN configuration."
    )

    st.stop()


# ============================================================
# AI AGENT INITIALIZATION
# ============================================================

if "agent" not in st.session_state:

    try:

        llm = LLMClient()

        st.session_state["has_gemini"] = (
            llm.gemini_key is not None
        )

        st.session_state["has_openai"] = (
            llm.openai_key is not None
        )

        st.session_state["llm_provider"] = (
            llm.provider
        )

        st.session_state["llm_model"] = (
            llm.active_model
        )

        st.session_state["llm_error"] = (
            llm.connection_error
        )

        st.session_state["agent"] = SkylarkBIAgent(
            deals_df,
            work_orders_df,
            llm_client=llm,
        )

    except Exception as exc:

        st.session_state["agent"] = None

        st.session_state["has_gemini"] = False
        st.session_state["has_openai"] = False
        st.session_state["llm_provider"] = None
        st.session_state["llm_model"] = None
        st.session_state["llm_error"] = str(exc)

        st.sidebar.warning(
            f"AI Agent unavailable: {exc}"
        )

else:

    # Keep the AI agent synchronized with refreshed data.

    agent = st.session_state.get("agent")

    if agent is not None:

        agent.deals_df = deals_df
        agent.work_orders_df = work_orders_df


# ============================================================
# SIDEBAR
# ============================================================

render_sidebar_controls(
    last_sync_time,
    len(deals_df),
    len(work_orders_df),
)


selected_tab = st.sidebar.radio(
    "Go to page:",
    [
        "📊 Executive Overview",
        "💼 Sales & Pipeline",
        "⚙️ Operations & Delivery",
        "💰 Finance & Receivables",
        "🔍 Sector Intelligence",
        "🛡️ Data Governance",
        "🤖 AI Business Assistant",
    ],
    label_visibility="collapsed",
)


# ============================================================
# PAGE ROUTING
# ============================================================

if selected_tab == "📊 Executive Overview":

    render_overview_page(
        deals_df,
        work_orders_df,
    )


elif selected_tab == "💼 Sales & Pipeline":

    render_sales_page(
        deals_df,
        agent=st.session_state.get("agent"),
    )


elif selected_tab == "⚙️ Operations & Delivery":

    render_operations_page(
        work_orders_df,
    )


elif selected_tab == "💰 Finance & Receivables":

    render_finance_page(
        deals_df,
        work_orders_df,
    )


elif selected_tab == "🔍 Sector Intelligence":

    render_drilldown_page(
        deals_df,
        work_orders_df,
    )


elif selected_tab == "🛡️ Data Governance":

    render_data_quality_page(
        deals_df,
        work_orders_df,
    )


elif selected_tab == "🤖 AI Business Assistant":

    agent = st.session_state.get("agent")

    if agent is None:

        st.error(
            "The AI Business Assistant is currently unavailable."
        )

        st.info(
            "Please verify your Gemini/OpenAI API configuration."
        )

    else:

        render_chat_page(agent)