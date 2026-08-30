"""
Skylark BI Query Engine
=======================
Deterministic intent router and analytics executor.

Translates natural language questions — including founder/CEO conversational phrasing —
into structured analytics intents and executes verifiable calculations over live
Monday.com Deals and Work Orders data.
"""

import re
from typing import Dict, Any, Optional, List
import pandas as pd

from app.analytics import (
    get_pipeline_summary,
    get_pipeline_by_sector,
    get_pipeline_by_stage,
    get_deal_status_summary,
    get_work_order_summary,
    get_billing_summary,
    get_sector_performance,
    get_data_quality_summary,
    get_leadership_summary,
    normalize_sector,
    get_owner_performance,
    get_stale_deals,
    get_top_opportunities,
    get_priority_opportunities,
    get_business_health_summary,
    get_deterministic_insights,
    get_executive_recommendations,
    get_revenue_by_sector,
    get_customer_pipeline,
    get_operational_risk_summary,
    get_cross_board_risk_analysis,
)

# ── Canonical sector list ────────────────────────────────────────────────────
KNOWN_SECTORS = [
    "Mining", "Renewables", "Powerline", "Railways",
    "Construction", "Aviation", "Dsp", "Tender", "Manufacturing",
    "Security And Surveillance", "Others"
]


# ── Helper: extract all sectors mentioned in query ────────────────────────────
def _extract_all_sectors(q: str) -> List[str]:
    found = []
    q_low = q.lower()
    # Normalize sector synonyms
    if any(k in q_low for k in ["energy", "solar", "wind", "renewable", "renewables"]):
        if "Renewables" not in found:
            found.append("Renewables")
    if "powerline" in q_low or "power line" in q_low:
        if "Powerline" not in found:
            found.append("Powerline")
    if "mining" in q_low or "mine" in q_low or "mines" in q_low:
        if "Mining" not in found:
            found.append("Mining")
    if any(k in q_low for k in ["railway", "railways", "rail"]):
        if "Railways" not in found:
            found.append("Railways")
    if "construction" in q_low:
        if "Construction" not in found:
            found.append("Construction")
    if "aviation" in q_low or "drone" in q_low:
        if "Aviation" not in found:
            found.append("Aviation")
    if "dsp" in q_low:
        if "Dsp" not in found:
            found.append("Dsp")
    if "tender" in q_low or "tenders" in q_low:
        if "Tender" not in found:
            found.append("Tender")
    if "manufacturing" in q_low:
        if "Manufacturing" not in found:
            found.append("Manufacturing")
    if "surveillance" in q_low or "security" in q_low:
        if "Security And Surveillance" not in found:
            found.append("Security And Surveillance")
    if "telecom" in q_low:
        if "Others" not in found:
            found.append("Others")

    # Direct search for known sector names
    for s in KNOWN_SECTORS:
        pattern = r"\b" + re.escape(s.lower()) + r"\b"
        if re.search(pattern, q_low) and s not in found:
            found.append(s)

    return found


def _extract_first_sector(q: str) -> Optional[str]:
    sectors = _extract_all_sectors(q)
    return sectors[0] if sectors else None


def _matches_any(q: str, keywords: List[str]) -> bool:
    return any(kw in q for kw in keywords)


# ── Primary rule-based intent detector ───────────────────────────────────────

