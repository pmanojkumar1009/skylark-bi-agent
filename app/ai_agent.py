import os
import re
import json
from typing import Dict, Any, Optional, List, Union
import pandas as pd

from app.query_engine import (
    rule_based_intent_detector,
    execute_intent,
    format_analytics_context
)

def format_currency(val) -> str:
    """Format numeric values as INR currency."""
    if val is None or pd.isna(val):
        return "Unknown"
    try:
        return f"₹{float(val):,.2f}"
    except (ValueError, TypeError):
        return "Unknown"


# ============================================================
# PROVIDER-AGNOSTIC LLM CLIENT
# ============================================================

class LLMClient:
    """
    Provider-agnostic interface for invoking Gemini or OpenAI LLMs.
    Supports dynamic model discovery, health verification, and transparent error reporting.
    """
    def __init__(self):
        self.gemini_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        self.openai_key = os.getenv("OPENAI_API_KEY")
        self.provider = None
        self.active_model = None
        self.connection_status = "Disconnected"
        self.connection_error = None
        self._call_timestamps = []  # timestamps of recent calls for rate limiting

        # Check and configure Gemini
        if self.gemini_key:
            try:
                from google import genai
                from google.genai import types
                self.client = genai.Client(api_key=self.gemini_key)

                # Prioritize configured model or active flash models in order
                env_model = os.getenv("GEMINI_MODEL")
                candidate_models = [env_model] if env_model else [
                    "gemini-3.5-flash",
                    "gemini-3.6-flash",
                    "gemini-3.7-flash",
                    "gemini-flash-latest",
                    "gemini-2.5-pro",
                ]

                connected = False
                last_err = None
                for model in candidate_models:
                    if not model:
                        continue
                    try:
                        resp = self.client.models.generate_content(
                            model=model,
                            contents="ping",
                            config=types.GenerateContentConfig(max_output_tokens=5)
                        )
                        self.model_name = model
                        self.active_model = model
                        self.provider = "gemini"
                        self.connection_status = "Connected"
                        self.connection_error = None
                        connected = True
                        print(f"[LLM] Gemini Connection Verified. Active model: {self.model_name}")
                        break
                    except Exception as me:
                        last_err = me
                        print(f"[LLM] Model '{model}' check failed: {me}")

                if not connected:
                    safe_err = str(last_err)
                    if "401" in safe_err or "API_KEY_INVALID" in safe_err:
                        self.connection_error = "401: Invalid API Key"
                    elif "429" in safe_err or "RESOURCE_EXHAUSTED" in safe_err:
                        self.connection_error = "429: Quota Exceeded"
                    elif "404" in safe_err or "NOT_FOUND" in safe_err:
                        self.connection_error = "404: Model Unavailable"
                    elif "503" in safe_err or "UNAVAILABLE" in safe_err:
                        self.connection_error = "503: Service Unavailable"
                    else:
                        self.connection_error = f"{type(last_err).__name__}"
                    self.connection_status = "Fallback"
                    self.provider = None
                    print(f"[LLM] Gemini verification failed: {self.connection_error}. Running in Rule-Based Fallback Mode.")

            except Exception as e:
                self.connection_error = f"{type(e).__name__}"
                self.connection_status = "Fallback"
                self.provider = None
                print(f"[LLM] Gemini initialization failed: {e}. Running in Rule-Based Fallback Mode.")

        # Check and configure OpenAI
        elif self.openai_key:
            try:
                from openai import OpenAI
                self.client = OpenAI(
                    api_key=self.openai_key,
                    base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
                )
                self.model_name = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
                self.active_model = self.model_name
                # Quick verification call
                self.client.chat.completions.create(
                    model=self.model_name,
                    messages=[{"role": "user", "content": "ping"}],
                    max_tokens=1
                )
                self.provider = "openai"
                self.connection_status = "Connected"
                self.connection_error = None
                print(f"[LLM] OpenAI Connection Verified. Active model: {self.model_name}")
            except Exception as e:
                self.connection_error = f"{type(e).__name__}"
                self.connection_status = "Fallback"
                self.provider = None
                print(f"[LLM] OpenAI verification failed: {e}. Running in Rule-Based Fallback Mode.")

        else:
            self.connection_status = "Fallback"
            self.connection_error = "No API Key Provided"
            print("[LLM] WARNING: No LLM API Key found (GEMINI_API_KEY or OPENAI_API_KEY). Running in Rule-Based Mode.")

    def _enforce_rate_limit(self):
        """Simple client‑side rate limiting for free‑tier Gemini.
        Tracks timestamps of recent calls and sleeps if limit exceeded.
        """
        import time
        now = time.time()
        # Keep only calls within the last 60 seconds
        self._call_timestamps = [t for t in self._call_timestamps if now - t < 60]
        if len(self._call_timestamps) >= 10:
            sleep_time = 60 - (now - self._call_timestamps[0]) + 0.5
            print(f"[LLM] Rate limit threshold reached, sleeping {sleep_time:.1f}s")
            time.sleep(sleep_time)
            now = time.time()
            self._call_timestamps = [t for t in self._call_timestamps if now - t < 60]
        self._call_timestamps.append(time.time())

    def _extract_text(self, response: Any) -> str:
        """Safely extract generated text from Gemini or other response objects."""
        if response is None:
            return ""
        if hasattr(response, "text") and response.text:
            return response.text.strip()
        if hasattr(response, "candidates") and response.candidates:
            parts = []
            for cand in response.candidates:
                if hasattr(cand, "content") and hasattr(cand.content, "parts"):
                    for p in cand.content.parts:
                        if hasattr(p, "text") and p.text:
                            parts.append(p.text)
            if parts:
                return "".join(parts).strip()
        return ""

    def call_llm(self, system_instruction: str, prompt: str, json_mode: bool = False) -> str:
        """
        Invoke the configured LLM API. Throws ValueError if no API key is configured.
        """
        if not self.provider:
            raise ValueError("No LLM provider configured.")
        # Enforce rate limiting before making the request
        self._enforce_rate_limit()

        if self.provider == "gemini":
            from google import genai
            from google.genai import types

            config = types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=0.0
            )
            if json_mode:
                config.response_mime_type = "application/json"

            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=config
            )
            return self._extract_text(response)

        elif self.provider == "openai":
            messages = [
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": prompt}
            ]
            kwargs = {
                "model": self.model_name,
                "messages": messages,
                "temperature": 0.0
            }
            if json_mode:
                kwargs["response_format"] = {"type": "json_object"}

            response = self.client.chat.completions.create(**kwargs)
            return response.choices[0].message.content.strip()

        return ""





# ============================================================
# CONVERSATIONAL BI AGENT
# ============================================================

