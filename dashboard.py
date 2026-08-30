import streamlit as st
import datetime

# Configure Streamlit page layouts
st.set_page_config(
    page_title="Skylark Drones - Business Intelligence Dashboard",
    page_icon="🦅",
    layout="wide",
    initial_sidebar_state="expanded"
)

from app.monday_client import MondayClient
from app.data_processor import (
    DEALS_COLUMNS,
    WORK_ORDER_COLUMNS,
    process_board,
    create_dataframe
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

# 1. Inject corporate styles
inject_styles()


# 2. Cached data loading function
@st.cache_data(show_spinner="Syncing live data from Monday.com...")
def load_raw_monday_data():
    """
    Retrieves all deals and work order items dynamically from the Monday.com API.
    Caches results until explicitly cleared by the refresh control button.
    """
    client = MondayClient()
    deals_items = client.get_deals()
    wos_items = client.get_work_orders()
    sync_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return deals_items, wos_items, sync_time


# 3. Load & Process data
try:
    deals_raw, wos_raw, last_sync_time = load_raw_monday_data()
    
    # Process raw columns dynamically
    deals_df = create_dataframe(process_board(deals_raw, DEALS_COLUMNS))
    work_orders_df = create_dataframe(process_board(wos_raw, WORK_ORDER_COLUMNS))
    
except Exception as exc:
    st.error(f"Failed to fetch data from Monday.com API: {exc}")
    st.info("Please verify your MONDAY_API_TOKEN environment variable in .env.")
    st.stop()


# 4. Initialize Conversational AI Agent
if "agent" not in st.session_state:
    try:
        llm = LLMClient()
        st.session_state["has_gemini"] = llm.gemini_key is not None
        st.session_state["has_openai"] = llm.openai_key is not None
        st.session_state["llm_provider"] = llm.provider
        st.session_state["llm_model"] = llm.active_model
        st.session_state["llm_error"] = llm.connection_error
        st.session_state["agent"] = SkylarkBIAgent(deals_df, work_orders_df, llm_client=llm)
    except Exception as e:
        st.sidebar.error(f"AI Agent failed to load: {e}")
else:
    # Ensure refreshed DataFrames are propagated to the agent
    st.session_state["agent"].deals_df = deals_df
    st.session_state["agent"].work_orders_df = work_orders_df



# 5. Render Sidebar Navigation & Brand Header
render_sidebar_controls(last_sync_time, len(deals_df), len(work_orders_df))

selected_tab = st.sidebar.radio(
    "Go to page:",
    [
        "📊 Executive Overview",
        "💼 Sales & Pipeline",
        "⚙️ Operations & Delivery",
        "💰 Finance & Receivables",
        "🔍 Sector Intelligence",
        "🛡️ Data Governance",
        "🤖 AI Business Assistant"
    ],
    label_visibility="collapsed"
)

# 6. Page Routing
if selected_tab == "📊 Executive Overview":
    render_overview_page(deals_df, work_orders_df)
elif selected_tab == "💼 Sales & Pipeline":
    render_sales_page(deals_df, agent=st.session_state.get("agent"))
elif selected_tab == "⚙️ Operations & Delivery":
    render_operations_page(work_orders_df)
elif selected_tab == "💰 Finance & Receivables":
    render_finance_page(deals_df, work_orders_df)
elif selected_tab == "🔍 Sector Intelligence":
    render_drilldown_page(deals_df, work_orders_df)
elif selected_tab == "🛡️ Data Governance":
    render_data_quality_page(deals_df, work_orders_df)
elif selected_tab == "🤖 AI Business Assistant":
    render_chat_page(st.session_state["agent"])
