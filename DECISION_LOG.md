# SKYLARK BI — Technical Decision Log

This document records the design patterns, architectural choices, and technical trade-offs made in the implementation of the Skylark BI Drones Monday.com assignment.

---

## 1. Problem Interpretation & Objectives

The primary goal of the assignment is to build a conversational Business Intelligence (BI) and AI Decision Intelligence platform that connects to Monday.com boards (Deals and Work Orders) to answer founder-level queries.
The system needs to translate messy, real-world data into actionable strategic insights while protecting numerical integrity (preventing LLM hallucination).

---

## 2. Architecture Decisions

### A. Dynamic Monday.com Data Pipeline
- **Decision**: Implemented dynamic GraphQL queries using paginated requests (100 records/page) in [`monday_client.py`](file:///d:/skylark-bi-agent/app/monday_client.py) instead of hardcoding static CSV/XLSX files.
- **Rationale**: Bypasses the default 500-item Monday API query limit, enabling the platform to scale to large boards while ensuring the dashboard is always operating on live source-of-truth data.

### B. Hybrid Deterministic & Generative AI Design
- **Decision**: Developed a two-layer query processor.
  - **Level 1 (Deterministic)**: Core mathematical calculations are executed programmatically in Python (`analytics.py`).
  - **Level 2 (Generative)**: Gemini acts as a reasoning engine, reading the formatted metrics context to summarize, explain, and recommend actions.
- **Rationale**: LLMs are bad at math. Offloading calculations to Python guarantees that numbers are 100% accurate, while using Gemini ensures the response remains conversational, strategic, and user-friendly.

---

## 3. Data Normalization & Resilience

Monday.com boards contain human-entered values with spelling variations, raw symbol inputs (e.g. `₹`, `Rs.`), and missing properties.
- **Dates**: Normalized multi-format dates to ISO `YYYY-MM-DD` using `pd.to_datetime(..., errors='coerce')`. Malformed dates fall back to `None` without crashing.
- **Finances**: Cleaned currency values by stripping non-numeric symbols, commas, and whitespace before casting to floats.
- **Sectors**: Standardized text casing and mapped common spelling variants or abbreviations (e.g., telecom -> Others).
- **Missing Probabilities**: Mapped `High` = 80%, `Medium` = 50%, `Low` = 20%, treating any blank or invalid fields as 0% weighted probability to prevent forecast inflation.

---

## 4. Anti-Hallucination Strategy (Numerical Guardrail)

- **Decision**: Implemented a post-generation numerical validator in [`ai_agent.py`](file:///d:/skylark-bi-agent/app/ai_agent.py). It parses all numbers > 10.0 mentioned in the LLM's response and verifies their presence in the source analytics context (checking both raw, percentage, and fractional mappings).
- **Rationale**: If a hallucinated metric is identified, the response is blocked, and the system swaps it with a pre-validated deterministic markdown table. This guarantees that no false metrics are shown in the executive command center.

---

## 5. Conversational Memory

- **Decision**: Wired conversation history using a session-state tracker in [`chat.py`](file:///d:/skylark-bi-agent/app/dashboard/chat.py). The past 6 exchanges (12 messages) are formatted as conversation context and prepended to query requests.
- **Rationale**: Allows the agent to maintain focus during follow-ups (e.g., "Why?", "What about Mining?", "Compare them") without bloating prompt tokens or creating state leaks.

---

## 6. Fallback Strategy

- **Decision**: When the Gemini API is offline, rate-limited, or lacks a key, the agent enters **Fallback Mode**. It bypasses LLM prompting and outputs pre-structured markdown reports containing the exact calculation logs.
- **Rationale**: Guarantees high availability. The application remains fully functional even in a disconnected network state, and the UI explicitly badges the mode as "Fallback Mode" to build user trust.

---

## 7. Leadership Briefing Interpretation

- **Decision**: Added a "Leadership Briefing" option that dynamically extracts key business dimensions: Overall Health, Top Opportunity (highest open pipeline sector), Biggest Risk (receivables concentration sector), Operational Concern (stuck work orders count), and Financial Concern (collection rates).
- **Rationale**: Condenses a complex multi-board dataset into 6 actionable bullet points, matching how founders inspect high-level operations.

---

## 8. Key Assumptions & Trade-offs

1. **Sector Alignment**: There is no formal foreign key connecting Deals to Work Orders. They are aligned at the normalized sector level.
2. **Missing Probability weights**: Open deals missing probability are treated as having 0% weight. While conservative, this prevents inflating weighted pipeline estimates.
3. **No Database Cache**: Opted for Streamlit’s memory caching (`@st.cache_data`) for data retrieval rather than creating a secondary database store, prioritizing deployment speed and architectural simplicity.

---

## 9. Future Improvements (With More Time)
- **Automatic Monday.com Webhooks**: Sync data in real-time when board values change, rather than manual sync refreshes.
- **Historical Data Snapshots**: Store weekly database backups to support actual trend lines and predictive analytics.
- **Token Optimization**: Compress historical context blocks with semantic summaries to decrease LLM prompt latency.
