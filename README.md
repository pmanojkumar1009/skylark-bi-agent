Absolutely. Since you **haven’t deployed yet**, your README should not claim a hosted link. Use this **copy-paste-ready README** now; after deployment, you only need to fill in the hosted URL.

````markdown
# Skylark BI — Monday.com Business Intelligence & AI Decision Intelligence Agent

Skylark BI is an AI-powered Business Intelligence agent built for founders and executives to ask natural-language questions about business performance.

The application connects directly to **Monday.com** and analyzes two real-world business datasets:

- **Deals** — sales opportunities and pipeline
- **Work Orders** — operational execution, billing, and receivables

The system combines **deterministic Python analytics** with **Google Gemini** to provide grounded, executive-level answers while minimizing numerical hallucinations.

---

## 🚀 Live Application

> **Hosted Application:** `TODO — ADD DEPLOYED URL HERE`

The application is designed as a Streamlit web application and can be accessed through a browser once deployed.

---

# 1. Problem Statement

Founders and executives often need quick answers to questions such as:

- How is the business performing?
- Which sector has the strongest pipeline?
- What opportunities should we focus on?
- How much money is outstanding?
- Where are receivables concentrated?
- Are there operational problems?
- Which sectors have the most risk?
- How much of the pipeline is likely to close?
- What should leadership focus on this week?

Answering these questions manually requires:

1. Extracting data from Monday.com.
2. Cleaning inconsistent business data.
3. Combining information across multiple boards.
4. Performing calculations and analysis.
5. Interpreting the results.
6. Preparing an executive-friendly response.

Skylark BI automates this workflow through a conversational Business Intelligence agent.

---

# 2. Solution

Skylark BI uses a hybrid architecture:

```text
                    USER QUESTION
                         │
                         ▼
              ┌─────────────────────┐
              │  Query Understanding │
              │   & Intent Routing   │
              └──────────┬──────────┘
                         │
                         ▼
              ┌─────────────────────┐
              │   Monday.com API     │
              │ Deals + Work Orders  │
              └──────────┬──────────┘
                         │
                         ▼
              ┌─────────────────────┐
              │ Data Cleaning &      │
              │ Normalization        │
              └──────────┬──────────┘
                         │
                         ▼
              ┌─────────────────────┐
              │ Deterministic       │
              │ Python Analytics    │
              └──────────┬──────────┘
                         │
                         ▼
              ┌─────────────────────┐
              │ Verified Metrics     │
              │ & Business Context   │
              └──────────┬──────────┘
                         │
                         ▼
              ┌─────────────────────┐
              │ Google Gemini API    │
              │ Natural Language AI  │
              └──────────┬──────────┘
                         │
                         ▼
              ┌─────────────────────┐
              │ Numerical / Safety  │
              │ Validation Layer    │
              └──────────┬──────────┘
                         │
                         ▼
                EXECUTIVE ANSWER
````

The important design principle is:

> **Python performs the calculations. Gemini explains the verified results.**

This prevents the LLM from being responsible for financial or operational calculations.

---

# 3. Key Features

## 3.1 Monday.com Integration

The application connects to Monday.com using its GraphQL API.

It dynamically reads:

* Deals board
* Work Orders board

The application does **not hardcode the provided CSV/XLSX data** as its source of truth.

Data is retrieved directly from Monday.com.

### Pagination

The Monday.com client supports cursor-based pagination and retrieves data in batches.

This allows the application to process boards containing hundreds of records rather than relying on a single API response.

---

# 4. Data Resilience

Real-world business data is often incomplete or inconsistent.

Skylark BI performs data cleaning and normalization before analysis.

Examples include:

### Financial values

Handles values such as:

```text
₹10,000
Rs. 10,000
10,000
10000
```

and converts them into numeric values.

### Dates

Normalizes inconsistent date formats into a consistent internal representation.

### Sector names

Normalizes inconsistent naming conventions so that related records can be analyzed together.

### Missing values

Missing:

* Deal values
* Probabilities
* Dates
* Statuses
* Sector information

are handled gracefully rather than causing the application to crash.

The system also communicates important data-quality limitations to the user.

---

# 5. Business Intelligence Capabilities

The agent supports founder-level questions across several business areas.

## Executive Business Health

Examples:

```text
How are we doing?

How is the business performing?

Give me a leadership update.

What are the three most important things I need to know?
```

---

## Sales & Pipeline

Examples:

```text
Which sector has the biggest pipeline?

Which sector is performing best?

How much of the pipeline is actually likely to close?

Are sales healthy?