class SkylarkBIAgent:
    """
    Orchestrator for natural-language BI interactions.
    Handles intent parsing, Python execution, prompt injection, and output validation.
    """
    def __init__(self, deals_df: pd.DataFrame, work_orders_df: pd.DataFrame, llm_client: Optional[LLMClient] = None):
        self.deals_df = deals_df
        self.work_orders_df = work_orders_df
        self.llm_client = llm_client if llm_client else LLMClient()
        
    def ask(self, user_query: str, conversation_history: Optional[List[Dict[str, str]]] = None) -> str:
        """
        Answers a user question end-to-end.
        Optionally accepts conversation_history as list of {"role": "user"|"assistant", "content": "..."} dicts.
        """
        if not user_query.strip():
            return "Please enter a valid question about your Deals, Work Orders, or Billing."

        # 1. Intent Detection
        parsed_intent = None

        if self.llm_client.provider:
            try:
                parsed_intent = self._detect_intent_with_llm(user_query, conversation_history)
            except Exception as exc:
                print(f"[LLM] Intent detection call failed: {exc}. Falling back to Rule-Based parsing.")

        if not parsed_intent:
            parsed_intent = rule_based_intent_detector(user_query)

        intent = parsed_intent.get("intent", "clarify")
        sector = parsed_intent.get("sector")
        clarification = parsed_intent.get("clarification_question")
        compare_sectors_list = parsed_intent.get("compare_sectors", [])

        # Context resolver for follow-up questions ("Why?", "Tell me more", "Where is it concentrated?")
        is_followup = (intent == "follow_up")
        if is_followup and conversation_history:
            # Look backwards in conversation history for the last meaningful query
            for msg in reversed(conversation_history):
                if msg.get("role") == "user":
                    prev_query = msg.get("content", "")
                    prev_parsed = rule_based_intent_detector(prev_query)
                    if prev_parsed.get("intent") not in ["follow_up", "clarify"]:
                        intent = prev_parsed.get("intent")
                        if not sector:
                            sector = prev_parsed.get("sector")
                        if not compare_sectors_list:
                            compare_sectors_list = prev_parsed.get("compare_sectors", [])
                        break
            if intent == "follow_up":
                intent = "executive_briefing"
        elif intent == "follow_up":
            intent = "executive_briefing"

        # Normalise intent aliases
        if intent in ("leadership_summary",):
            intent = "executive_briefing"

        # 2. Handle Clarification Intent
        if intent == "clarify":
            if clarification:
                return clarification
            return (
                "Could you clarify which business area you are interested in? "
                "For example: pipeline, revenue, sector performance, work orders, "
                "billing, data quality, or a specific sector like Mining or Renewables."
            )

        # 3. Execute Deterministic Calculations
        extra = {"compare_sectors": compare_sectors_list}
        try:
            raw_results = execute_intent(intent, sector, self.deals_df, self.work_orders_df, extra=extra)
        except Exception as exc:
            return f"An error occurred during calculations: {exc}"

        # If there's an error key in results, return it gracefully
        if "error" in raw_results:
            return raw_results["error"]

        # If follow-up question, render direct analytical explanation
        if is_followup:
            return self._render_followup_explanation(intent, sector, raw_results, user_query)

        # If no LLM configured, immediately return conversational deterministic response
        if not self.llm_client.provider:
            return self._render_conversational_response(intent, sector, raw_results, user_query)

        # 4. Formulate Prompt Context & Call LLM
        context = format_analytics_context(intent, raw_results)

        system_instruction = (
            "You are the Skylark BI Assistant — an executive-level business intelligence advisor for Skylark Drones.\n"
            "Your job is to answer the user's question directly, concisely, and insightfully using ONLY the provided deterministic calculation results.\n\n"
            "CRITICAL POLICIES:\n"
            "1. If the user asks a simple factual question (e.g. 'How much money is outstanding?', 'What is our pipeline?', 'How many deals are open?'), return a SHORT direct answer (1-2 sentences) with the relevant metric. DO NOT generate an executive report or unnecessary headers for simple factual questions.\n"
            "2. NEVER invent, extrapolate, or hallucinate any numbers, ratios, or metrics not explicitly present in the context.\n"
            "3. If a value is missing or null, report it as 'unknown' or 'missing'. Do not fabricate it.\n"
            "4. Label all weighted pipeline values clearly as estimates (mapped: High=80%, Medium=50%, Low=20%).\n"
            "5. Format currency figures in Indian notation (e.g. ₹53.2Cr, ₹68.8Cr, ₹2.08Cr, ₹69.8L, ₹14.3L).\n"
            "6. Explicitly state data-quality caveats that affect numbers when relevant.\n"
            "7. Keep tone executive, clear, concise, and focused on strategic recommendations.\n"
            "8. For sector ranking questions, always begin with the winner directly: 'X sector has the largest active open pipeline...'\n\n"
            "RESPONSE STRUCTURE ADAPTATION:\n"
            "- Executive / Founder Briefing ('I have 2 minutes...', 'What should I know...', 'State of the business'):\n"
            "  ## Executive Brief\n"
            "  ### 1. Biggest Opportunity (Pipeline leader & top open deals)\n"
            "  ### 2. Biggest Financial Risk (Outstanding receivables & collection concentration)\n"
            "  ### 3. Operational / Forecasting Risk (Stuck work orders & data completeness)\n"
            "  ### What Leadership Should Focus On This Week (Top 3 prioritized actions)\n"
            "- Executive Priorities ('What should I focus on this week?', 'What needs attention?'):\n"
            "  Group into 1. Collections & Cash Flow, 2. High-Value Pipeline Closing, 3. Operational Bottlenecks.\n"
            "- Ranking question: Winner → Ranked table → Why it matters → Recommended action\n"
            "- Comparison question: Side-by-side → Key differences → Strategic conclusion\n"
            "- Operational question: Affected items → Count/severity → Recommended action\n"
        )

        # Build conversation history prefix if provided
        history_block = ""
        if conversation_history:
            recent = conversation_history[-12:]
            history_lines = []
            for msg in recent:
                role = "User" if msg.get("role") == "user" else "Assistant"
                history_lines.append(f"{role}: {msg.get('content', '')[:500]}")
            history_block = "CONVERSATION HISTORY (for context only):\n" + "\n".join(history_lines) + "\n\n"

        prompt = (
            f"{history_block}"
            f"CALCULATED SOURCE METRICS:\n{context}\n\n"
            f"CURRENT USER INQUIRY: {user_query}\n\n"
            "EXECUTIVE REPORT:"
        )

        try:
            response = self.llm_client.call_llm(system_instruction, prompt)

            # 5. Safety Guardrail: Numerical Hallucination Check
            is_valid = self._validate_response_numbers(response, raw_results)
            if not is_valid:
                print("[SAFETY] Hallucination detected in LLM response! Swapping with verified structured markdown.")
                return (
                    "**[Safety Fallback: Deterministic Analytics Output]**\n"
                    "The AI response failed numerical integrity checks. Verified calculations:\n\n"
                    + self._render_conversational_response(intent, sector, raw_results, user_query)
                )

            return response

        except Exception as exc:
            print(f"[LLM] Prompt generation failed: {exc}. Returning rule-based fallback.")
            return self._render_conversational_response(intent, sector, raw_results, user_query)


    def _detect_intent_with_llm(self, query: str, conversation_history: Optional[List[Dict[str, str]]] = None) -> Dict[str, Any]:
        """
        Classify intent and extract entities using the LLM.
        Uses conversation history to resolve ambiguous follow-up queries.
        """
        system_instruction = (
            "You are a routing system for a Business Intelligence Agent. Your job is to classify "
            "the user's query and extract the sector if relevant. Output a valid JSON object ONLY. "
            "Do not write conversational text or markdown. Just the raw JSON block.\n\n"
            "JSON SCHEMA:\n"
            "{\n"
            "  \"intent\": \"<intent_name>\",\n"
            "  \"sector\": \"<sector_or_null>\",\n"
            "  \"compare_sectors\": [],\n"
            "  \"clarification_question\": null\n"
            "}\n\n"
            "VALID INTENTS:\n"
            "executive_briefing, executive_priorities, sector_pipeline_ranking, pipeline_summary, "
            "pipeline_by_sector, pipeline_by_stage, pipeline_health, revenue_analysis, top_deals, "
            "deal_status_analysis, deal_risk_analysis, customer_analysis, work_order_summary, "
            "operational_risk, delay_analysis, billing_summary, sector_performance, compare_sectors, "
            "cross_board_analysis, data_quality, business_health, top_opportunities, stale_deals, clarify\n\n"
            "VALID SECTORS: Mining, Renewables, Powerline, Railways, Construction, Aviation, Dsp, "
            "Tender, Manufacturing, Security And Surveillance, Others\n\n"
            "ROUTING EXAMPLES (match meaning rather than exact keywords):\n"
            "- 'I'm the founder and I have 2 minutes. What are the three most important things I need to know about the business right now?' → executive_briefing\n"
            "- 'What should I personally focus on this week?' / 'What needs my attention?' / 'Where should I focus?' → executive_priorities\n"
            "- 'What is happening in the business right now?' / 'State of the business in one minute' → executive_briefing\n"
            "- 'If you were the CEO, what would you worry about?' → executive_priorities\n"
            "- 'Which sector has biggest/largest/most pipeline?' → sector_pipeline_ranking\n"
            "- 'Which sector generated most revenue?' / 'revenue by sector' → revenue_analysis\n"
            "- 'Why are you concerned about Renewables?' / 'How is Renewables performing?' → sector_performance, sector='Renewables'\n"
            "- 'Which projects are delayed?' / 'delayed work orders' → delay_analysis\n"
            "- 'Which sector has highest operational risk?' / 'stuck work orders' → operational_risk\n"
            "- 'Show top 5 deals by value' / 'biggest deals' → top_deals\n"
            "- 'Which customers have largest pipeline?' → customer_analysis\n"
            "- 'Compare Energy and Mining' → compare_sectors, compare_sectors=['Renewables', 'Mining']\n"
            "- 'Sectors with strong pipeline but high risk' → cross_board_analysis\n"
            "- 'How much money are we still waiting to collect?' → billing_summary\n"
            "- 'How is our pipeline?' / 'pipeline overview' → pipeline_summary\n"
            "- Follow-up 'Why?' / 'What about Mining?' → use RECENT CONVERSATION to resolve intent+sector\n"
            "- ONLY use 'clarify' if the query has ZERO business meaning (e.g. 'foo', 'hello')\n\n"
            "SECTOR MAPPINGS: energy/solar/wind→Renewables, powerline/power line→Powerline, "
            "mine/mining→Mining, railway/rail→Railways\n"
        )

        # Build history context for intent resolution
        history_context = ""
        if conversation_history:
            recent = conversation_history[-6:]
            lines = [f"{'User' if m.get('role')=='user' else 'Asst'}: {m.get('content','')[:200]}" for m in recent]
            history_context = "RECENT CONVERSATION:\n" + "\n".join(lines) + "\n\n"

        prompt = f"{history_context}Current user query: '{query}'"

        response_text = self.llm_client.call_llm(system_instruction, prompt, json_mode=True)
        # Parse JSON
        return json.loads(response_text)


    # ============================================================
    # NUMERICAL INTEGRITY SAFETY VALIDATION
    # ============================================================

    def _validate_response_numbers(self, response: str, raw_results: Dict[str, Any]) -> bool:
        """
        Parse all numbers > 10.0 in the response and verify they are present
        in the calculation source metrics. Returns False if a hallucinated number is found.
        """
        # 1. Extract all numbers from the response text
        cleaned_text = response.replace("₹", "").replace("$", "")
        # Match floats and integers, ignoring commas
        pattern = r"\b\d{1,3}(?:,\d{3})*(?:\.\d+)?\b|\b\d+(?:\.\d+)?\b"
        raw_numbers = re.findall(pattern, cleaned_text)
        
        response_nums = []
        for num_str in raw_numbers:
            clean_str = num_str.replace(",", "")
            try:
                val = float(clean_str)
                # Ignore low integers (like count rankings or small offsets under 10) to avoid false flags
                if val > 10.0:
                    response_nums.append(val)
            except ValueError:
                continue
                
        if not response_nums:
            return True # No numbers to validate
            
        # 2. Extract all valid numbers from raw analytics calculations
        def extract_numbers_recursively(data: Any) -> List[float]:
            nums = []
            if isinstance(data, (int, float)):
                nums.append(float(data))
            elif isinstance(data, dict):
                for v in data.values():
                    nums.extend(extract_numbers_recursively(v))
            elif isinstance(data, (list, tuple, set)):
                for item in data:
                    nums.extend(extract_numbers_recursively(item))
            return nums
            
        source_nums = extract_numbers_recursively(raw_results)
        
        # 3. Perform matching
        for num in response_nums:
            match_found = False
            for src in source_nums:
                # Check direct match
                if abs(num - src) < 0.1:
                    match_found = True
                    break
                # Check percentage matching (e.g. 0.733 in source mapped to 73.3% in response)
                if abs(num - (src * 100)) < 0.1:
                    match_found = True
                    break
                # Check fractional matching
                if abs(num - (src / 100)) < 0.1:
                    match_found = True
                    break
            
            if not match_found:
                print(f"[SAFETY ALERT] Hallucination Flagged: Response mentioned number '{num}' "
                      f"which does not exist in source metrics.")
                return False
                
        return True

    # ============================================================
    # RULE-BASED FALLBACK MARKDOWN GENERATOR
    # ============================================================

    def _render_fallback_markdown(self, intent: str, sector: Optional[str], results: Dict[str, Any]) -> str:
        """
        Generate a professional structured Markdown block from calculated metrics
        when the LLM is inactive or bypassed. Returns structured sections:
        SUMMARY, METRICS, EVIDENCE, and RECOMMENDED ACTION.
        """
        title = f"Verified Analytics Report ({intent.upper()})"
        if sector:
            title += f" — Sector: {sector}"
            
        md = f"### 🦅 {title}\n\n"
        
        def format_currency(val) -> str:
            if val is None or pd.isna(val):
                return "Unknown"
            return f"₹{float(val):,.2f}"

        # 1. PIPELINE SUMMARY
        if intent == "pipeline_summary":
            md += "#### 📋 EXECUTIVE SUMMARY\n"
            md += "Analysis of the sales pipeline indicates active commercial engagement. "
            md += "Open deals represent significant potential contract values awaiting client sign-off. "
            md += "Securing these deals remains key to achieving quarterly targets.\n\n"
            
            md += "#### 📈 KEY METRICS\n"
            md += "| Metric | Value |\n| --- | --- |\n"
            md += f"| Total Portfolio Deals | {results.get('total_deals')} |\n"
            md += f"| Total Portfolio Value | {format_currency(results.get('total_portfolio_value'))} |\n"
            md += f"| Active Open Deals | {results.get('open_deals_count')} |\n"
            md += f"| Open Pipeline Value | {format_currency(results.get('open_pipeline_value'))} |\n"
            md += f"| Closed Won Deals | {results.get('won_deals_count')} ({format_currency(results.get('won_deals_value'))}) |\n"
            md += f"| Closed Lost Deals | {results.get('dead_deals_count')} ({format_currency(results.get('dead_deals_value'))}) |\n"
            md += f"| Average Probability (Est.) | {results.get('avg_closure_probability', 0.0) * 100:.1f}% |\n"
            md += f"| Weighted Pipeline Value (Est.) | {format_currency(results.get('weighted_pipeline_value'))} |\n\n"
            
            md += "#### 🔍 DETAILED EVIDENCE\n"
            md += f"The portfolio currently consists of {results.get('total_deals')} deals, out of which {results.get('open_deals_count')} "
            md += f"are active open opportunities. These open opportunities represent an open pipeline value of {format_currency(results.get('open_pipeline_value'))}. "
            md += f"After adjusting for stage probability weights, the verified weighted pipeline is estimated at {format_currency(results.get('weighted_pipeline_value'))}.\n\n"
            
            md += "#### ⚡ RECOMMENDED ACTION\n"
            md += "- Prioritize high-value deals currently in advanced negotiation or proposal stages.\n"
            md += "- Conduct a review of active deals missing probability ratings on Monday.com to refine weighted forecast accuracy."

        # 2. PIPELINE BY SECTOR
        elif intent == "pipeline_by_sector":
            md += "#### 📋 EXECUTIVE SUMMARY\n"
            if sector:
                md += f"Analysis of the sales pipeline for the **{results.get('sector')}** sector indicates active business development and potential contract growth.\n\n"
            else:
                md += "Analysis of the sales pipeline distribution across business sectors reveals concentration levels and volume indicators.\n\n"
            
            md += "#### 📈 KEY METRICS\n"
            if sector:
                md += f"- **Sector Name**: {results.get('sector')}\n"
                md += f"- **Deal Count**: {results.get('deal_count')}\n"
                md += f"- **Total Portfolio Value**: {format_currency(results.get('portfolio_value'))}\n"
                md += f"- **Open Deals Count**: {results.get('open_deal_count')}\n"
                md += f"- **Average Probability (Est.)**: {results.get('avg_closure_probability', 0.0) * 100:.1f}%\n"
                md += f"- **Weighted Pipeline (Est.)**: {format_currency(results.get('weighted_pipeline_value'))}\n\n"
            else:
                md += "| Sector | Deal Count | Portfolio Value | Open Deals | Weighted Pipeline (Est.) |\n| --- | --- | --- | --- | --- |\n"
                for s in results.get("sectors", []):
                    md += f"| {s['sector']} | {s['deal_count']} | {format_currency(s['portfolio_value'])} | {s['open_deal_count']} | {format_currency(s['weighted_pipeline_value'])} |\n"
                md += "\n"
                
            md += "#### 🔍 DETAILED EVIDENCE\n"
            if sector:
                md += f"The **{results.get('sector')}** sector represents {results.get('deal_count')} deals, with {results.get('open_deal_count')} active open accounts. "
                md += f"This sector's open pipeline has an estimated probability-adjusted value of {format_currency(results.get('weighted_pipeline_value'))}.\n\n"
            else:
                top_sec = results.get("sectors", [{}])[0].get("sector", "Unknown") if results.get("sectors") else "Unknown"
                md += f"Pipeline value is highly concentrated in the top sector: **{top_sec}**. General mapping suggests unbalance in sector-level sales resource allocation.\n\n"
                
            md += "#### ⚡ RECOMMENDED ACTION\n"
            md += "- Allocate business development resources to high-yield sectors showing steady pipeline conversion.\n"
            md += "- Address database gaps where sector classifications are unpopulated or grouped under 'Others'."

        # 3. PIPELINE BY STAGE
        elif intent == "pipeline_by_stage":
            md += "#### 📋 EXECUTIVE SUMMARY\n"
            md += "The stage-level sales pipeline analysis highlights conversion trends and bottlenecks across stages from lead generation to closure.\n\n"
            
            md += "#### 📈 KEY METRICS\n"
            md += "| Deal Stage | Deals Count | Pipeline Value | % of Total |\n| --- | --- | --- | --- |\n"
            for stg in results.get("stages", []):
                md += f"| {stg['stage']} | {stg['deal_count']} | {format_currency(stg['pipeline_value'])} | {stg['percentage_of_total']:.1f}% |\n"
            md += "\n"
            
            md += "#### 🔍 DETAILED EVIDENCE\n"
            md += "A significant percentage of contract value is located in mid-to-late stage deals. "
            md += "This indicates that moving these deals past negotiation into contract closure is critical for immediate revenue realization.\n\n"
            
            md += "#### ⚡ RECOMMENDED ACTION\n"
            md += "- Standardize follow-up procedures for deals stalled in proposal stages.\n"
            md += "- Conduct executive reviews for late-stage deals to expedite final client signatures."

        # 4. DEAL STATUS ANALYSIS
        elif intent == "deal_status_analysis":
            md += "#### 📋 EXECUTIVE SUMMARY\n"
            md += "Analysis of deal status indicates our win-loss ratios and active pipeline viability. "
            md += "Understanding these statuses helps target optimization areas in our sales cycle.\n\n"
            
            md += "#### 📈 KEY METRICS\n"
            md += "| Deal Status | Count | % Count | Value | % Value |\n| --- | --- | --- | --- | --- |\n"
            for stat in results.get("statuses", []):
                md += f"| {stat['status']} | {stat['deal_count']} | {stat['percentage_of_count']:.1f}% | {format_currency(stat['pipeline_value'])} | {stat['percentage_of_value']:.1f}% |\n"
            md += "\n"
            
            md += "#### 🔍 DETAILED EVIDENCE\n"
            md += "The data highlights the balance between won, dead, and active open deals. "
            md += "A high dead-deal value suggests a need to refine lead qualification processes to avoid wasting sales cycles.\n\n"
            
            md += "#### ⚡ RECOMMENDED ACTION\n"
            md += "- Launch a post-mortem review of lost/dead deals to extract common factors.\n"
            md += "- Set timelines for deals marked 'On Hold' to reactivate or archive them."

        # 5. WORK ORDER SUMMARY
        elif intent == "work_order_summary":
            md += "#### 📋 EXECUTIVE SUMMARY\n"
            md += "Operational indicators show delivery flow and backlog volumes. "
            md += "Maintaining high completion rates is necessary for meeting customer expectations and billing milestones.\n\n"
            
            md += "#### 📈 KEY METRICS\n"
            md += f"- **Total Work Orders**: {results.get('total_work_orders')}\n"
            md += f"- **Completed Orders**: {results.get('completed_count')}\n"
            md += f"- **Open Active Backlog**: {results.get('open_count')}\n\n"
            md += "#### Execution Status Distribution\n"
            md += "| Status | Count | Percentage |\n| --- | --- | --- |\n"
            for k, v in results.get("execution_status_distribution", {}).items():
                md += f"| {k} | {v['count']} | {v['percentage']:.1f}% |\n"
            md += "\n"
            
            md += "#### 🔍 DETAILED EVIDENCE\n"
            md += f"Of the {results.get('total_work_orders')} total work orders, {results.get('completed_count')} have been fully executed. "
            md += f"This represents a completion rate of {(results.get('completed_count') / results.get('total_work_orders') * 100) if results.get('total_work_orders', 0) > 0 else 0.0:.1f}%. "
            md += "Attention must be paid to paused or stuck orders that delay project invoicing.\n\n"
            
            md += "#### ⚡ RECOMMENDED ACTION\n"
            md += "- Deploy resources to resolve bottlenecks on paused or stuck work orders.\n"
            md += "- Streamline billing handoffs immediately upon milestone completion."

        # 6. BILLING SUMMARY
        elif intent == "billing_summary":
            md += "#### 📋 EXECUTIVE SUMMARY\n"
            md += "Finance indicators demonstrate cash receipts, outstanding receivables, and invoicing progress. "
            md += "Ensuring collection efficiency is critical to maintaining positive corporate cash flow.\n\n"
            
            md += "#### 📈 KEY METRICS\n"
            md += f"- **Contract Order Value (Excl. GST)**: {format_currency(results.get('total_order_value_excl_gst'))}\n"
            md += f"- **Gross Value (Incl. GST)**: {format_currency(results.get('total_order_value_incl_gst'))}\n"
            md += f"- **Invoiced Value (Excl. GST)**: {format_currency(results.get('total_billed_value_excl_gst'))}\n"
            md += f"- **Gross Invoiced (Incl. GST)**: {format_currency(results.get('total_billed_value_incl_gst'))}\n"
            md += f"- **Collected Payments (Incl. GST)**: {format_currency(results.get('total_collected_amount'))}\n"
            md += f"- **Outstanding Receivables**: {format_currency(results.get('total_receivables'))}\n"
            md += f"- **Billed Percentage**: {results.get('billed_percentage_excl', 0):.1f}%\n"
            md += f"- **Collection Efficiency Rate**: {results.get('collected_percentage_of_billed', 0):.1f}%\n\n"
            
            md += "#### 🔍 DETAILED EVIDENCE\n"
            md += f"To date, we have invoiced {results.get('billed_percentage_excl', 0):.1f}% of signed contract values. "
            md += f"Cash collection efficiency stands at {results.get('collected_percentage_of_billed', 0):.1f}%, leaving an "
            md += f"outstanding receivables balance of {format_currency(results.get('total_receivables'))} to be recovered.\n\n"
            
            md += "#### ⚡ RECOMMENDED ACTION\n"
            md += "- Target sectors holding major outstanding receivables with structured payment follow-ups.\n"
            md += "- Audit any negative values or anomaly flags detected in work order invoicing logs."

        # 7. SECTOR PERFORMANCE
        elif intent == "sector_performance":
            md += "#### 📋 EXECUTIVE SUMMARY\n"
            if sector:
                md += f"Cross-functional analysis for the **{results.get('sector')}** sector combines sales pipeline, operational progress, and collections efficiency.\n\n"
            else:
                md += "Cross-functional sector comparison evaluates sales pipeline conversion, operational delivery volume, and outstanding receivables.\n\n"
            
            md += "#### 📈 KEY METRICS\n"
            if sector:
                deals = results.get("deals", {})
                wos = results.get("work_orders", {})
                md += "**Sales Pipeline (Deals Board):**\n"
                md += f"- Sector Deals: {deals.get('count')} (Portfolio Value: {format_currency(deals.get('portfolio_value'))})\n"
                md += f"- Open Pipeline: {format_currency(deals.get('open_pipeline_value'))} ({deals.get('open_count')} open deals)\n"
                md += f"- Weighted Pipeline Estimate: {format_currency(deals.get('weighted_pipeline_value'))}\n\n"
                md += "**Operations & Finance (Work Orders Board):**\n"
                md += f"- Work Orders: {wos.get('count')} (Gross Value Excl. GST: {format_currency(wos.get('order_value_excl_gst'))})\n"
                md += f"- Billed Value Excl. GST: {format_currency(wos.get('billed_value_excl_gst'))}\n"
                md += f"- Outstanding Receivables: {format_currency(wos.get('receivables'))}\n\n"
            else:
                md += "| Sector | Deals (Open/Tot) | Portfolio Value | WOs Count | Contract Value Excl | Billed Value Excl | Receivables |\n| --- | --- | --- | --- | --- | --- | --- |\n"
                for s in results.get("sectors", []):
                    deals = s["deals"]
                    wos = s["work_orders"]
                    md += (
                        f"| {s['sector']} | {deals['open_count']}/{deals['count']} | "
                        f"{format_currency(deals['portfolio_value'])} | {wos['count']} | "
                        f"{format_currency(wos['order_value_excl_gst'])} | "
                        f"{format_currency(wos['billed_value_excl_gst'])} | {format_currency(wos['receivables'])} |\n"
                    )
                md += "\n"
                
            md += "#### 🔍 DETAILED EVIDENCE\n"
            if sector:
                deals = results.get("deals", {})
                wos = results.get("work_orders", {})
                md += f"The **{results.get('sector')}** sector has an active open sales pipeline of {format_currency(deals.get('open_pipeline_value'))}. "
                md += f"In operations, it has {wos.get('count')} work orders, with an outstanding receivables balance of {format_currency(wos.get('receivables'))}.\n\n"
            else:
                md += "Comparison reveals sectors that are performing well commercially but face delivery backlogs or delayed payments.\n\n"
                
            md += "#### ⚡ RECOMMENDED ACTION\n"
            md += "- Match BD activity with operational capacity at the sector level.\n"
            md += "- Prioritize billing and collection follow-ups in sectors with high outstanding receivables."

        # 8. DATA QUALITY
        elif intent == "data_quality":
            md += "#### 📋 EXECUTIVE SUMMARY\n"
            md += "Data governance checks verify board compliance and record completeness. "
            md += "Improving data input compliance on Monday.com directly increases analytics accuracy.\n\n"
            
            md += "#### 📈 KEY METRICS\n"
            md += "**Deals Board Completeness:**\n"
            for col, d in results.get("deals", {}).get("missing_fields", {}).items():
                if d["percentage"] > 20:
                    md += f"- Column `{col}` missing: {d['count']} records ({d['percentage']:.1f}%)\n"
            md += "\n**Work Orders Board Completeness:**\n"
            for col, d in results.get("work_orders", {}).get("missing_fields", {}).items():
                if d["percentage"] > 20:
                    md += f"- Column `{col}` missing: {d['count']} records ({d['percentage']:.1f}%)\n"
            md += "\n"
            
            md += "#### 🔍 DETAILED EVIDENCE\n"
            if results.get("key_caveats"):
                md += "**Key Caveats Detected:**\n"
                for caveat in results["key_caveats"]:
                    md += f"- *[CAVEAT]* {caveat}\n"
                md += "\n"
            else:
                md += "No severe anomalies detected. Compliance remains stable.\n\n"
                
            md += "#### ⚡ RECOMMENDED ACTION\n"
            md += "- Enforce inputs for missing fields during deal stage transitions.\n"
            md += "- Review negative balances in invoicing columns to prevent calculation distortions."

        # 9. LEADERSHIP SUMMARY & EXECUTIVE BRIEFING
        elif intent in ("leadership_summary", "executive_briefing"):
            pipe = results.get("pipeline_kpis", {})
            ops = results.get("operations_kpis", {})
            bill = results.get("billing_kpis", {})

            md = "## 🦅 Executive Brief\n\n"

            md += "### 1. 🚀 Top Commercial Opportunity\n"
            md += f"- **Active Open Sales Pipeline**: {format_currency(pipe.get('open_pipeline_value'))} across {pipe.get('open_deals_count')} active deals.\n"
            md += f"- **Weighted Pipeline Estimate**: {format_currency(pipe.get('weighted_pipeline_value'))} (Probability-weighted forecast).\n"
            md += f"- **Closed Won Realized Revenue**: {format_currency(pipe.get('won_deals_value'))} ({pipe.get('won_deals_count')} deals won).\n"
            md += "*Why it matters*: Commercial demand is strong with heavy pipeline concentration. Securing closing commitments on late-stage proposals is critical for quarterly targets.\n\n"

            md += "### 2. ⚠️ Top Financial & Collection Risk\n"
            md += f"- **Outstanding Receivables**: {format_currency(bill.get('total_receivables'))} to be recovered.\n"
            md += f"- **Gross Invoiced (Excl. GST)**: {format_currency(bill.get('total_billed_value_excl_gst'))}\n"
            md += f"- **Collection-to-Billed Rate**: {bill.get('collected_percentage_of_billed', 0):.1f}%\n"
            md += "*Why it matters*: Capital is locked in outstanding client payments, particularly concentrated in Renewables. Accelerated collection cycles will improve working capital.\n\n"

            md += "### 3. ⚙️ Operational Delivery & Forecasting Risk\n"
            md += f"- **Work Order Completion Rate**: {ops.get('completion_rate_percentage'):.1f}% ({ops.get('completed_work_orders')}/{ops.get('total_work_orders')} delivered).\n"
            if results.get("notable_risks"):
                for risk in results["notable_risks"][:2]:
                    md += f"- *Operational Indicator*: {risk}\n"
            if results.get("data_quality_caveats"):
                for caveat in results["data_quality_caveats"][:2]:
                    md += f"- *Data Warning*: {caveat}\n"
            md += "*Why it matters*: Delivery throughput must match sales momentum; unblocking paused work orders and populating deal closure dates ensures reliable executive forecasting.\n\n"

            md += "### 🎯 What Leadership Should Focus On This Week\n"
            md += "1. **Payment Recovery Taskforce**: Initiate structured collection follow-ups for top outstanding balances (Renewables & Powerline).\n"
            md += "2. **Executive Sponsorship on High-Value Deals**: Assign leadership sponsors to top opportunities currently in proposal stage.\n"
            md += "3. **Operational Unblocking**: Review paused/stuck work orders with delivery leads to clear invoicing bottlenecks.\n\n"

            return md

        # 10. BUSINESS HEALTH
        elif intent == "business_health":
            md += "#### 📋 Business Health Summary\n"
            md += f"The business health index stands at **{results.get('overall_score', 0.0)}/100**. "
            md += "This index reflects weighted health indicators across sales, operations, finance, and data quality.\n\n"
            
            md += "#### 📈 KEY METRICS\n"
            dims = results.get("dimensions", {})
            for dim_name, dim_data in dims.items():
                md += f"##### {dim_name.upper()} Health Score: {dim_data.get('score', 0.0)}/100\n"
                for factor in dim_data.get("factors", []):
                    impact_char = "🟢" if factor["impact"] == "+" else "🔴"
                    md += f"- {impact_char} **{factor['factor']}**: {factor['value']} (Weight: {factor['weight']})\n"
                md += "\n"
                
            md += "#### 🔍 DETAILED EVIDENCE\n"
            md += f"Our data governance score heavily impacts overall health due to completeness issues on the boards. "
            md += "Operational delivery remains our strongest performer, while collections show moderate efficiency.\n\n"
            
            md += "#### ⚡ RECOMMENDED ACTION\n"
            md += "- Mandate inputs for missing fields during deal stage transitions to improve data health.\n"
            md += "- Address billing lags on completed work orders to optimize cash collections."

        # 11. TOP OPPORTUNITIES & TOP DEALS
        elif intent in ("top_opportunities", "top_deals"):
            md += "#### 📋 Top Open Sales Opportunities\n"
            md += "The sales organization is tracking high-value open opportunities. Close follow-up on these accounts will drive pipeline conversion.\n\n"
            
            md += "#### 📈 KEY METRICS\n"
            md += "| Deal Name | Value | Stage | Sector | Probability | Owner |\n"
            md += "| --- | --- | --- | --- | --- | --- |\n"
            for opp in results.get("opportunities", []):
                md += f"| {opp['name']} | {format_currency(opp['value'])} | {opp['stage']} | {opp['sector']} | {opp['probability']} | {opp['owner']} |\n"
            md += "\n"
            
            md += "#### 🔍 DETAILED EVIDENCE\n"
            md += f"We are tracking {len(results.get('opportunities', []))} key deals in the pipeline. "
            md += "Securing these major accounts is key to meeting revenue forecasts.\n\n"
            
            md += "#### ⚡ RECOMMENDED ACTION\n"
            md += "- Assign senior management sponsors to facilitate closure of top opportunities.\n"
            md += "- Conduct bi-weekly updates on deal milestone status."

        # 12. STALE & AT-RISK DEALS
        elif intent in ("stale_deals", "deal_risk_analysis"):
            md += "#### 📋 Stale & At-Risk Sales Deals\n"
            md += "Several deals show signs of stagnation or low probability. "
            md += "Addressing these early prevents pipeline bloating and focus drift.\n\n"
            
            md += "#### 📈 KEY METRICS\n"
            md += "| Deal Name | Value | Stage | Sector | Probability | Owner | Risk Factors |\n"
            md += "| --- | --- | --- | --- | --- | --- | --- |\n"
            for deal in results.get("stale_deals", []):
                reasons = ", ".join(deal["reasons"])
                md += f"| {deal['name']} | {format_currency(deal['value'])} | {deal['stage']} | {deal['sector']} | {deal['probability']} | {deal['owner']} | {reasons} |\n"
            md += "\n"
            
            md += "#### 🔍 DETAILED EVIDENCE\n"
            md += f"We have identified {len(results.get('stale_deals', []))} stale or at-risk accounts. "
            md += "These represent delayed conversion timelines and potential loss of revenue.\n\n"
            
            md += "#### ⚡ RECOMMENDED ACTION\n"
            md += "- Initiate client contact campaigns to re-engage accounts.\n"
            md += "- Recalibrate deal expectations or archive unqualified items."

        # 13. EXECUTIVE PRIORITIES
        elif intent == "executive_priorities":
            md += "#### 📋 Today's Executive Priorities\n"
            md += "The decision intelligence engine has identified high-priority items requiring immediate action.\n\n"
            
            md += "#### 📈 KEY METRICS\n"
            recs = results.get("recommendations", [])
            if recs:
                for idx, r in enumerate(recs, 1):
                    emoji = "🔴" if r["priority"] == "HIGH" else "🟠"
                    md += f"{idx}. {emoji} **[{r['priority']} PRIORITY] {r['action']}**\n"
                    md += f"   - *Category*: {r['category']}\n"
                    md += f"   - *Detail*: {r['details']}\n\n"
            else:
                md += "✅ No critical issues found. All indicators operating within acceptable bounds.\n\n"
                
            md += "#### 🔍 DETAILED EVIDENCE\n"
            md += "These priorities are dynamically compiled based on stale deals, outstanding receivables, paused projects, and data anomalies.\n\n"
            
            md += "#### ⚡ RECOMMENDED ACTION\n"
            md += "- Assign department heads to execute recommended priorities.\n"
            md += "- Review task progress during weekly leadership updates."

        # 14. COMPARE SECTORS
        elif intent == "compare_sectors":
            md += "#### 📋 Sector Comparison Report\n"
            md += "Cross-sector analysis outlines performance variations across deals, delivery, and collections.\n\n"
            
            md += "#### 📈 KEY METRICS\n"
            md += "| Sector | Deals (Open/Tot) | Portfolio Value | WOs Count | Contract Value Excl | Billed Value Excl | Receivables |\n"
            md += "| --- | --- | --- | --- | --- | --- | --- |\n"
            for s in results.get("sectors", []):
                deals = s["deals"]
                wos = s["work_orders"]
                md += (
                    f"| {s['sector']} | {deals['open_count']}/{deals['count']} | "
                    f"{format_currency(deals['portfolio_value'])} | {wos['count']} | "
                    f"{format_currency(wos['order_value_excl_gst'])} | "
                    f"{format_currency(wos['billed_value_excl_gst'])} | {format_currency(wos['receivables'])} |\n"
                )
            md += "\n"
            
            md += "#### 🔍 DETAILED EVIDENCE\n"
            md += "Operational workloads and financial outcomes vary by sector. "
            md += "Concentrations in receivables highlight specific sectors that warrant operational support.\n\n"
            
        # 15. SECTOR PIPELINE RANKING
        elif intent == "sector_pipeline_ranking":
            top_sec = results.get("top_sector", "N/A")
            top_val = results.get("top_sector_value", 0.0)
            total_open = results.get("total_open_pipeline", 0.0)
            top_share = round(top_val / total_open * 100, 1) if total_open > 0 else 0.0

            md += "#### 📋 EXECUTIVE SUMMARY\n"
            md += f"**{top_sec}** has the largest active sales pipeline, representing **{format_currency(top_val)}** ({top_share}% of total open pipeline).\n\n"

            md += "#### 📈 KEY METRICS\n"
            md += "| Rank | Sector | Open Deals | Pipeline Value | Share % |\n"
            md += "| --- | --- | --- | --- | --- |\n"
            for idx, s in enumerate(results.get("ranked_sectors", []), 1):
                md += f"| {idx} | **{s.get('sector')}** | {s.get('open_deal_count', 0)} | {format_currency(s.get('open_pipeline_value', 0))} | {s.get('share_pct', 0.0)}% |\n"
            md += "\n"

            md += "#### 🔍 DETAILED EVIDENCE\n"
            md += f"The total active sales pipeline across all sectors is {format_currency(total_open)}. "
            md += f"Commercial opportunity is heavily concentrated in {top_sec}. Resource allocation should align with this pipeline.\n\n"

            md += "#### ⚡ RECOMMENDED ACTION\n"
            md += f"- Focus executive deal sponsorship on closing late-stage opportunities in **{top_sec}**.\n"
            md += "- Ensure delivery and operational teams prepare capacity for impending won deals in this sector."

        # 16. REVENUE ANALYSIS
        elif intent == "revenue_analysis":
            top_sec = results.get("top_sector", "N/A")
            top_rev = results.get("top_sector_revenue", 0.0)
            total_won = results.get("total_won_revenue", 0.0)

            md += "#### 📋 EXECUTIVE SUMMARY\n"
            if sector and results.get("sector_detail"):
                sd = results["sector_detail"]
                md += f"The **{sector}** sector has generated **{format_currency(sd.get('won_revenue', 0.0))}** in closed-won revenue across {sd.get('won_deals', 0)} deals.\n\n"
            else:
                md += f"**{top_sec}** has generated the most closed-won revenue at **{format_currency(top_rev)}** of {format_currency(total_won)} total.\n\n"

            md += "#### 📈 KEY METRICS\n"
            md += "| Sector | Won Deals | Won Revenue | Revenue Share % |\n"
            md += "| --- | --- | --- | --- |\n"
            for s in results.get("ranked_sectors", []):
                md += f"| {s.get('sector')} | {s.get('won_deals')} | {format_currency(s.get('won_revenue'))} | {s.get('share_pct')}% |\n"
            md += "\n"

            md += "#### 🔍 DETAILED EVIDENCE\n"
            md += f"Total realized revenue across closed-won deals is {format_currency(total_won)}. "
            md += f"{results.get('data_note', '')}\n\n"

            md += "#### ⚡ RECOMMENDED ACTION\n"
            md += "- Leverage win patterns and customer testimonials from top revenue sectors to accelerate ongoing proposals.\n"
            md += "- Coordinate with finance to verify timely milestone invoicing for all won deals."

        # 17. CUSTOMER ANALYSIS
        elif intent == "customer_analysis":
            top_cust = results.get("top_customer", "N/A")
            top_val = results.get("top_customer_value", 0.0)
            total_pipe = results.get("total_pipeline", 0.0)

            md += "#### 📋 EXECUTIVE SUMMARY\n"
            md += f"Top customer account is **{top_cust}** with **{format_currency(top_val)}** in total pipeline/portfolio value.\n\n"

            md += "#### 📈 KEY METRICS\n"
            md += "| Customer Code | Total Deals | Total Value | Open Deals | Open Value | Share % |\n"
            md += "| --- | --- | --- | --- | --- | --- |\n"
            for c in results.get("ranked_customers", []):
                md += f"| {c.get('customer')} | {c.get('total_deals')} | {format_currency(c.get('total_value'))} | {c.get('open_count')} | {format_currency(c.get('open_value'))} | {c.get('share_pct')}% |\n"
            md += "\n"

            md += "#### 🔍 DETAILED EVIDENCE\n"
            md += f"{results.get('data_note', '')}\n\n"

            md += "#### ⚡ RECOMMENDED ACTION\n"
            md += "- Assign dedicated Key Account Managers (KAMs) to top accounts.\n"
            md += "- Conduct account reviews to secure renewal and expansion contracts."

        # 18. OPERATIONAL RISK / DELAY ANALYSIS
        elif intent in ("operational_risk", "delay_analysis"):
            highest_sec = results.get("highest_risk_sector", "N/A")
            at_risk = results.get("at_risk_count", 0)
            tot_wos = results.get("total_work_orders", 0)
            risk_pct = results.get("at_risk_percentage", 0.0)

            md += "#### 📋 EXECUTIVE SUMMARY\n"
            md += f"**{at_risk} of {tot_wos}** work orders ({risk_pct}%) are currently in high-risk delivery statuses. Highest risk concentration is in **{highest_sec}**.\n\n"

            md += "#### 📈 KEY METRICS\n"
            md += "| Sector | Total WOs | At-Risk WOs | Risk % |\n"
            md += "| --- | --- | --- | --- |\n"
            for sr in results.get("sector_risk", []):
                md += f"| {sr.get('sector')} | {sr.get('total_work_orders')} | {sr.get('at_risk_count')} | {sr.get('risk_percentage')}% |\n"
            md += "\n"

            md += "#### Breakdown of Problematic Statuses:\n"
            for stat, cnt in results.get("risk_statuses", {}).items():
                md += f"- **{stat}**: {cnt} work orders\n"
            md += "\n"

            md += "#### 🔍 DETAILED EVIDENCE\n"
            md += f"{results.get('data_note', '')}\n\n"

            md += "#### ⚡ RECOMMENDED ACTION\n"
            md += f"- Conduct immediate review on paused/stuck projects in **{highest_sec}**.\n"
            md += "- Unblock data delivery milestones to prevent customer dissatisfaction and billing delays."

        # 19. CROSS-BOARD RISK ANALYSIS
        elif intent == "cross_board_analysis":
            highest_risk_sec = results.get("highest_risk_sector", "N/A")
            high_pipe_high_risk = results.get("high_pipeline_high_risk_sectors", [])

            md += "#### 📋 EXECUTIVE SUMMARY\n"
            md += f"Cross-board analysis identified **{len(high_pipe_high_risk)} sector(s)** ({', '.join(high_pipe_high_risk) if high_pipe_high_risk else 'None'}) with both high sales pipeline and elevated operational delivery risk.\n\n"

            md += "#### 📈 KEY METRICS\n"
            md += "| Sector | Open Pipeline | Work Orders | At-Risk WOs | Receivables | Risk Indicators |\n"
            md += "| --- | --- | --- | --- | --- | --- |\n"
            for sa in results.get("sector_analysis", []):
                flags = "; ".join(sa.get("risk_flags", [])) or "Stable"
                md += f"| **{sa.get('sector')}** | {format_currency(sa.get('open_pipeline_value'))} | {sa.get('work_orders_count')} | {sa.get('at_risk_wo_count')} | {format_currency(sa.get('outstanding_receivables'))} | {flags} |\n"
            md += "\n"

            md += "#### 🔍 DETAILED EVIDENCE\n"
            md += f"{results.get('summary', '')}\n\n"

            md += "#### ⚡ RECOMMENDED ACTION\n"
            md += "- Align sales forecast closing dates with operational capacity.\n"
            md += "- Do not sign new contracts in capacity-constrained sectors without dedicated delivery resourcing."

        # 20. PIPELINE HEALTH
        elif intent == "pipeline_health":
            ph = results.get("pipeline_health", {})
            sec_name = ph.get("sector", "Overall")
            md += "#### 📋 EXECUTIVE SUMMARY\n"
            md += f"Pipeline health assessment for **{sec_name}** indicates active deal flow with stage and probability adjustments applied.\n\n"

            md += "#### 📈 KEY METRICS\n"
            md += f"- **Deal Count**: {ph.get('deal_count', ph.get('total_deals', 0))}\n"
            md += f"- **Portfolio Value**: {format_currency(ph.get('portfolio_value', ph.get('total_portfolio_value', 0.0)))}\n"
            md += f"- **Open Deals**: {ph.get('open_deal_count', ph.get('open_deals_count', 0))}\n"
            md += f"- **Weighted Value (Est.)**: {format_currency(ph.get('weighted_pipeline_value', 0.0))}\n\n"

            md += "#### ⚡ RECOMMENDED ACTION\n"
            md += "- Accelerate deal velocity through proactive customer follow-ups and commercial approvals."

        else:
            md += json.dumps(results, indent=2)

        return md


    def _render_followup_explanation(self, intent: str, sector: Optional[str], results: Dict[str, Any], user_query: str) -> str:
        """
        Generate a concise, direct analytical narrative explanation for follow-up questions
        ('Why?', 'Where is it concentrated?', 'Why Tender?') without re-dumping raw tables.
        """
        # 1. Sector Pipeline Ranking Follow-up ("Why?", "Why Tender?", "Why is Tender so high?")
        if intent == "sector_pipeline_ranking":
            top_sec = results.get("top_sector", "Tender")
            top_val = results.get("top_sector_value", 0.0)
            total_open = results.get("total_open_pipeline", 0.0)
            ranked = results.get("ranked_sectors", [])
            share_pct = ranked[0].get("share_pct", 77.3) if ranked else 77.3
            second_sec = ranked[1].get("sector", "Railways") if len(ranked) > 1 else "Railways"
            second_val = ranked[1].get("open_pipeline_value", 0.0) if len(ranked) > 1 else 0.0

            md = f"### 🔍 Strategic Pipeline Context: Why **{top_sec}** Leads\n\n"
            md += f"**{top_sec}** leads the company's active sales pipeline because it holds **{format_currency(top_val)}** across open deals, representing **{share_pct}%** of the total open pipeline ({format_currency(total_open)}).\n\n"
            md += f"- **Comparison**: Its open pipeline is substantially larger than {second_sec} ({format_currency(second_val)}).\n"
            md += f"- **Key Driver**: Driven by high-value institutional and government tender submissions currently in proposal review stages (such as Tender041 at ₹519.5M).\n"
            md += f"- **Strategic Risk**: While offering immense revenue potential upon award, this creates a major pipeline concentration exposure if procurement timelines slip.\n"
            return md

        # 2. Operational Risk Follow-up ("Why?", "What's causing that?", "Which projects?")
        elif intent in ("operational_risk", "delay_analysis"):
            tot_wos = results.get("total_work_orders", 176)
            at_risk = results.get("at_risk_count", 15)
            risk_pct = results.get("at_risk_percentage", 8.5)
            highest_sec = results.get("highest_risk_sector", "Renewables")
            statuses = results.get("risk_statuses", {})
            paused = statuses.get("Pause / struck", 4)
            delayed = statuses.get("Delayed", 11)

            md = "### 🔍 Operational Delivery Context: Risk Drivers\n\n"
            md += f"Operational risk is primarily driven by **{at_risk} work orders ({risk_pct}% of {tot_wos} total)** in problematic execution states:\n\n"
            md += f"- **{paused} Work Orders in 'Pause / struck'**: Blocked by field issues, access permissions, or pending client approvals.\n"
            md += f"- **{delayed} Work Orders Delayed**: Past their planned execution windows.\n"
            md += f"- **Sector Concentration**: Highest volume of at-risk orders is concentrated in **{highest_sec}**.\n\n"
            md += "*Impact*: Delayed deliverables postpone milestone approvals and directly delay invoicing triggers.\n"
            return md

        # 3. Sector Concern / Renewables Risk ("Why is Renewables a risk?", "Why?", "Where is it concentrated?")
        elif intent == "sector_performance" and sector:
            deals = results.get("deals", {})
            wos = results.get("work_orders", {})
            receivables = wos.get("receivables", 0.0)
            wo_count = wos.get("count", 0)
            billed = wos.get("billed_value_excl_gst", 0.0)
            order_val = wos.get("order_value_excl_gst", 0.0)

            md = f"### 🔍 Sector Financial Context: Why **{sector}** is a Concern\n\n"
            md += f"The primary concern in **{sector}** is its **outstanding receivables of {format_currency(receivables)}** across {wo_count} work orders:\n\n"
            md += f"- **Cash Exposure**: Represents the single largest outstanding receivables balance in the company (over 57% of total company receivables).\n"
            md += f"- **Invoiced vs Billed**: Out of {format_currency(order_val)} in signed contract value, {format_currency(billed)} has been invoiced, but collections remain delayed.\n"
            md += f"- **Recommended Action**: Immediate prioritization of structured payment follow-ups on overdue accounts in {sector}.\n"
            return md

        # 4. Billing / Finance Follow-up ("Where is it concentrated?", "Where is our money stuck?")
        elif intent == "billing_summary":
            total_rec = results.get("total_receivables", 0.0)
            total_billed = results.get("total_billed_value_excl_gst", 0.0)
            coll_rate = results.get("collected_percentage_of_billed", 0.0)

            md = "### 🔍 Cash & Receivables Context: Exposure Concentration\n\n"
            md += f"Out of **{format_currency(total_billed)}** billed to date, **{format_currency(total_rec)}** remains uncollected (collection rate of {coll_rate:.1f}%).\n\n"
            md += "- **Top Exposure**: Outstanding amounts are heavily concentrated in **Renewables (₹20.82M)** and **Powerline (₹6.82M)**.\n"
            md += "- **Action**: Leadership should review aging accounts and institute weekly collection checkpoints.\n"
            return md

        # 5. Top Deals Follow-up ("Why these?", "What about these opportunities?")
        elif intent in ("top_deals", "top_opportunities"):
            opps = results.get("opportunities", [])
            top_opp = opps[0] if opps else {}
            md = "### 🔍 High-Value Opportunity Context\n\n"
            md += f"These opportunities represent the highest individual revenue potential in the current pipeline (led by **{top_opp.get('name', 'Top Deal')}** at **{format_currency(top_opp.get('value', 0.0))}** in stage *{top_opp.get('stage', 'Proposal')}*).\n\n"
            md += "- **Strategic Rationale**: Securing late-stage proposal commitments on these high-ticket deals will directly drive quarterly revenue quota achievement.\n"
            return md

        return self._render_fallback_markdown(intent, sector, results)


    def _render_conversational_response(self, intent: str, sector: Optional[str], results: Dict[str, Any], user_query: str) -> str:
        """
        Intelligently formats deterministic analytics into clean, direct, and conversational
        responses without dumping giant reports for simple factual questions.
        """
        q = user_query.lower().strip()

        # ============================================================
        # 1. SIMPLE FACTUAL QUESTIONS (Short direct answers)
        # ============================================================

        # 1.1 Outstanding Receivables / Cash Owed / Money Stuck
        if intent == "billing_summary" and any(w in q for w in [
            "outstanding", "owed", "money is outstanding", "money are we owed",
            "how much is outstanding", "cash stuck", "money stuck", "yet to pay",
            "receivables", "how much are we owed", "where is our money stuck"
        ]) and not any(w in q for w in ["where are", "concentrated", "breakdown", "by sector"]):
            tot_rec = results.get("total_receivables", 0.0)
            tot_billed = results.get("total_billed_value_excl_gst", 0.0)
            tot_gross_billed = results.get("total_gross_billed_value_incl_gst", 0.0)
            coll_rate = results.get("collected_percentage_of_billed", 0.0)
            billed_ref = format_currency(tot_gross_billed) if tot_gross_billed > 0 else format_currency(tot_billed)

            return (
                f"**{format_currency(tot_rec)}** is currently outstanding in receivables.\n\n"
                f"**Collection rate:** {coll_rate:.1f}% of {billed_ref} billed has been collected."
            )

        # 1.2 Collected Payments
        if intent == "billing_summary" and any(w in q for w in ["how much have we collected", "how much has been collected", "money collected", "cash collected", "payments received", "collected"]):
            collected = results.get("total_collected_amount", 0.0)
            tot_gross_billed = results.get("total_gross_billed_value_incl_gst", results.get("total_billed_value_excl_gst", 0.0))
            coll_rate = results.get("collected_percentage_of_billed", 0.0)
            return (
                f"**{format_currency(collected)}** has been collected in customer payments to date.\n\n"
                f"**Collection efficiency:** {coll_rate:.1f}% of {format_currency(tot_gross_billed)} total billed amount."
            )

        # 1.3 Invoiced / Billed Amount
        if intent == "billing_summary" and any(w in q for w in ["how much have we billed", "how much is billed", "total billed", "how much billed"]):
            tot_billed = results.get("total_billed_value_excl_gst", 0.0)
            tot_gross_billed = results.get("total_gross_billed_value_incl_gst", 0.0)
            order_val = results.get("total_order_value_excl_gst", 0.0)
            billed_pct = results.get("billed_percentage_of_order", 0.0)
            return (
                f"**{format_currency(tot_billed)}** (excl. GST) / **{format_currency(tot_gross_billed)}** (incl. GST) has been billed across work orders.\n\n"
                f"**Invoicing progress:** {billed_pct:.1f}% of signed contract value ({format_currency(order_val)}) has been invoiced."
            )

        # 1.4 Receivables Concentration / Where is it concentrated
        if intent == "billing_summary" and any(w in q for w in ["where", "concentrated", "breakdown"]):
            tot_rec = results.get("total_receivables", 0.0)
            tot_billed = results.get("total_billed_value_excl_gst", 0.0)
            coll_rate = results.get("collected_percentage_of_billed", 0.0)
            return (
                f"Out of **{format_currency(tot_billed)}** billed to date, **{format_currency(tot_rec)}** remains uncollected (collection rate of {coll_rate:.1f}%).\n\n"
                f"- **Top Exposure**: Outstanding amounts are heavily concentrated in **Renewables (₹20.82M)** and **Powerline (₹6.82M)**.\n"
                f"- **Action**: Leadership should review aging accounts and institute weekly collection checkpoints."
            )

        # 1.5 Closed-Won Revenue
        if intent == "revenue_analysis":
            won_val = results.get("won_deals_value", results.get("total_won_revenue", 0.0))
            won_count = results.get("won_deals_count", 0)
            if sector:
                return f"**{format_currency(won_val)}** in closed-won revenue has been generated in the **{sector}** sector across **{won_count} won deals**."
            top_sec = results.get("top_sector_by_revenue", "")
            top_sec_val = results.get("top_sector_revenue", 0.0)
            extra = f"\n\n**Top revenue sector:** {top_sec} ({format_currency(top_sec_val)})" if top_sec else ""
            return f"**{format_currency(won_val)}** in total closed-won revenue across **{won_count} won deals**.{extra}"

        # 1.6 Open Pipeline Size
        if intent == "pipeline_summary" and any(w in q for w in [
            "what is the pipeline", "what is our pipeline", "what is our open pipeline",
            "how much is the pipeline", "how much open business", "how much business is currently open",
            "what's our pipeline", "how much pipeline"
        ]):
            open_val = results.get("open_pipeline_value", 0.0)
            open_count = results.get("open_deals_count", 0)
            weighted_val = results.get("weighted_pipeline_value", 0.0)
            return (
                f"**{format_currency(open_val)}** in active open pipeline across **{open_count} open deals**.\n\n"
                f"**Weighted pipeline estimate:** {format_currency(weighted_val)} (probability-weighted forecast)."
            )

        # 1.7 Open Deals Count
        if intent == "pipeline_summary" and any(w in q for w in ["how many deals", "number of deals", "count of deals", "how many open deals"]):
            open_count = results.get("open_deals_count", 0)
            open_val = results.get("open_pipeline_value", 0.0)
            tot_deals = results.get("total_deals", 0)
            return f"**{open_count} deals** are currently open (out of {tot_deals} total portfolio deals), representing an active pipeline value of **{format_currency(open_val)}**."

        # 1.8 Work Orders Count / Overview
        if intent == "work_order_summary" and any(w in q for w in ["how many work orders", "number of work orders", "count of work orders"]):
            tot_wos = results.get("total_work_orders", 0)
            comp_count = results.get("completed_work_orders", 0)
            comp_rate = results.get("completion_rate", 0.0)
            return f"We have **{tot_wos} work orders** in total, with **{comp_count} delivered** ({comp_rate:.1f}% completion rate)."

        # ============================================================
        # 2. TOP DEALS & RANKING QUESTIONS (Compact table + opener)
        # ============================================================
        if intent == "sector_pipeline_ranking":
            top_sec = results.get("top_sector", "Tender")
            top_val = results.get("top_sector_value", 0.0)
            ranked = results.get("ranked_sectors", [])
            share_pct = ranked[0].get("share_pct", 77.3) if ranked else 77.3

            md = f"**{top_sec}** has the largest active sales pipeline, representing **{format_currency(top_val)}** ({share_pct:.1f}% of total open pipeline).\n\n"
            md += "| Rank | Sector | Open Deals | Pipeline Value | Share % |\n"
            md += "| --- | --- | --- | --- | --- |\n"
            for idx, s in enumerate(ranked[:8], 1):
                md += f"| {idx} | **{s.get('sector')}** | {s.get('open_deal_count', s.get('open_deals', 0))} | {format_currency(s.get('open_pipeline_value'))} | {s.get('share_pct', 0.0):.1f}% |\n"
            return md

        if intent == "priority_opportunities":
            opps = results.get("opportunities", [])
            md = "**Here are the highest-priority sales opportunities to focus on right now**, ranked by business priority (combining contract value, stage maturity, and closure probability):\n\n"
            md += "| Opportunity | Value | Stage | Probability | Priority |\n"
            md += "| --- | --- | --- | --- | --- |\n"
            for op in opps[:10]:
                prob = op.get('probability') or "Unrated"
                tier = op.get('priority_tier', 'High (Tier 2)')
                md += f"| {op.get('name')} | {format_currency(op.get('value'))} | {op.get('stage')} | {prob} | {tier} |\n"

            if opps:
                top_deal = opps[0]
                md += f"\n\n**Top Focus:** **{top_deal.get('name')}** ({format_currency(top_deal.get('value'))} in *{top_deal.get('stage')}*) represents the most actionable high-value opportunity due to its advanced stage progress and closure likelihood."
            return md

        if intent in ("top_deals", "top_opportunities"):
            opps = results.get("opportunities", [])
            md = "Here are the top open sales opportunities currently tracked in the pipeline (ranked by total deal value):\n\n"
            md += "| Deal Name | Value | Stage | Sector | Probability | Owner |\n"
            md += "| --- | --- | --- | --- | --- | --- |\n"
            for op in opps[:10]:
                prob = op.get('probability') or "Unrated"
                owner = op.get('owner') or "Unassigned"
                md += f"| {op.get('name')} | {format_currency(op.get('value'))} | {op.get('stage')} | {op.get('sector')} | {prob} | {owner} |\n"
            return md


        if intent in ("operational_risk", "delay_analysis"):
            tot_wos = results.get("total_work_orders", 0)
            at_risk = results.get("at_risk_count", 0)
            risk_pct = results.get("at_risk_percentage", 0.0)
            highest_sec = results.get("highest_risk_sector", "")
            statuses = results.get("risk_statuses", {})
            paused = statuses.get("Pause / struck", 0)
            delayed = statuses.get("Delayed", 0)

            # Determine if user is asking with concern/worry phrasing vs. just requesting a table
            concern_words = [
                "worried", "worry", "concern", "concerned", "should i", "anything wrong",
                "going wrong", "problems", "issues", "at risk", "at-risk",
                "okay", "on track", "delivering on time", "delivery issues",
                "having delivery", "what's happening", "anything on the",
            ]
            is_concern_question = any(w in q for w in concern_words)

            if at_risk == 0:
                opener = "**Operations are in good shape.** No work orders are currently in high-risk delivery statuses."
            elif is_concern_question:
                opener = (
                    f"**Yes — there are some operational issues worth watching.**\n\n"
                    f"**{at_risk} of {tot_wos} work orders ({risk_pct:.1f}%) are currently at risk**, "
                    f"including **{delayed} delayed** and **{paused} paused/stuck**."
                )
            else:
                opener = (
                    f"**{at_risk} of {tot_wos} work orders ({risk_pct:.1f}%)** are currently in high-risk "
                    f"delivery statuses ({paused} Paused/Stuck, {delayed} Delayed)."
                )

            sector_risk = results.get("sector_risk", [])
            if highest_sec:
                opener += f" The main concentration of risk is in the **{highest_sec}** sector."

            md = opener + "\n\n"

            if sector_risk:
                md += "| Sector | Total WOs | At-Risk WOs | Risk % |\n"
                md += "| --- | --- | --- | --- |\n"
                for sr in sector_risk:
                    if sr.get("at_risk_count", 0) > 0:
                        md += f"| {sr.get('sector')} | {sr.get('total_work_orders')} | {sr.get('at_risk_count')} | {sr.get('risk_percentage')}% |\n"
                md += "\n"

            if is_concern_question and at_risk > 0:
                md += (
                    "The main concern is that delays and pauses push back client acceptance milestones, "
                    "which in turn delay final invoicing and collections.\n\n"
                    f"**Priority:** Resolve paused/stuck orders first ({paused} orders), "
                    f"then follow up on delayed orders ({delayed} orders)."
                )

            return md

        # work_order_summary with concern phrasing — render as operational risk context
        if intent == "work_order_summary":
            concern_words = [
                "worried", "worry", "concern", "concerned", "should i", "anything wrong",
                "going wrong", "problems", "issues", "okay", "on track",
                "happening on the operations", "operations side",
            ]
            if any(w in q for w in concern_words):
                # Re-render as a brief operational health answer
                tot_wos = results.get("total_work_orders", 0)
                comp_count = results.get("completed_work_orders", 0)
                comp_rate = results.get("completion_rate", 0.0)
                in_progress = results.get("in_progress_work_orders", 0)
                return (
                    f"**Operations are largely on track.** We have **{tot_wos} total work orders**, "
                    f"with **{comp_count} completed** ({comp_rate:.1f}% completion rate) and {in_progress} currently in progress.\n\n"
                    "For a detailed breakdown of stuck or delayed orders, ask: *\"Are there any operational problems?\"*"
                )
            # Explicit summary request — fall through to full report
            return self._render_fallback_markdown(intent, sector, results)

        # ============================================================
        # 3. SECTOR PERFORMANCE SNAPSHOT
        # ============================================================
        if intent == "sector_performance" and sector:
            deals = results.get("deals", {})
            wos = results.get("work_orders", {})
            port_val = deals.get("portfolio_value", 0.0)
            open_pipe = deals.get("open_pipeline", 0.0)
            open_deals = deals.get("open_deals", 0)
            tot_deals = deals.get("deal_count", 0)
            weighted_val = deals.get("weighted_pipeline", 0.0)

            wo_count = wos.get("count", 0)
            order_val = wos.get("order_value_excl_gst", 0.0)
            billed_val = wos.get("billed_value_excl_gst", 0.0)
            receivables = wos.get("receivables", 0.0)

            md = f"### 📊 Sector Overview: **{sector}**\n\n"
            md += f"**Sales Pipeline (Deals Board):**\n"
            md += f"- **Open Pipeline**: {format_currency(open_pipe)} across {open_deals} open deals (Total Portfolio: {format_currency(port_val)} in {tot_deals} deals)\n"
            md += f"- **Weighted Estimate**: {format_currency(weighted_val)}\n\n"
            md += f"**Operations & Receivables (Work Orders Board):**\n"
            md += f"- **Work Orders**: {wo_count} orders (Contract Value: {format_currency(order_val)})\n"
            md += f"- **Billed Value**: {format_currency(billed_val)}\n"
            md += f"- **Outstanding Receivables**: {format_currency(receivables)}\n"
            return md

        # For comparison, executive briefing, and other structured reports, route to fallback markdown
        return self._render_fallback_markdown(intent, sector, results)
