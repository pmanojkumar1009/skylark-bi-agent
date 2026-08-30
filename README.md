# SKYLARK BI — Monday.com Business Intelligence & AI Decision Intelligence Platform

Skylark BI is an enterprise-grade Business Intelligence and AI Decision Intelligence platform that connects directly to Monday.com to aggregate real-world operational data (Deals and Work Orders) and answer founder-level business queries.

It combines **deterministic Python analytics** with **generative AI reasoning (Gemini API)** and enforces a **numerical integrity guardrail** to prevent hallucinations.

---

## 1. Problem & Solution

### The Problem
messy, real-world data from Monday.com boards (missing fields, inconsistent naming, raw text dates, symbols in financial fields) makes standard query engines fail. Furthermore, generative AI models (LLMs) are prone to hallucinations and are mathematically unreliable, which is unacceptable for executive decision-making.

### The Solution
A hybrid design that performs all mathematical calculations deterministically in Python, formats them into a structured context, and feeds them to Gemini. A safety layer checks the output numbers against the calculations to ensure 100% accuracy.

---

## 2. Directory Structure

```text
skylark-bi-agent/
│
├── .env                  # Environment secrets (Board IDs, API Tokens)
├── .gitignore            # Ignored files (prevents committing secrets)
├── requirements.txt      # Declared project dependencies
├── main.py               # Application entrypoint & CLI Query Session
├── dashboard.py          # Streamlit Dashboard Launcher
├── test_analytics.py     # Deterministic calculations unit tests
├── test_ai_agent.py      # Conversational agent mocked unit tests
├── DECISION_LOG.md       # Technical assumptions and design choices
│
└── app/
    ├── __init__.py
    ├── config.py          # Loads and validates environment variables
    ├── monday_client.py   # Monday.com GraphQL API client with pagination
    ├── data_processor.py  # Cleans messy values and maps column hashes
    ├── analytics.py       # Deterministic aggregations & performance summaries
    ├── query_engine.py    # Classifies user query intents and formats context
    ├── ai_agent.py        # Provider-agnostic LLM interface & safety validator
    │
    └── dashboard/         # Dashboard Page Modules
        ├── __init__.py
        ├── components.py  # Shared design system components & Indian formatting
        ├── charts.py      # Plotly chart definitions with Indian axis ticks
        ├── overview.py    # Page 1: Executive Overview & Business Health
        ├── sales.py       # Page 2: Sales & Pipeline Analytics
        ├── operations.py  # Page 3: Operations & Execution Command Center
        ├── finance.py     # Page 4: Finance & Outstanding Receivables
        ├── drilldown.py   # Page 5: Sector Intelligence (Drill-Down)
        ├── data_quality.py # Page 6: Data Governance Console
        └── chat.py        # Page 7: AI Business Assistant Chat (with history)
```

---

## 3. Monday.com Integration & Pagination
* **GraphQL Pagination**: Retrieves deals and work orders from Monday.com using cursor-based pagination (100 records per page), bypassing standard API limits.
* **Cleaning & Normalization**: Normalizes dates to `YYYY-MM-DD`, strips symbols (e.g. `₹`, `Rs.`, `,`) from financial inputs, maps inconsistent sector names to standard categories, and groups statuses.

---

## 4. Analytics & AI Architecture

```
   USER QUERY (CLI or Dashboard Chat)
       ↓
   QUERY UNDERSTANDING (Intent Detection & Routing)
       ↓
   DETERMINISTIC PYTHON ANALYTICS (app/analytics.py)
       ↓
   STRUCTURED VERIFIED METRICS (Context JSON)
       ↓
   LLM ANSWER GENERATION (Gemini API / Fallback Mode)
       ↓
   NUMERICAL VALIDATION (Guardrail check against calculations)
       ↓
   FINAL RESPONSE (Natural Language / Safe Markdown Table)
```

### A. Intent Routing
Routes queries to 14 distinct business intents (e.g. `pipeline_summary`, `sector_performance`, `billing_summary`). Ambiguous queries return clarification prompts.

### B. Conversation Memory
Retains up to 6 rounds of exchange context in the session history, allowing seamless follow-up queries (e.g. "Why?", "What about Mining?").

### C. Grounding & Safety Guardrail
Checks every number > 10.0 in the AI's output against the raw deterministic metrics context. If a mismatch is identified, the output is blocked and swapped with a clean verified metrics report.

### D. Fallback Architecture
If the Gemini API key is missing or rate limits are reached, the system enters Fallback Mode and outputs pre-formatted markdown tables.

---

## 5. Security & Configuration

Secrets are stored securely in `.env` and excluded from source control via `.gitignore`:
- `MONDAY_API_TOKEN`: Access token for Monday.com GraphQL API.
- `DEALS_BOARD_ID`: Deals board ID.
- `WORK_ORDERS_BOARD_ID`: Work orders board ID.
- `GEMINI_API_KEY`: API key for Google GenAI.

---

## 6. Execution & Installation

### Setup
1. Clone the repository.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Configure environment variables in `.env`.

### Run Tests
```bash
python -X utf8 -m unittest test_analytics.py test_ai_agent.py
```

### Run Streamlit UI
```bash
python -m streamlit run dashboard.py
```

### Run CLI Query Loop
```bash
python -X utf8 main.py
```

---

## 7. Decision Log Summary
Refer to [`DECISION_LOG.md`](file:///d:/skylark-bi-agent/DECISION_LOG.md) in the project root for details on architectural assumptions, trade-offs, and future improvements.
