import streamlit as st
from app.dashboard.components import (
    section_header, page_header, format_inr,
    C_BG_SURFACE, C_BG_RAISED, C_BORDER,
    C_BLUE, C_CYAN, C_EMERALD, C_AMBER, C_RED,
    C_TEXT_PRIMARY, C_TEXT_BODY, C_TEXT_MUTED
)


def render_chat_page(agent):
    """Renders Page 7: AI Business Assistant — with conversation memory."""

    page_header(
        "AI Business Assistant",
        "Enterprise-grade business intelligence powered by Gemini AI and live Monday.com data.",
        "🤖"
    )

    # ── LLM STATUS BADGE ──
    provider = getattr(agent.llm_client, "provider", None)
    active_model = getattr(agent.llm_client, "active_model", None) or getattr(agent.llm_client, "model_name", "Gemini")
    conn_error = getattr(agent.llm_client, "connection_error", None)

    if provider == "gemini":
        badge_color = C_EMERALD
        badge_text  = "● GEMINI CONNECTED"
        badge_sub   = f"Powered by {active_model} · Live analytics context"
    elif provider == "openai":
        badge_color = C_CYAN
        badge_text  = "● OPENAI CONNECTED"
        badge_sub   = f"Powered by {active_model} · Live analytics context"
    else:
        badge_color = C_AMBER
        badge_text  = "◌ GEMINI FALLBACK"
        badge_sub   = f"Deterministic analytics only ({conn_error or 'API unavailable'})"


    st.markdown(
        f"""
        <div style="display:flex; justify-content:space-between; align-items:center;
             background:{C_BG_SURFACE}; border:1px solid {C_BORDER}; border-left:3px solid {badge_color};
             border-radius:8px; padding:12px 18px; margin-bottom:18px;">
          <div>
            <div style="font-size:12px; font-weight:700; color:{badge_color}; letter-spacing:0.5px;">{badge_text}</div>
            <div style="font-size:11px; color:{C_TEXT_MUTED}; margin-top:2px;">{badge_sub}</div>
          </div>
          <div style="font-size:10px; color:{C_TEXT_MUTED}; text-align:right;">
            Conversation memory: last 6 exchanges<br>
            Anti-hallucination: <span style="color:{C_EMERALD};">Active</span>
          </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    # ── QUICK QUESTION SHORTCUTS ──
    section_header("Quick Intelligence Queries", "Click any question to get an instant AI-powered analysis.")

    shortcuts = [
        ("📊 Executive Briefing", "Give me an executive leadership briefing with key metrics, top risk, and top opportunity."),
        ("💼 Pipeline Status",    "What is our current open pipeline value and weighted pipeline estimate?"),
        ("🏆 Top Opportunities",  "What are the top open deal opportunities I should focus on?"),
        ("⚠️ At-Risk Deals",      "Which deals are stale or at risk of not closing?"),
        ("⚙️ Ops Summary",        "Summarise our work order delivery status and any stuck or paused orders."),
        ("💰 Finance Overview",   "What is our current billing, collection rate, and outstanding receivables?"),
        ("🛡️ Data Quality",       "What are the main data quality issues affecting our analytics accuracy?"),
        ("📈 Business Health",    "Give me the overall business health score with key dimension scores."),
    ]

    cols = st.columns(4)
    for i, (label, query) in enumerate(shortcuts):
        with cols[i % 4]:
            if st.button(label, key=f"shortcut_{i}", use_container_width=True):
                st.session_state["pending_query"] = query

    st.markdown("<hr style='border-color:#1B2840; margin:16px 0;'>", unsafe_allow_html=True)

    # ── CONVERSATION HISTORY ──
    if "chat_messages" not in st.session_state:
        st.session_state["chat_messages"] = []

    # Render existing messages
    for msg in st.session_state["chat_messages"]:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # ── HANDLE PENDING QUERY FROM SHORTCUTS ──
    pending = st.session_state.pop("pending_query", None)

    # ── CHAT INPUT ──
    user_input = st.chat_input(
        "Ask anything about pipeline, deals, operations, finance, sector performance...",
        key="chat_input_box"
    )

    # Use pending shortcut query if no manual input
    active_query = user_input or pending

    if active_query:
        # Show user message
        with st.chat_message("user"):
            st.markdown(active_query)
        st.session_state["chat_messages"].append({"role": "user", "content": active_query})

        # Get conversation history (exclude current message we just appended)
        history = st.session_state["chat_messages"][:-1]

        # Generate AI response
        with st.chat_message("assistant"):
            with st.spinner("Analysing live data…"):
                try:
                    # Pass conversation history for memory support
                    response = agent.ask(active_query, conversation_history=history)
                except Exception as e:
                    response = f"An error occurred while generating the response: {e}"

            # Render the response
            st.markdown(response)

            # Show metadata footer
            is_fallback = (
                provider is None or
                "[Safety Fallback" in response or
                response.startswith("Please enter") or
                response.startswith("Would you") or
                "Could you please specify" in response
            )
            mode_label = "Fallback Analytics" if is_fallback else f"Gemini AI ({agent.llm_client.model_name if hasattr(agent.llm_client, 'model_name') else 'gemini'})"
            mode_color = C_AMBER if is_fallback else C_EMERALD

            st.markdown(
                f"<div style='margin-top:8px; font-size:10px; color:{C_TEXT_MUTED}; "
                f"border-top:1px solid {C_BORDER}; padding-top:6px;'>"
                f"<span style='color:{mode_color}; font-weight:700;'>●</span> "
                f"Source: {mode_label} · Live Monday.com data · Anti-hallucination: Active"
                f"</div>",
                unsafe_allow_html=True
            )

        # Save assistant response to history
        st.session_state["chat_messages"].append({"role": "assistant", "content": response})

    # ── CLEAR HISTORY ──
    st.markdown("<div style='margin-top:10px;'></div>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 1, 4])
    with c1:
        if st.button("🗑️ Clear Chat", key="clear_chat", use_container_width=True):
            st.session_state["chat_messages"] = []
            st.rerun()
    with c2:
        msg_count = len(st.session_state.get("chat_messages", []))
        st.markdown(
            f"<div style='padding:8px 0; font-size:11px; color:{C_TEXT_MUTED};'>"
            f"{msg_count // 2} exchanges in memory</div>",
            unsafe_allow_html=True
        )