Which opportunities are most important?
```

The system can calculate:

* Open pipeline
* Pipeline by sector
* Pipeline by stage
* Weighted pipeline
* Opportunity values
* Pipeline concentration
* Top opportunities

---

## Operational Performance

Examples:

```text
Should I be worried about anything on the operations side?

Are operations keeping up?

Are there any operational problems I should know about?
```

The system analyzes:

* Total work orders
* Completed work orders
* Open backlog
* Delayed orders
* Paused/stuck orders
* Execution status distribution
* Sector-level operational risk

---

## Finance & Receivables

Examples:

```text
How much money is outstanding?

Where is our cash stuck?

Where should we focus our attention to improve cash flow?

How much are we owed?
```

The system analyzes:

* Contract value
* Billed value
* Invoiced value
* Collected payments
* Outstanding receivables
* Collection efficiency
* Receivables concentration

---

## Sector Analysis

The agent can compare sectors such as:

```text
Tell me about Mining.

And Renewables?

Compare Mining and Renewables.

Why is Renewables a risk?
```

Sector analysis combines information from both:

* Deals
* Work Orders

to provide a broader business view.

---

# 6. Conversational Follow-Ups

The agent supports conversational follow-up questions.

For example:

```text
User:
Which sector has the biggest pipeline?

Agent:
Tender has the largest pipeline...

User:
Why?

Agent:
Tender dominates because...

User:
What about Mining?

Agent:
Mining currently has...

User:
Why is that?

Agent:
The main driver is...
```

The application maintains structured conversation context including:

* Previous intent
* Previous sector
* Comparison sectors
* Previous analytical results
* Recent conversation history

This allows short queries such as:

```text
Why?

Where is it concentrated?

What about Mining?

And Renewables?

What makes it so high?
```

to be interpreted in context.

---

# 7. AI Architecture

The application uses **Google Gemini API** for natural-language reasoning.

Gemini receives structured, verified business metrics rather than directly performing raw-data calculations.

Example:

```text
Monday.com
     ↓
Data Processing
     ↓
Python Analytics
     ↓
Verified Metrics
     ↓
Gemini
     ↓
Natural Language Explanation
```

This separation allows the system to combine:

* Deterministic numerical analysis
* LLM reasoning
* Conversational interaction

---

# 8. Numerical Safety Guardrail

Financial and business intelligence systems cannot rely blindly on LLM-generated numbers.

Skylark BI therefore implements a numerical validation layer.

The system:

1. Calculates metrics using Python.
2. Creates a verified analytics context.
3. Sends that context to Gemini.
4. Checks numerical claims in the generated response.
5. Prevents unsupported numerical outputs.
6. Falls back to a verified analytics response when necessary.

The goal is to ensure that important business numbers originate from deterministic calculations rather than being invented by the LLM.

---

# 9. Fallback Mode

The application includes a rule-based fallback architecture.

If Gemini is:

* unavailable
* rate-limited
* incorrectly configured
* missing an API key

the application can still return verified analytics using deterministic Python logic.

For example:

```text
Gemini API
    │
    ├── Available → Gemini-generated explanation
    │
    └── Unavailable → Verified rule-based analytics
```

This ensures that the dashboard does not completely fail when the external LLM service is unavailable.

> In production, the preferred path is **Google Gemini API**.
> The fallback exists for resilience and development/testing.

---

# 10. Intent Detection

The query engine classifies natural-language questions into business intents.

Examples include:

```text
executive_briefing
executive_priorities
sector_pipeline_ranking
sector_performance
pipeline_summary
top_deals
billing_summary
receivables
operational_risk
cross_board_analysis
compare_sectors
data_quality
delay_analysis
follow_up
```

The intent determines which deterministic analytics functions are executed.

---

# 11. Dashboard

The application provides a Streamlit dashboard with multiple analytical views.

### Executive Overview

Provides an overall business health view.

### Sales & Pipeline

Shows pipeline and opportunity performance.

### Operations

Shows work-order execution and operational bottlenecks.

### Finance

Shows invoicing, collections, and outstanding receivables.

### Sector Intelligence

Provides sector-level analysis and comparisons.

### Data Quality

Highlights incomplete or inconsistent business records.

### AI Business Assistant

Provides the conversational interface for founder-level questions.

---

# 12. Project Structure

```text
skylark-bi-agent/
│
├── .gitignore
├── README.md
├── DECISION_LOG.md
├── requirements.txt
├── main.py
├── dashboard.py
│
├── test_analytics.py
├── test_ai_agent.py
├── test_connection.py
├── test_monday.py
│
└── app/
    │
    ├── __init__.py
    ├── config.py
    ├── monday_client.py
    ├── data_processor.py
    ├── analytics.py
    ├── query_engine.py
    ├── ai_agent.py
    │
    └── dashboard/
        ├── __init__.py
        ├── components.py
        ├── charts.py
        ├── overview.py
        ├── sales.py
        ├── operations.py
        ├── finance.py
        ├── drilldown.py
        ├── data_quality.py
        └── chat.py