def rule_based_intent_detector(query: str) -> Dict[str, Any]:
    """
    Deterministic semantic intent classifier.
    Understands human founder questions and maps to correct analytics intent.
    Uses multi-signal contextual categorization rather than fragile exact phrases.
    """
    q = query.lower().strip()
    matched_sectors = _extract_all_sectors(q)
    first_sector = matched_sectors[0] if matched_sectors else None

    # ── 1. Conversational Follow-up Shorthands ─────────────────────────────────
    if q in [
        "why", "why?", "why is that", "why is that?", "tell me more", "tell me more.",
        "explain", "explain why", "more details", "what changed", "what changed?",
        "how much is that", "how much is that?", "what should we do", "what should we do?",
        "why tender?", "why is tender so high?", "why does tender dominate the pipeline?",
        "what makes it so high?", "how come?", "where is it concentrated?", "where are they concentrated?",
        "why these?", "what is driving the risk?", "which one is riskier?", "which is riskier?",
        "why is that?",
    ]:
        return {
            "intent": "follow_up",
            "sector": first_sector,
            "clarification_question": None,
        }

    if q.startswith("what about ") or q.startswith("how about ") or q.startswith("and "):
        if first_sector:
            return {
                "intent": "sector_performance",
                "sector": first_sector,
                "clarification_question": None,
            }

    # ── 2. Explicit Comparison Queries ─────────────────────────────────────────
    if "compare" in q or "comparison" in q or " vs " in q or " versus " in q:
        return {
            "intent": "compare_sectors",
            "sector": None,
            "compare_sectors": matched_sectors,
            "clarification_question": None,
        }

    # ── 3. Cross-Board Analysis (Compound sales + operations / risks) ──────────
    if _matches_any(q, [
        "sales and operations", "deals and work orders", "cross-board", "cross board",
        "keeping up with sales", "operations keeping up", "risks across", "biggest risks across",
        "strongest pipeline but", "high pipeline and", "pipeline but also",
        "strong sales potential but operational", "are operations keeping up",
    ]):
        return {
            "intent": "cross_board_analysis",
            "sector": None,
            "compare_sectors": matched_sectors,
            "clarification_question": None,
        }

    # ── 4. Customer / Client Analysis ──────────────────────────────────────────
    if _matches_any(q, [
        "customer", "customers", "client", "clients", "account", "accounts",
        "which customer", "which client", "biggest customer", "largest customer",
        "which customers have the largest", "customer pipeline", "most revenue customer",
        "which customers should i be paying attention to", "which customers or sectors are creating collection risk",
    ]):
        return {
            "intent": "customer_analysis",
            "sector": first_sector,
            "clarification_question": None,
        }

    # ── 5. Pipeline & Deal Risk Analysis (At-risk, Stale, Stuck Deals) ────────
    if _matches_any(q, [
        "pipeline risk", "pipeline risks", "risk in pipeline", "risks in our pipeline",
        "risks in pipeline", "risky deals", "deals at risk", "stale deals", "stale deal",
        "deals stuck", "stuck deals", "deals are stale", "which opportunities are risky",
        "which deals are risky", "which opportunities look risky",
    ]):
        return {
            "intent": "deal_risk_analysis",
            "sector": first_sector,
            "clarification_question": None,
        }

    # ── 6. Operational Risk & Delay Analysis ──────────────────────────────────
    # Check for delivery issues, stuck work orders, operational problems FIRST
    has_ops_word = any(w in q for w in ["operation", "operations", "operational", "delivery", "deliveries", "work order", "work orders", "workorder", "workorders", "project", "projects", "execution", "completion rate"])
    # Extended risk signal: includes concern/worry phrasing used in executive questions
    has_risk_word = any(w in q for w in [
        "problem", "problems", "issue", "issues", "risk", "risks", "trouble",
        "stuck", "paused", "delayed", "delay", "delays", "behind", "falling behind",
        "overdue", "bottleneck", "bottlenecks", "struggling", "late",
        "worried", "worry", "concern", "concerned", "wrong", "going wrong",
        "should i be", "anything wrong", "anything bad", "at risk",
    ])

    if has_ops_word and has_risk_word:
        if any(w in q for w in ["delayed", "delay", "delays", "behind", "overdue", "late"]):
            return {
                "intent": "delay_analysis",
                "sector": first_sector,
                "clarification_question": None,
            }
        return {
            "intent": "operational_risk",
            "sector": first_sector,
            "clarification_question": None,
        }

    # Explicit concern/executive phrasing that should also route to operational_risk
    # even when ops words are implied rather than present
    if _matches_any(q, [
        "operational problems", "delivery issues", "delivery problem", "delivery problems",
        "is anything stuck", "projects falling behind", "projects are falling behind",
        "projects delayed", "delayed projects", "operational bottlenecks", "operational bottleneck",
        "which sector has the highest operational risk", "which sector is struggling",
        "operational risk", "delivery risk", "stuck work order", "stuck work orders",
        "pause / struck", "paused projects", "paused work", "what's going wrong with delivery",
        "execution risks", "any projects stuck",
        # Concern-phrased executive questions
        "should i be worried", "anything on the operations side", "going wrong operationally",
        "operations side", "are operations okay", "are we okay operationally",
        "should i be concerned about operations", "are we having delivery",
        "are there any operational", "what's happening on the operations",
        "is operations on track", "are operations on track", "are deliveries on track",
        "how are deliveries going", "are we delivering on time",
    ]):
        return {
            "intent": "operational_risk",
            "sector": first_sector,
            "clarification_question": None,
        }

    # ── 7. Sector Pipeline Ranking (Where/Which Sector has most pipeline/opportunity) ─
    if _matches_any(q, [
        "where are we seeing most", "where is most of our", "where are we strongest",
        "which sector has the biggest", "which sector has the largest", "which sector has the most",
        "which sector has the highest", "who has the biggest pipeline", "who has the largest pipeline",
        "biggest pipeline by sector", "top sector by pipeline", "biggest pipeline", "largest pipeline",
        "most pipeline", "strongest pipeline", "strongest sales pipeline", "which sector is doing best",
        "which industry has the most pipeline", "which industry has the most business",
        "sector with highest pipeline", "sector with biggest pipeline",
        "which sector is performing best", "which sector is best", "which vertical is strongest",
        "which part of the business is doing best", "where do we have the most upside",
    ]):
        if first_sector and not any(kw in q for kw in ["which sector", "who has", "where is", "by sector", "industry", "where are we seeing most", "doing best", "performing best"]):
            return {
                "intent": "pipeline_by_sector",
                "sector": first_sector,
                "clarification_question": None,
            }
        return {
            "intent": "sector_pipeline_ranking",
            "sector": None,
            "clarification_question": None,
        }

    # ── 8. Top Deals & Key Opportunities (Specific high-value items) ──────────
    if _matches_any(q, ["how many deals", "how many are open", "how many open deals", "number of open deals", "count of open deals"]):
        return {
            "intent": "pipeline_summary",
            "sector": None,
            "clarification_question": None,
        }

    has_deal_word = any(w in q for w in ["deal", "deals", "opportunity", "opportunities", "prospect", "prospects"])
    if has_deal_word or _matches_any(q, [
        "what should i pay attention to", "pay attention to", "worth watching",
        "which should i watch", "which opportunities are worth", "biggest opportunities",
        "show me our biggest opportunities", "what's our biggest opportunity",
        "what is our biggest opportunity", "key opportunities", "top opportunities",
        "biggest open deals", "top open deals", "largest open deals", "show me the biggest open deals",
        "which opportunities are most important", "which deals need my attention", "which opportunities need my attention",
        "show me important deals", "show me the biggest opportunities",
        "most important for us to win", "important for us to win right now",
    ]):
        if any(w in q for w in ["risky", "risk", "risks", "stuck", "stale", "falling through", "at risk", "at-risk", "lost"]):
            return {
                "intent": "deal_risk_analysis",
                "sector": first_sector,
                "clarification_question": None,
            }

        # Check for Business Priority inquiries (importance, win right now, attention, priority)
        if _matches_any(q, [
            "most important", "win right now", "important for us to win",
            "pay attention to", "need my attention", "focus on", "prioritize",
            "critical to win", "critical deals", "which deals are most critical",
            "most important to close", "key deals to close", "where should sales focus",
        ]):
            return {
                "intent": "priority_opportunities",
                "sector": first_sector,
                "clarification_question": None,
            }

        return {
            "intent": "top_deals",
            "sector": first_sector,
            "clarification_question": None,
        }

    # ── 9. Operations Overview ────────────────────────────────────────────────
    if has_ops_word or _matches_any(q, [
        "how are operations doing", "how are operations", "what's happening operationally",
        "what is happening operationally", "ops summary", "operations summary",
        "delivery status", "operational delivery", "completion rate", "what's our completion rate",
        "what is our completion rate",
    ]):
        if first_sector:
            return {
                "intent": "sector_performance",
                "sector": first_sector,
                "clarification_question": None,
            }
        return {
            "intent": "work_order_summary",
            "sector": None,
            "clarification_question": None,
        }

    # ── 10. Finance, Receivables & Collections ─────────────────────────────────
    if _matches_any(q, [
        "money", "cash", "payment", "payments", "receivable", "receivables",
        "collection", "collections", "collected", "collect", "how much have we collected",
        "billing", "billed", "invoice", "invoicing", "unpaid", "outstanding",
        "waiting to collect", "where is our money stuck", "are customers paying us",
        "how healthy are collections", "how are collections", "what's happening financially",
        "financial", "finance", "cash flow", "how much are we waiting to collect",
        "which sector has the biggest receivables", "which sector has the largest receivables",
        "where is our cash stuck", "how much money are customers yet to pay", "how much are we owed",
        "where are receivables concentrated",
    ]):
        if first_sector:
            return {
                "intent": "sector_performance",
                "sector": first_sector,
                "clarification_question": None,
            }
        return {
            "intent": "billing_summary",
            "sector": None,
            "clarification_question": None,
        }

    # ── 9. Closed-Won Revenue Analysis ─────────────────────────────────────────
    if _matches_any(q, [
        "how much have we won", "how much revenue have we won", "what is our closed revenue",
        "closed revenue", "won revenue", "closed won revenue", "closed won value",
        "how much business have we successfully closed", "how much business have we won",
        "which sector generated the most revenue", "which sector generated most revenue",
        "generated the most revenue", "most revenue", "highest revenue", "biggest revenue",
        "revenue by sector", "total won revenue", "revenue generated",
    ]):
        return {
            "intent": "revenue_analysis",
            "sector": first_sector,
            "clarification_question": None,
        }

    # ── 11. Data Governance & Data Quality ────────────────────────────────────
    if _matches_any(q, [
        "data quality", "data-quality", "missing values", "missing data",
        "caveat", "caveats", "anomaly", "anomalies", "quality issues",
        "data completeness", "show me data quality", "data quality issues",
        "how good is our data", "can i trust the pipeline numbers", "can i trust the data",
        "can we trust this pipeline", "can we trust the pipeline", "can we trust this data",
        "can we trust", "can i trust", "what's missing from the data", "what is missing from the data",
        "are there data quality problems", "how complete is our crm", "are probabilities missing",
        "missing probabilities", "how many deals are missing values", "can we trust the pipeline number",
    ]):
        return {
            "intent": "data_quality",
            "sector": None,
            "clarification_question": None,
        }

    # ── 12. Named Sector Performance (e.g. "How is Mining doing?", "Why is Renewables a concern?")
    if first_sector:
        if _matches_any(q, ["pipeline", "funnel", "quarter", "month", "deals", "opportunity"]):
            return {
                "intent": "pipeline_by_sector",
                "sector": first_sector,
                "clarification_question": None,
            }
        return {
            "intent": "sector_performance",
            "sector": first_sector,
            "clarification_question": None,
        }

    # ── 13. General Pipeline & Sales Queries ──────────────────────────────────
    if _matches_any(q, [
        "pipeline", "how is our pipeline", "how's our pipeline", "how is the pipeline",
        "how's the pipeline", "pipeline looking", "pipeline overview", "give me the overview of the pipeline",
        "how much business is currently open", "how much could we potentially close",
        "weighted pipeline", "what is our weighted pipeline", "what is the weighted pipeline",
        "realistic value of the pipeline", "how many deals are open", "how many deals are currently open",
        "how many are open", "how many are still open", "what's going on with sales",
        "what is our open pipeline", "active pipeline", "total pipeline", "what's happening with sales",
        "what is happening with sales", "sales update", "how much open business",
        "is our pipeline healthy", "how strong is our pipeline", "do we have enough pipeline",
        "are sales healthy", "sales healthy", "likely to close", "actually likely to close",
        "how much of the pipeline is actually likely to close", "how much of our pipeline will close",
    ]):
        return {
            "intent": "pipeline_summary",
            "sector": None,
            "clarification_question": None,
        }

    # ── 14. Executive Briefing (Founder / CEO High-Level Briefing) ────────────
    # Recognizes founder/CEO role, quick time constraints, or broad state of the business
    has_exec_role = any(r in q for r in ["founder", "ceo", "leadership", "executive", "board", "management", "president"])
    has_quick_time = any(t in q for t in ["2 minutes", "two minutes", "1 minute", "one minute", "30 seconds", "quick", "in a nutshell", "brief"])
    has_biz_overview = any(b in q for b in [
        "how's the business doing", "how is the business doing", "how are things looking",
        "how are we doing", "give me a quick update", "what's happening in the business",
        "what is happening in the business", "what's happening in the company", "state of the business",
        "three most important things", "3 most important things", "most important things",
        "things i need to know", "things should know", "overview of the business",
        "tell the founders", "update for the leadership", "leadership update",
        "leadership briefing", "executive briefing", "executive overview", "give me the quick version",
        "top 5 things i should know", "top 5 things", "what's going well and what isn't",
        "what is happening right now", "what's happening right now", "what's happening",
        "what would you tell the board", "tell the board", "how is the business performing",
        "where are we right now", "give me the business overview",
    ])

    if has_biz_overview or (has_exec_role and (has_quick_time or "know" in q or "update" in q or "business" in q)):
        return {
            "intent": "executive_briefing",
            "sector": None,
            "clarification_question": None,
        }

    # ── 15. Executive Priorities / Strategic Weekly Focus ─────────────────────
    if _matches_any(q, [
        "focus", "priorities", "priority", "what should i focus on", "what should i personally focus on",
        "where should i focus", "where should leadership focus", "what needs my attention",
        "needs attention", "what should i worry about", "what's worrying you", "what would you worry about",
        "what's keeping leadership up", "anything i should worry about", "is there anything i should worry about",
        "anything i should be worried about", "what are the biggest problems right now",
        "biggest problems right now", "biggest problems in the business", "what's the biggest problem",
        "what are the biggest problems", "where are we weakest", "where are we losing money",
        "where are we losing the most money", "what should leadership focus on", "where should we focus",
        "if you were me, what would you focus on", "if you were me", "where should i put my attention",
        "where should we put our attention", "what's keeping me up at night", "keeping me up at night",
        "what are the biggest business risks right now", "biggest business risks", "where are we exposed",
    ]):
        return {
            "intent": "executive_priorities",
            "sector": None,
            "clarification_question": None,
        }

    # ── 16. Business Health Score ─────────────────────────────────────────────
    if _matches_any(q, [
        "business health", "health score", "sales health", "operations health",
        "finance health", "overall health score", "how healthy is the business",
        "are we doing okay", "are we doing well",
    ]):
        return {
            "intent": "business_health",
            "sector": None,
            "clarification_question": None,
        }

    # ── 17. Deal Stage / Status Distribution ──────────────────────────────────
    if _matches_any(q, ["deal stage", "pipeline by stage", "stage distribution", "by stage"]):
        return {
            "intent": "pipeline_by_stage",
            "sector": None,
            "clarification_question": None,
        }

    if _matches_any(q, ["deal status", "status analysis", "status distribution", "win loss", "win rate"]):
        return {
            "intent": "deal_status_analysis",
            "sector": None,
            "clarification_question": None,
        }

    # ── 18. Broad Business Questions Fallback (Default to Executive Briefing) ─
    if any(w in q for w in ["business", "company", "update", "doing", "going on", "status", "summary", "overview"]):
        return {
            "intent": "executive_briefing",
            "sector": None,
            "clarification_question": None,
        }

    # ── 19. Genuinely Ambiguous Query ─────────────────────────────────────────
    return {
        "intent": "clarify",
        "sector": None,
        "clarification_question": (
            "Could you clarify which business area you are interested in? "
            "For example: pipeline, closed revenue, top deals, sector performance, "
            "work orders, billing, data quality, or a specific sector like Mining or Renewables."
        ),
    }


