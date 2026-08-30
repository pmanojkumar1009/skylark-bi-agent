
# Skylark BI — AI Business Intelligence & Decision Intelligence Agent

> **An AI-powered Business Intelligence platform that lets founders and executives ask natural-language questions about sales, operations, finance, and business performance — using live Monday.com data.**

[![Streamlit](https://img.shields.io/badge/Streamlit-App-red?logo=streamlit)](https://streamlit.io/)
[![Pandas](https://img.shields.io/badge/Pandas-Analytics-150458?logo=pandas)](https://pandas.pydata.org/)
[![Google Gemini](https://img.shields.io/badge/Google-Gemini-orange)](https://ai.google.dev/)
[![Monday.com](https://img.shields.io/badge/Monday.com-GraphQL-6161FF)](https://developer.monday.com/api-reference/docs)

**Live Demo:** https://skylark-bi-agent-kuatxs6sq3uxbncst2r2ae.streamlit.app/  
**Repository:** https://github.com/pmanojkumar1009/skylark-bi-agent

---

## Overview

Skylark BI is a **conversational Business Intelligence and Decision Intelligence platform** designed for founders and executives.

Instead of manually opening dashboards, filtering spreadsheets, and calculating KPIs, users can simply ask questions such as:

> **"Which sector has the biggest pipeline?"**

> **"Where is our cash stuck?"**

> **"Are there any operational risks?"**

> **"Compare Mining and Renewables."**

> **"What should I focus on this week?"**

Skylark BI retrieves live business data from **Monday.com**, performs deterministic analytics using Python, and uses **Google Gemini** to convert verified metrics into concise executive-level insights.

### Core principle

```text
Python calculates.
Gemini explains.
````

This separation is intentional: **business-critical numbers are calculated deterministically rather than relying on an LLM to perform financial or operational calculations.**

---

# Why Skylark BI?

Traditional BI workflows often require users to:

```text
Find the data
     ↓
Clean the data
     ↓
Build calculations
     ↓
Filter dashboards
     ↓
Interpret charts
     ↓
Make a decision
```

Skylark BI turns that into:

```text
Ask a question
     ↓
Understand intent
     ↓
Retrieve live business data
     ↓
Calculate verified metrics
     ↓
Apply AI reasoning
     ↓
Receive an executive answer
```

The goal is not simply to build another dashboard.

The goal is to create a **decision-support layer on top of business data.**

---

# Key Features

## 1. Live Monday.com Integration

Skylark BI connects directly to Monday.com's GraphQL API.

It works with two primary business datasets:

* **Deals** — sales opportunities and pipeline
* **Work Orders** — operational execution, billing, and receivables

The application retrieves data dynamically rather than treating local CSV/XLSX files as the source of truth.

### API capabilities

* GraphQL API integration
* Cursor-based pagination
* Multi-board data retrieval
* Error handling
* Environment-based credentials
* Live business data

---

# 2. Natural-Language Business Intelligence

Users do not need to know SQL, Pandas, or dashboard filters.

They can ask questions naturally.

### Executive Questions

```text
How are we doing?

How is the business performing?

Give me a leadership update.

What should I focus on this week?

What's keeping me up at night?
```

### Sales & Pipeline

```text
Which sector has the biggest pipeline?

Which opportunities should we focus on?

Are sales healthy?

How much of the pipeline is likely to close?

Which deals are most important?
```

### Operations

```text
Are there any operational problems?

Are operations keeping up?

Which sector has the highest operational risk?
```

### Finance

```text
How much money is outstanding?

Where is our cash stuck?

How much are we owed?

Where are receivables concentrated?
```

### Sector Intelligence

```text
Tell me about Mining.

What about Renewables?

Compare Mining and Renewables.

Why is Renewables a risk?
```

---

# 3. Deterministic Analytics Engine

The application uses Python and Pandas for business calculations.

The analytics layer provides capabilities including:

* Pipeline analysis
* Weighted pipeline
* Pipeline by sector
* Pipeline by stage
* Revenue by sector
* Top opportunities
* Priority opportunities
* Billing analysis
* Receivables analysis
* Operational risk
* Work-order performance
* Business health
* Leadership KPIs
* Data-quality analysis
* Cross-board sector analysis

This ensures that critical metrics are **reproducible and verifiable.**

---

# 4. AI-Powered Executive Reasoning

Google Gemini is used as the reasoning and explanation layer.

Gemini does not receive responsibility for calculating the underlying business metrics.

Instead:

```text
Monday.com
    ↓
Data Processing
    ↓
Deterministic Python Analytics
    ↓
Verified Business Metrics
    ↓
Google Gemini
    ↓
Executive Explanation
```

This allows the system to combine:

* Numerical accuracy
* Business reasoning
* Natural-language interaction
* Executive-friendly communication

---

# 5. Numerical Hallucination Guardrail

A major challenge with AI-powered BI systems is **numerical hallucination**.

An LLM may produce a plausible-looking number that does not actually exist in the source data.

Skylark BI implements a validation layer to reduce this risk.

### Validation flow

```text
Verified Metrics
      ↓
     Gemini
      ↓
Generated Response
      ↓
Numerical Validation
      ↓
 ┌────┴────┐
 │         │
Valid    Invalid
 │         │
 ▼         ▼
Answer   Verified
         Fallback
```

If the generated response contains unsupported numerical values, the system can reject the response and fall back to verified structured analytics.

This makes the AI layer safer for business and financial questions.

---

# 6. Intelligent Fallback Mode

Skylark BI does not completely depend on Gemini being available.

If the LLM service is unavailable because of:

* Missing API key
* API failure
* Rate limiting
* Configuration problems

the application can fall back to deterministic rule-based analytics.

```text
             Gemini Available?
                  │
          ┌───────┴───────┐
         YES              NO
          │                │
          ▼                ▼
      Gemini AI       Rule-Based
      Explanation      Analytics
          │                │
          └───────┬────────┘
                  ▼
           Verified Answer
```

This improves application resilience.

---

# 7. Conversational Memory

The agent supports multi-turn business conversations.

For example:

```text
User:
Which sector has the biggest pipeline?

Agent:
Tender currently has the largest pipeline.

User:
Why?

Agent:
The main driver is the concentration of high-value
opportunities in that sector.

User:
What about Mining?

Agent:
Mining has a smaller pipeline but stronger operational
activity...

User:
Why is that?

Agent:
The difference is primarily driven by...
```

The system maintains relevant conversational context such as:

* Previous intent
* Current sector
* Comparison sectors
* Previous analytical results
* Recent conversation history

This allows short follow-up questions such as:

```text
Why?

What about Mining?

And Renewables?

Where is it concentrated?

What makes it so high?
```

to be interpreted in context.

---

# 8. Data Resilience & Quality Handling

Real-world business data is rarely perfectly clean.

Skylark BI includes normalization and defensive handling for inconsistent data.

### Financial values

Handles formats such as:

```text
₹10,000
Rs. 10,000
10,000
10000
```

### Probabilities

Handles values such as:

```text
High
Medium
Low
80%
0.8
80
```

### Missing data

The system safely handles missing:

* Deal values
* Probabilities
* Dates
* Statuses
* Sector information
* Operational fields

### Data-quality awareness

The application surfaces relevant limitations instead of silently assuming missing information is valid.

---

# 9. Business Intelligence Modules

| Module                | Purpose                                                |
| --------------------- | ------------------------------------------------------ |
| Executive Overview    | Overall business health and leadership KPIs            |
| Sales & Pipeline      | Pipeline, opportunities, stages and sector performance |
| Operations            | Work-order execution, delays and operational risks     |
| Finance               | Billing, collections and receivables                   |
| Sector Intelligence   | Cross-sector and cross-board analysis                  |
| Data Quality          | Missing and inconsistent business data                 |
| AI Business Assistant | Natural-language business questions                    |

---

# Architecture

```text
                         ┌──────────────────────┐
                         │      Founder / User  │
                         └──────────┬───────────┘
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │   Streamlit Dashboard│
                         │   Conversational UI  │
                         └──────────┬───────────┘
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │     Query Engine     │
                         │ Intent + Context     │
                         └──────────┬───────────┘
                                    │
                                    ▼
                    ┌───────────────────────────────┐
                    │        Monday.com API         │
                    │                               │
                    │    Deals + Work Orders        │
                    └───────────────┬───────────────┘
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │   Data Processing    │
                         │ Cleaning + Normalize │
                         └──────────┬───────────┘
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │  Python Analytics    │
                         │  Deterministic Math  │
                         └──────────┬───────────┘
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │  Verified Metrics    │
                         └──────────┬───────────┘
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │   Google Gemini      │
                         │   AI Reasoning       │
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
                         │  Executive Answer    │
                         │ Insights + Tables    │
                         └──────────────────────┘
```

---

# Technology Stack

| Technology                 | Role                            |
| -------------------------- | ------------------------------- |
| **Python**                 | Application and analytics logic |
| **Streamlit**              | Interactive web dashboard       |
| **Pandas**                 | Data processing and analytics   |
| **Plotly**                 | Interactive visualizations      |
| **Monday.com GraphQL API** | Live business data              |
| **Google Gemini API**      | AI reasoning and explanation    |
| **python-dotenv**          | Environment configuration       |
| **unittest**               | Automated testing               |

---

# Project Structure

```text
skylark-bi-agent/
│
├── .devcontainer/
│   └── devcontainer.json
│
├── app/
│   ├── __init__.py
│   ├── ai_agent.py
│   ├── analytics.py
│   ├── config.py
│   ├── data_processor.py
│   ├── monday_client.py
│   ├── query_engine.py
│   │
│   └── dashboard/
│       ├── charts.py
│       ├── chat.py
│       ├── components.py
│       ├── data_quality.py
│       ├── drilldown.py
│       ├── finance.py
│       ├── operations.py
│       ├── overview.py
│       └── sales.py
│
├── dashboard.py
├── main.py
│
├── test_ai_agent.py
├── test_analytics.py
├── test_connection.py
├── test_monday.py
│
├── DECISION_LOG.md
├── README.md
├── requirements.txt
└── .gitignore
```

---

# Installation

## 1. Clone the repository

```bash
git clone https://github.com/pmanojkumar1009/skylark-bi-agent.git
cd skylark-bi-agent
```

## 2. Create a virtual environment

### Windows

```powershell
python -m venv .venv
.venv\Scripts\activate
```

### macOS / Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
```

## 3. Install dependencies

```bash
pip install -r requirements.txt
```

---

# Configuration

Create a `.env` file in the project root:

```env
MONDAY_API_TOKEN=your_monday_api_token
DEALS_BOARD_ID=your_deals_board_id
WORK_ORDERS_BOARD_ID=your_work_orders_board_id
GEMINI_API_KEY=your_google_gemini_api_key
```

### Security

Credentials are **never stored in source code**.

The `.env` file is excluded from Git:

```text
.env
__pycache__/
*.pyc
.venv/
venv/
```

Never commit API keys or other secrets to GitHub.

---

# Running the Application

Start the Streamlit dashboard:

```bash
python -m streamlit run dashboard.py
```

The application will normally open at:

```text
http://localhost:8501
```

---

# CLI

The project also provides a command-line interface:

```bash
python -X utf8 main.py
```

---

# Testing

Skylark BI includes automated tests covering analytics, AI behavior, routing, resilience, and data handling.

Run the complete test suite:

```bash
python -X utf8 -m unittest discover -v
```

### Current test result

```text
Ran 40 tests
OK
```

The tests cover:

* Business health calculations
* Pipeline calculations
* Sector performance
* Cross-board analytics
* Revenue analysis
* Billing calculations
* Receivables
* Operational risk
* Priority opportunities
* Query routing
* Natural-language questions
* Founder/executive questions
* Conversational follow-ups
* LLM fallback behavior
* Numerical hallucination prevention
* Data-quality handling
* Mixed-type probability values
* Empty datasets

---

# Example User Journey

### Question

```text
Which sector has the biggest pipeline?
```

### Processing

```text
Natural Language
       ↓
Intent Detection
       ↓
Sector Pipeline Analytics
       ↓
Monday.com Deals Data
       ↓
Deterministic Calculation
       ↓
Verified Metrics
       ↓
Gemini Explanation
```

### Result

The user receives a concise executive explanation instead of raw data or a complicated query.

---

# Design Philosophy

The most important architectural decision in Skylark BI is the separation between **calculation** and **reasoning**.

```text
┌──────────────────────────────┐
│ Python                       │
│                              │
│ • Data processing            │
│ • Financial calculations     │
│ • KPI calculations           │
│ • Aggregations               │
│ • Ranking                    │
│ • Validation                 │
└──────────────┬───────────────┘
               │
               ▼
       Verified Metrics
               │
               ▼
┌──────────────────────────────┐
│ Google Gemini                │
│                              │
│ • Explanation                │
│ • Context                    │
│ • Reasoning                  │
│ • Conversational responses   │
└──────────────────────────────┘
```

This design provides a better balance between:

* Accuracy
* Explainability
* Resilience
* Natural-language interaction
* Business usability

---

# Reliability & Error Handling

Skylark BI is designed to fail gracefully.

### Monday.com API failure

API failures are handled without unnecessarily crashing the dashboard.

### Gemini failure

The application can fall back to deterministic analytics.

### Invalid or ambiguous question

The agent can request clarification instead of inventing an answer.

### Missing business data

Missing values are handled safely and relevant data-quality limitations can be surfaced.

### Unexpected data types

Analytics functions are defensive against values such as:

```text
None
NaN
pd.NA
integers
floats
strings
percentages
unexpected values
```

---

# Security Considerations

The application uses environment variables for sensitive credentials:

```text
MONDAY_API_TOKEN
DEALS_BOARD_ID
WORK_ORDERS_BOARD_ID
GEMINI_API_KEY
```

Secrets are excluded from Git using `.gitignore`.

Before pushing changes:

```bash
git status
```

Verify that `.env` is not listed.

---

# Future Improvements

Potential future extensions include:

* Historical business trend analysis
* Revenue forecasting
* Predictive pipeline forecasting
* Automated anomaly detection
* Scheduled executive reports
* Risk alerts
* Role-based access control
* Authentication
* Production caching/database layer
* Advanced semantic search
* More sophisticated entity resolution
* LLM evaluation pipelines
* Streaming AI responses
* Automated business alerts

---

# Assignment Deliverables

This project was developed as part of the **Skylark Drones Monday.com Business Intelligence Agent assignment**.

The implementation includes:

* Live Monday.com integration
* Deals and Work Orders analysis
* Data cleaning and normalization
* Natural-language query understanding
* Deterministic business analytics
* Cross-board sector analysis
* Google Gemini integration
* Numerical hallucination protection
* Rule-based fallback
* Conversational follow-ups
* Executive-level insights
* Interactive Streamlit dashboard
* Automated test coverage
* Architecture and design documentation

---

# Links

### Live Application

[https://skylark-bi-agent-kuatxs6sq3uxbncst2r2ae.streamlit.app/](https://skylark-bi-agent-kuatxs6sq3uxbncst2r2ae.streamlit.app/)

### GitHub Repository

[https://github.com/pmanojkumar1009/skylark-bi-agent](https://github.com/pmanojkumar1009/skylark-bi-agent)

### Author

**Manojkumar**

GitHub:
[https://github.com/pmanojkumar1009](https://github.com/pmanojkumar1009)

---

# Project Highlights

```text
┌─────────────────────────────────────────────┐
│             SKYLARK BI                      │
├─────────────────────────────────────────────┤
│                                             │
│  Live Monday.com Business Data              │
│              ↓                              │
│  Deterministic Python Analytics             │
│              ↓                              │
│  Verified Business Metrics                  │
│              ↓                              │
│  Google Gemini Reasoning                    │
│              ↓                              │
│  Numerical Safety Validation                │
│              ↓                              │
│  Executive Decision Intelligence            │
│                                             │
└─────────────────────────────────────────────┘
```