```

---

# 13. Technology Stack

| Technology             | Purpose                                 |
| ---------------------- | --------------------------------------- |
| Python                 | Backend analytics and application logic |
| Streamlit              | Web dashboard and conversational UI     |
| Pandas                 | Data processing and analysis            |
| Plotly                 | Interactive visualizations              |
| Monday.com GraphQL API | Live business data source               |
| Google Gemini API      | Natural-language reasoning              |
| python-dotenv          | Environment configuration               |
| unittest               | Automated testing                       |

---

# 14. Environment Variables

Create a `.env` file in the project root.

```env
MONDAY_API_TOKEN=your_monday_api_token
DEALS_BOARD_ID=your_deals_board_id
WORK_ORDERS_BOARD_ID=your_work_orders_board_id
GEMINI_API_KEY=your_google_gemini_api_key
```

### Important

Never commit `.env` to GitHub.

The repository `.gitignore` includes:

```text
.env
__pycache__/
*.pyc
.venv/
venv/
```

---

# 15. Installation

## Clone the Repository

```bash
git clone https://github.com/pmanojkumar1009/skylark-bi-agent.git
cd skylark-bi-agent
```

---

## Create a Virtual Environment

### Windows

```powershell
python -m venv .venv
.venv\Scripts\activate
```

### macOS/Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
```

---

## Install Dependencies

```bash
pip install -r requirements.txt
```

---

# 16. Configure Monday.com

The application requires two Monday.com boards:

### Board 1 — Deals

Contains sales pipeline information such as:

* Deal name
* Sector
* Deal value
* Stage
* Probability
* Owner
* Dates

### Board 2 — Work Orders

Contains operational information such as:

* Work order
* Sector
* Order value
* Billing information
* Payment information
* Execution status
* Dates

The application reads the boards dynamically using the Monday.com API.

---

# 17. Run the Application Locally

Start the Streamlit dashboard:

```bash
python -m streamlit run dashboard.py
```

The application will normally be available at:

```text
http://localhost:8501
```

---

# 18. Run the CLI

The project also provides a command-line interface.

```bash
python -X utf8 main.py
```

---

# 19. Run Automated Tests

Run the analytics and AI-agent tests:

```bash
python -X utf8 -m unittest test_analytics.py test_ai_agent.py -v
```

Additional integration tests:

```bash
python -X utf8 -m unittest test_connection.py test_monday.py -v
```

The test suite covers:

* Analytics calculations
* Query routing
* Natural-language queries
* Conversational follow-ups
* Sector analysis
* Pipeline analysis
* Billing analysis
* Operational analysis
* Cross-board analysis
* Data-quality handling
* Fallback behavior
* Numerical safety

---

# 20. Example Questions

The following are examples of questions the agent can answer:

```text
How are we doing?

How is the business performing?

Which sector has the biggest pipeline?

Why is Tender so high?

What about Mining?

Tell me about Renewables.

Why is Renewables a risk?

Are there any operational problems I should know about?

Should I be worried about anything on the operations side?

What deals should I pay attention to?

Which opportunities are most important for us to win?

How much money is outstanding?

Where is it concentrated?

Where is our cash stuck?

How much are we owed?

Are sales healthy?

Are operations keeping up?

What's keeping me up at night?

Where should I put my attention?

Which sector is performing best?

Compare Mining and Renewables.

How much of the pipeline is actually likely to close?
```

---

# 21. Data Quality Considerations

The underlying business data contains incomplete and inconsistent records.

Examples include:

* Missing deal values
* Missing probabilities
* Missing dates
* Inconsistent sector names
* Different financial formats
* Missing operational fields

The system does not silently assume that incomplete information is complete.

Instead, the application surfaces relevant caveats to the user.

For example:

```text
Data Quality Note:
A significant portion of opportunities does not contain an explicit
probability. Weighted pipeline calculations should therefore be
interpreted with caution.
```

---

# 22. Security

Sensitive credentials are never stored directly in source code.

The application uses environment variables for:

```text
MONDAY_API_TOKEN
DEALS_BOARD_ID
WORK_ORDERS_BOARD_ID
GEMINI_API_KEY
```

The `.env` file is excluded from Git using `.gitignore`.