# ── Intent execution ──────────────────────────────────────────────────────────

def execute_intent(
    intent: str,
    sector: Optional[str],
    deals_df: pd.DataFrame,
    work_orders_df: pd.DataFrame,
    extra: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Execute deterministic analytics for the given intent.
    Guarantees that all metrics are computed accurately from live data.
    """
    extra = extra or {}

    # ── Pipeline Summary ──────────────────────────────────────────────────────
    if intent == "pipeline_summary":
        return get_pipeline_summary(deals_df)

    # ── Sector Pipeline Ranking (Strictly uses active OPEN pipeline) ───────────
    elif intent in ("sector_pipeline_ranking",):
        results = get_pipeline_by_sector(deals_df)
        # Sort strictly by open_pipeline_value descending
        results_sorted = sorted(results, key=lambda x: (x.get("open_pipeline_value", 0), x.get("portfolio_value", 0)), reverse=True)
        total_open = sum(r.get("open_pipeline_value", 0) for r in results_sorted)
        for r in results_sorted:
            r["share_pct"] = round(r.get("open_pipeline_value", 0) / total_open * 100, 1) if total_open > 0 else 0.0
        return {
            "ranked_sectors": results_sorted,
            "top_sector": results_sorted[0]["sector"] if results_sorted else "N/A",
            "top_sector_value": results_sorted[0]["open_pipeline_value"] if results_sorted else 0.0,
            "total_open_pipeline": total_open,
        }

    # ── Pipeline by Sector ────────────────────────────────────────────────────
    elif intent in ("pipeline_by_sector", "pipeline_health"):
        results = get_pipeline_by_sector(deals_df)
        if sector:
            norm = sector.strip().title()
            filtered = [r for r in results if r["sector"].lower() == norm.lower()]
            if filtered:
                return filtered[0]
            return {
                "sector": sector,
                "deal_count": 0,
                "portfolio_value": 0.0,
                "open_deal_count": 0,
                "open_pipeline_value": 0.0,
                "avg_closure_probability": 0.0,
                "weighted_pipeline_value": 0.0,
                "message": f"No deals found for sector '{sector}'."
            }
        return {"sectors": results}

    elif intent == "pipeline_by_stage":
        return {"stages": get_pipeline_by_stage(deals_df)}

    # ── Revenue Analysis (Closed-Won) ─────────────────────────────────────────
    elif intent == "revenue_analysis":
        return get_revenue_by_sector(deals_df, sector)

    # ── Top Deals / Key Opportunities ─────────────────────────────────────────
    elif intent in ("top_deals", "top_opportunities"):
        limit = extra.get("limit", 10)
        return {"opportunities": get_top_opportunities(deals_df, limit=limit)}

    elif intent == "priority_opportunities":
        limit = extra.get("limit", 10)
        return {"opportunities": get_priority_opportunities(deals_df, limit=limit)}

    elif intent == "deal_status_analysis":
        return {"statuses": get_deal_status_summary(deals_df)}

    elif intent in ("deal_risk_analysis", "stale_deals"):
        import datetime
        return {"stale_deals": get_stale_deals(deals_df, reference_date=datetime.date.today())}

    elif intent == "customer_analysis":
        return get_customer_pipeline(deals_df)

    # ── Operations ────────────────────────────────────────────────────
    elif intent == "work_order_summary":
        return get_work_order_summary(work_orders_df)

    elif intent in ("operational_risk", "delay_analysis"):
        return get_operational_risk_summary(work_orders_df, sector)

    # ── Finance ───────────────────────────────────────────────────────────────
    elif intent == "billing_summary":
        return get_billing_summary(work_orders_df)

    # ── Sector Performance / Comparisons ──────────────────────────────────────
    elif intent == "sector_performance":
        results = get_sector_performance(deals_df, work_orders_df)
        if sector:
            norm = sector.strip().title()
            filtered = [r for r in results if r["sector"].lower() == norm.lower()]
            if filtered:
                return filtered[0]
            return {
                "sector": sector,
                "deals": {"count": 0, "portfolio_value": 0.0, "open_count": 0,
                          "active_count": 0, "open_pipeline_value": 0.0, "weighted_pipeline_value": 0.0},
                "work_orders": {"count": 0, "order_value_excl_gst": 0.0, "billed_value_excl_gst": 0.0,
                                "receivables": 0.0, "execution_status_distribution": {}},
                "message": f"No data found for sector '{sector}'.",
            }
        return {"sectors": results}

    elif intent == "compare_sectors":
        all_sectors = get_sector_performance(deals_df, work_orders_df)
        compare_list = extra.get("compare_sectors", [])
        if compare_list:
            norm_list = [s.lower() for s in compare_list]
            filtered = [s for s in all_sectors if s["sector"].lower() in norm_list]
            return {"sectors": filtered if filtered else all_sectors}
        return {"sectors": all_sectors}

    elif intent == "cross_board_analysis":
        return get_cross_board_risk_analysis(deals_df, work_orders_df)

    # ── Executive Briefing & Decision Intelligence ────────────────────────────
    elif intent in ("executive_briefing", "leadership_summary"):
        return get_leadership_summary(deals_df, work_orders_df)

    elif intent == "executive_priorities":
        return {"recommendations": get_executive_recommendations(deals_df, work_orders_df)}

    elif intent == "business_health":
        return get_business_health_summary(deals_df, work_orders_df)

    # ── Data Governance ───────────────────────────────────────────────────────
    elif intent == "data_quality":
        return get_data_quality_summary(deals_df, work_orders_df)

    # ── Clarification ─────────────────────────────────────────────────────────
    elif intent == "clarify":
        return {
            "clarification_question": (
                "Could you clarify which business area you are interested in? "
                "For example: pipeline, closed revenue, top deals, sector performance, "
                "work orders, billing, data quality, or a specific sector like Mining or Renewables."
            )
        }

    else:
        return {"error": f"Intent '{intent}' not recognized. Please rephrase your question."}


# ── Analytics context formatter ───────────────────────────────────────────────

def format_analytics_context(intent: str, results: Dict[str, Any]) -> str:
    """
    Serialize deterministic analytics output into a structured prompt context block.
    """
    import json

    context = f"=== DETERMINISTIC CALCULATION RESULTS (INTENT: {intent.upper()}) ===\n"
    context += json.dumps(results, indent=2, default=str)
    context += "\n=================================================================\n"
    context += (
        "\nANALYTICAL POLICIES:\n"
        "- Weighted pipeline values are ESTIMATES using: High=80%, Medium=50%, Low=20%.\n"
        "- Open deals missing closure probability are treated as 0% weight.\n"
        "- All sums omit NaN/null values safely.\n"
        "- Currency is in Indian Rupees (INR). Format as ₹X.XXCr (crores) or ₹XX.XL (lakhs).\n"
        "- Numbers in response MUST match source metrics exactly — do NOT invent any figure.\n"
    )
    return context