Before pushing the repository, verify:

```bash
git status
```

and ensure that `.env` is not listed.

---

# 23. Error Handling

The application is designed to handle common failures gracefully.

### Monday.com API Failure

The application catches API errors and prevents the dashboard from crashing.

### Gemini API Failure

The application switches to verified rule-based analytics.

### Missing Data

Missing values are handled during processing and appropriate caveats are shown.

### Invalid Queries

Ambiguous queries can result in clarification prompts instead of fabricated answers.

---

# 24. Design Decisions

The major architectural decision was to avoid making the LLM responsible for business calculations.

Instead:

```text
Python = calculations
Gemini = reasoning and explanation
```

This approach provides a balance between:

* Numerical accuracy
* Explainability
* Conversational interaction
* Resilience

More detailed assumptions, trade-offs, limitations, and future improvements are documented in:

```text
DECISION_LOG.md
```

---

# 25. Future Improvements

With additional development time, the platform could be extended with:

* More advanced semantic intent detection
* Better entity resolution across Monday.com boards
* Automated scheduled leadership reports
* Historical trend analysis
* Forecasting models
* More sophisticated probability estimation
* Revenue forecasting
* Automated anomaly detection
* Role-based access control
* Authentication
* Production database/cache
* More advanced LLM evaluation
* Streaming AI responses
* Automated alerts for operational and financial risks

---

# 26. Deployment

The application can be deployed using a Python-compatible hosting platform.

The deployment must provide the following environment variables:

```text
MONDAY_API_TOKEN
DEALS_BOARD_ID
WORK_ORDERS_BOARD_ID
GEMINI_API_KEY
```

After deployment, update the Live Application section at the top of this README:

```text
Hosted Application: https://your-deployed-url
```

The hosted application should be publicly accessible for assignment evaluation.

---

# 27. Assignment Deliverables

This project was developed for the **Skylark Drones Monday.com Business Intelligence Agent assignment**.

The implementation addresses the major assignment requirements:

### Monday.com Integration

Live read-only integration with Monday.com using the GraphQL API.

### Data Resilience

Cleaning, normalization, missing-value handling, and data-quality warnings.

### Query Understanding

Natural-language intent detection and conversational follow-ups.

### Business Intelligence

Founder-level analysis across:

* Sales
* Pipeline
* Operations
* Finance
* Receivables
* Sector performance

### AI Agent

Google Gemini-powered natural-language explanations grounded in deterministic analytics.

### Leadership Support

Executive summaries, priorities, risks, and decision-focused insights.

---

# 28. Submission

### GitHub Repository

```text
https://github.com/pmanojkumar1009/skylark-bi-agent
```

### Hosted Application

```text
TODO — ADD DEPLOYED URL
```

### Decision Log

```text
DECISION_LOG.md
```

The repository contains the source code, setup instructions, tests, architecture documentation, and decision log required for evaluation.

---

# 29. Author

**Manojkumar**

GitHub:

```text
https://github.com/pmanojkumar1009
```

---

## Final Architecture

```text
                  ┌──────────────────────┐
                  │      Founder/User    │
                  └──────────┬───────────┘
                             │
                             ▼
                  ┌──────────────────────┐
                  │ Streamlit Dashboard  │
                  │  Conversational UI   │
                  └──────────┬───────────┘
                             │
                             ▼
                  ┌──────────────────────┐
                  │ Query Engine         │
                  │ Intent + Context     │
                  └──────────┬───────────┘
                             │
                             ▼
              ┌──────────────────────────────┐
              │       Monday.com API         │
              │                              │
              │  Deals       Work Orders     │
              └──────────────┬───────────────┘
                             │
                             ▼
                  ┌──────────────────────┐
                  │ Data Processing      │
                  │ Cleaning/Normalize   │
                  └──────────┬───────────┘
                             │
                             ▼
                  ┌──────────────────────┐
                  │ Python Analytics     │
                  │ Deterministic Math  │
                  └──────────┬───────────┘
                             │
                             ▼
                  ┌──────────────────────┐
                  │ Verified Metrics     │
                  └──────────┬───────────┘
                             │
                             ▼
                  ┌──────────────────────┐
                  │ Google Gemini API    │
                  │ AI Reasoning         │
                  └──────────┬───────────┘
                             │
                             ▼
                  ┌──────────────────────┐
                  │ Numerical Guardrail  │
                  │ + Safety Validation  │
                  └──────────┬───────────┘
                             │
                             ▼
                  ┌──────────────────────┐
                  │ Executive Answer     │
                  │ Tables + Insights    │
                  └──────────────────────┘
```

