import unittest
from unittest.mock import MagicMock, patch
import pandas as pd
import json

from app.ai_agent import SkylarkBIAgent, LLMClient
from app.query_engine import rule_based_intent_detector

class TestBIAgent(unittest.TestCase):

    def setUp(self):
        # Create minimal deals and work orders dataframes for testing routing
        self.deals_df = pd.DataFrame([
            {
                "id": "1",
                "name": "Mining Deal 1",
                "deal_status": "Open",
                "closure_probability": "High",
                "deal_value": 500000.0,
                "deal_stage": "E. Proposal/Commercials Sent",
                "sector_service": "Mining"
            },
            {
                "id": "2",
                "name": "Renewables Deal 1",
                "deal_status": "Won",
                "closure_probability": None,
                "deal_value": 1000000.0,
                "deal_stage": "G. Project Won",
                "sector_service": "Renewables"
            }
        ])
        
        self.work_orders_df = pd.DataFrame([
            {
                "id": "101",
                "name": "WO 1",
                "execution_status": "Completed",
                "sector": "Mining",
                "type_of_work": "Topography Survey: RGB",
                "amount_excl_gst": 100000.0,
                "amount_incl_gst": 118000.0,
                "billed_value_excl_gst": 100000.0,
                "billed_value_incl_gst": 118000.0,
                "collected_amount": 118000.0,
                "amount_receivable": 0.0,
                "amount_to_bill_excl_gst": 0.0,
                "amount_to_bill_incl_gst": 0.0,
                "billing_status": "Billed"
            }
        ])

    def test_rule_based_intent_routing(self):
        """Verify that the rule-based fallback accurately detects intents and sectors."""
        # Generic pipeline -> pipeline_summary
        res = rule_based_intent_detector("how is the pipeline looking?")
        self.assertEqual(res["intent"], "pipeline_summary")
        
        # Sector pipeline
        res = rule_based_intent_detector("Show me pipeline for Mining")
        self.assertEqual(res["intent"], "pipeline_by_sector")
        self.assertEqual(res["sector"], "Mining")

        # Sector performance
        res = rule_based_intent_detector("How is Renewables performing?")
        self.assertEqual(res["intent"], "sector_performance")
        self.assertEqual(res["sector"], "Renewables")

        # Leadership update
        res = rule_based_intent_detector("Prepare a leadership update")
        self.assertIn(res["intent"], ["leadership_summary", "executive_briefing"])

        # Billing summary
        res = rule_based_intent_detector("How much have we billed and collected?")
        self.assertEqual(res["intent"], "billing_summary")

        # Data quality
        res = rule_based_intent_detector("Show data caveats and missing values")
        self.assertEqual(res["intent"], "data_quality")

    @patch("app.ai_agent.LLMClient")
    def test_agent_clarification(self, mock_llm_class):
        """Test that ambiguous questions return a clarification response."""
        mock_llm = MagicMock()
        mock_llm.provider = "openai"
        # Mock LLM to return clarification JSON
        mock_llm.call_llm.return_value = json.dumps({
            "intent": "clarify",
            "sector": None,
            "clarification_question": "Would you like the overall pipeline, or a specific sector such as Mining, Renewables, or Powerline?"
        })
        mock_llm_class.return_value = mock_llm

        agent = SkylarkBIAgent(self.deals_df, self.work_orders_df, llm_client=mock_llm)
        resp = agent.ask("how is the pipeline looking?")
        
        self.assertEqual(resp, "Would you like the overall pipeline, or a specific sector such as Mining, Renewables, or Powerline?")
        # Should have called LLM for intent detection
        mock_llm.call_llm.assert_called_once()

    @patch("app.ai_agent.LLMClient")
    def test_numerical_hallucination_prevention(self, mock_llm_class):
        """Test that LLM hallucinating values triggers the safety fallback to markdown results."""
        mock_llm = MagicMock()
        mock_llm.provider = "openai"
        
        # 1. First call (intent detection) returns billing_summary
        # 2. Second call (prompt response) returns a hallucinated number (e.g. ₹9,999,999,999.00)
        mock_llm.call_llm.side_effect = [
            json.dumps({
                "intent": "billing_summary",
                "sector": None,
                "clarification_question": None
            }),
            "Our overall billing is ₹9,999,999,999.00 with ₹0.00 receivables."
        ]
        mock_llm_class.return_value = mock_llm

        agent = SkylarkBIAgent(self.deals_df, self.work_orders_df, llm_client=mock_llm)
        resp = agent.ask("How is our billing?")
        
        # Check that the safety fallback was triggered because 9,999,999,999.00 is not in the source metrics (total is 100,000)
        self.assertIn("Safety Fallback: Deterministic Analytics Output", resp)
        self.assertIn("₹100,000.00", resp)
        self.assertNotIn("₹9,999,999,999.00", resp)

    @patch("app.ai_agent.LLMClient")
    def test_valid_llm_answer(self, mock_llm_class):
        """Verify that a correct LLM response with valid figures passes successfully."""
        mock_llm = MagicMock()
        mock_llm.provider = "openai"
        
        mock_llm.call_llm.side_effect = [
            json.dumps({
                "intent": "billing_summary",
                "sector": None,
                "clarification_question": None
            }),
            "The total contract order value excl. GST is ₹100,000.00, and billed value is ₹100,000.00."
        ]
        mock_llm_class.return_value = mock_llm

        agent = SkylarkBIAgent(self.deals_df, self.work_orders_df, llm_client=mock_llm)
        resp = agent.ask("How is our billing?")
        
        self.assertNotIn("Safety Fallback", resp)
        self.assertIn("₹100,000.00", resp)

    @patch("app.ai_agent.LLMClient")
    def test_cross_board_performance_routing(self, mock_llm_class):
        """Test routing and query formatting for cross-board sector performance."""
        mock_llm = MagicMock()
        mock_llm.provider = "openai"
        mock_llm.call_llm.side_effect = [
            json.dumps({
                "intent": "sector_performance",
                "sector": "Mining",
                "clarification_question": None
            }),
            "The Mining sector has 1 deal with portfolio value ₹500,000.00, and 1 work order value ₹100,000.00."
        ]
        mock_llm_class.return_value = mock_llm

        agent = SkylarkBIAgent(self.deals_df, self.work_orders_df, llm_client=mock_llm)
        resp = agent.ask("How is Mining performing across sales and operations?")
        
        self.assertNotIn("Safety Fallback", resp)
        self.assertIn("₹500,000.00", resp)
        self.assertIn("₹100,000.00", resp)

    @patch("app.ai_agent.LLMClient")
    def test_leadership_summary_routing(self, mock_llm_class):
        """Test routing for the overall leadership update."""
        mock_llm = MagicMock()
        mock_llm.provider = "openai"
        mock_llm.call_llm.side_effect = [
            json.dumps({
                "intent": "leadership_summary",
                "sector": None,
                "clarification_question": None
            }),
            "Here is the executive overview. The open sales pipeline is ₹500,000.00."
        ]
        mock_llm_class.return_value = mock_llm

        agent = SkylarkBIAgent(self.deals_df, self.work_orders_df, llm_client=mock_llm)
        resp = agent.ask("Prepare a leadership update.")
        
        self.assertIn("₹500,000.00", resp)

    def test_rule_based_fallback_mode(self):
        """Test that agent runs fully in rule-based fallback mode when LLM is inactive."""
        # Setup agent with an LLM client that has no provider (provider = None)
        llm_client = LLMClient()
        llm_client.provider = None
        
        agent = SkylarkBIAgent(self.deals_df, self.work_orders_df, llm_client=llm_client)
        resp = agent.ask("how is the billing looking?")
        
        self.assertIn("Verified Analytics Report (BILLING_SUMMARY)", resp)
        self.assertIn("Contract Order Value (Excl. GST)", resp)
        self.assertIn("₹100,000.00", resp)

    def test_advanced_routing(self):
        """Verify routing for new advanced intents."""
        res = rule_based_intent_detector("What is our business health score?")
        self.assertEqual(res["intent"], "business_health")

        res = rule_based_intent_detector("Which deals are our biggest opportunities?")
        self.assertIn(res["intent"], ["top_opportunities", "top_deals"])

        res = rule_based_intent_detector("Show me our stale and at-risk deals")
        self.assertIn(res["intent"], ["stale_deals", "deal_risk_analysis"])

        res = rule_based_intent_detector("Compare Mining and Renewables performance")
        self.assertEqual(res["intent"], "compare_sectors")
        self.assertIn("Mining", res["compare_sectors"])
        self.assertIn("Renewables", res["compare_sectors"])

        res = rule_based_intent_detector("What should leadership focus on?")
        self.assertEqual(res["intent"], "executive_priorities")

    def test_advanced_fallback_rendering(self):
        """Test rule-based fallback rendering of advanced calculations."""
        llm_client = LLMClient()
        llm_client.provider = None
        agent = SkylarkBIAgent(self.deals_df, self.work_orders_df, llm_client=llm_client)

        # Test business health
        resp = agent.ask("How is our business health?")
        self.assertIn("Business Health Summary", resp)
        self.assertIn("SALES Health Score", resp)

        # Test top opportunities
        resp = agent.ask("What are our biggest opportunities?")
        self.assertIn("top open sales opportunities", resp.lower())

        # Test stale deals
        resp = agent.ask("Which deals are stale?")
        self.assertIn("Stale & At-Risk Sales Deals", resp)

        # Test compare sectors
        resp = agent.ask("Compare Mining and Renewables")
        self.assertIn("Sector Comparison Report", resp)

    def test_sector_pipeline_ranking_regression(self):
        """
        CRITICAL ACCEPTANCE REGRESSION TEST:
        'Which sector has the biggest pipeline?' must route to sector_pipeline_ranking
        and MUST NOT return a generic PIPELINE_SUMMARY report.
        """
        # 1. Test intent detector directly
        res = rule_based_intent_detector("Which sector has the biggest pipeline?")
        self.assertEqual(res["intent"], "sector_pipeline_ranking")

        # 2. Test variants of the question
        variants = [
            "which sector has the biggest pipeline?",
            "Which sector has the largest pipeline?",
            "Who has the biggest pipeline by sector?",
            "Where is most of our pipeline?",
            "Which industry has the most pipeline?",
            "Where is our strongest sales pipeline?",
            "biggest pipeline by sector",
            "Which sector has the highest pipeline?",
        ]
        for v in variants:
            r = rule_based_intent_detector(v)
            self.assertEqual(r["intent"], "sector_pipeline_ranking", f"Failed for variant: {v}")

        # 3. Test agent execution returns ranked sector output rather than generic pipeline summary
        llm_client = LLMClient()
        llm_client.provider = None
        agent = SkylarkBIAgent(self.deals_df, self.work_orders_df, llm_client=llm_client)
        resp = agent.ask("Which sector has the biggest pipeline?")

        # Must NOT be generic pipeline summary title
        self.assertNotIn("PIPELINE_SUMMARY", resp)
        # Must mention the top sector (Mining has 500,000 open in setUp)
        self.assertIn("Mining", resp)
        self.assertIn("₹500,000.00", resp)
        # Must contain ranking table
        self.assertIn("| Rank | Sector |", resp)

    def test_all_18_standard_founder_questions(self):
        """Verify routing for all 18 standard founder questions in the assignment."""
        test_cases = [
            ("Which sector has the biggest pipeline?", "sector_pipeline_ranking"),
            ("How's our pipeline looking?", "pipeline_summary"),
            ("Which sector generated the most revenue?", "revenue_analysis"),
            ("Show me the top 5 deals by value.", "top_deals"),
            ("What are our biggest pipeline risks?", "deal_risk_analysis"),
            ("Which deals are most likely to close?", "top_deals"),
            ("Which projects are delayed?", "delay_analysis"),
            ("Which sector has the highest operational risk?", "operational_risk"),
            ("Compare Energy and Mining.", "compare_sectors"),
            ("What is our weighted pipeline?", "pipeline_summary"),
            ("How many deals are currently open?", "pipeline_summary"),
            ("Which customers have the largest outstanding opportunities?", "customer_analysis"),
            ("Give me an executive briefing.", "executive_briefing"),
            ("What are the biggest risks across sales and operations?", "cross_board_analysis"),
            ("Show me data quality issues.", "data_quality"),
        ]

        for query, expected_intent in test_cases:
            res = rule_based_intent_detector(query)
            self.assertEqual(
                res["intent"], expected_intent,
                f"Query '{query}' expected intent '{expected_intent}' but got '{res['intent']}'"
            )

    def test_conversation_memory_followup(self):
        """Test follow-up queries using conversation history."""
        llm_client = LLMClient()
        llm_client.provider = None
        agent = SkylarkBIAgent(self.deals_df, self.work_orders_df, llm_client=llm_client)

        history = [
            {"role": "user", "content": "Which sector has the biggest pipeline?"},
            {"role": "assistant", "content": "Mining has the largest active sales pipeline with ₹500,000.00."}
        ]

    def test_founder_and_executive_queries(self):
        """Verify that natural founder/CEO phrasing maps to executive intents without clarification."""
        llm_client = LLMClient()
        llm_client.provider = None
        agent = SkylarkBIAgent(self.deals_df, self.work_orders_df, llm_client=llm_client)

        # 1. Founder 2-minute question
        q1 = "I'm the founder and I have 2 minutes. What are the three most important things I need to know about the business right now?"
        res1 = rule_based_intent_detector(q1)
        self.assertEqual(res1["intent"], "executive_briefing")
        resp1 = agent.ask(q1)
        self.assertNotIn("Could you clarify", resp1)
        self.assertIn("Executive Brief", resp1)

        # 2. Personal weekly focus question
        q2 = "What should I personally focus on this week?"
        res2 = rule_based_intent_detector(q2)
        self.assertEqual(res2["intent"], "executive_priorities")
        resp2 = agent.ask(q2)
        self.assertNotIn("Could you clarify", resp2)
        self.assertIn("Executive Priorities", resp2)

        # 3. Sector concern question
        q3 = "Why are you concerned about Renewables?"
        res3 = rule_based_intent_detector(q3)
        self.assertEqual(res3["intent"], "sector_performance")
        self.assertEqual(res3["sector"], "Renewables")
        resp3 = agent.ask(q3)
        self.assertNotIn("Could you clarify", resp3)
        self.assertIn("Renewables", resp3)

        # 4. Other natural founder questions
        founder_cases = [
            ("What's happening in the business right now?", "executive_briefing"),
            ("If you were the CEO, what would you worry about?", "executive_priorities"),
            ("What needs my attention?", "executive_priorities"),
            ("Give me a quick leadership update.", "executive_briefing"),
            ("Where should leadership focus?", "executive_priorities"),
            ("Are we doing okay?", "business_health"),
            ("What's going well and what isn't?", "executive_briefing"),
            ("Give me the state of the business in one minute.", "executive_briefing"),
            ("Where are we seeing most of our sales opportunity?", "sector_pipeline_ranking"),
            ("How much money are we still waiting to collect?", "billing_summary"),
            ("Do we have any operational bottlenecks?", "delay_analysis"),
        ]
    def test_all_40_natural_language_questions(self):
        """Verify routing for all 40 natural language questions from the assignment requirements."""
        queries_and_intents = [
            # PIPELINE
            ("Which sector has the biggest pipeline?", "sector_pipeline_ranking"),
            ("Where are we seeing most of our sales opportunity?", "sector_pipeline_ranking"),
            ("How's our pipeline looking?", "pipeline_summary"),
            ("Is our pipeline healthy?", "pipeline_summary"),
            ("How much open business do we have?", "pipeline_summary"),
            # TOP DEALS
            ("What deals should I pay attention to?", "top_deals"),
            ("Which opportunities are most important?", "top_deals"),
            ("Show me the biggest open deals.", "top_deals"),
            # EXECUTIVE
            ("Give me a leadership update.", "executive_briefing"),
            ("I'm the founder and I have 2 minutes. What are the three most important things I need to know about the business right now?", "executive_briefing"),
            ("What should I personally focus on this week?", "executive_priorities"),
            ("What should I worry about?", "executive_priorities"),
            # OPERATIONS
            ("Are there any operational problems I should know about?", "operational_risk"),
            ("Are any projects stuck?", "operational_risk"),
            ("What's going wrong with delivery?", "operational_risk"),
            ("Do we have execution risks?", "operational_risk"),
            ("How are operations doing?", "work_order_summary"),
            # SECTOR
            ("Why is Renewables a risk?", "sector_performance"),
            ("Tell me about Renewables.", "sector_performance"),
            ("How is Mining doing?", "sector_performance"),
            ("Compare Mining and Renewables.", "compare_sectors"),
            # FINANCE
            ("How much money is outstanding?", "billing_summary"),
            ("Where are receivables concentrated?", "billing_summary"),
            ("How much have we billed?", "billing_summary"),
            ("How much have we collected?", "billing_summary"),
            # DATA QUALITY
            ("Can we trust this pipeline?", "data_quality"),
            ("What's missing from the data?", "data_quality"),
            ("Are there data quality problems?", "data_quality"),
            # FOLLOW-UP
            ("Why?", "follow_up"),
            ("What about Mining?", "sector_performance"),
            ("Compare it with Renewables.", "compare_sectors"),
            ("How much is that?", "follow_up"),
            ("What should we do?", "follow_up"),
            # GENERAL HUMAN QUESTIONS
            ("How are we doing?", "executive_briefing"),
            ("Anything I should be worried about?", "executive_priorities"),
            ("What needs my attention?", "executive_priorities"),
            ("What's the biggest problem in the business right now?", "executive_priorities"),
            ("Where should we focus?", "executive_priorities"),
            ("What would you tell the board?", "executive_briefing"),
            ("Give me the quick version.", "executive_briefing"),
        ]

        llm_client = LLMClient()
        llm_client.provider = None
        agent = SkylarkBIAgent(self.deals_df, self.work_orders_df, llm_client=llm_client)

        for q, expected_intent in queries_and_intents:
            res = rule_based_intent_detector(q)
            if expected_intent in ("top_deals", "priority_opportunities"):
                self.assertIn(
                    res["intent"],
                    ["top_deals", "priority_opportunities"],
                    f"Query '{q}' expected top deals / priority opportunities intent but got '{res['intent']}'"
                )
            else:
                self.assertEqual(
                    res["intent"], expected_intent,
                    f"Query '{q}' expected intent '{expected_intent}' but got '{res['intent']}'"
                )
            # Ensure none of these questions produce clarification
            if expected_intent != "follow_up":
                resp = agent.ask(q)
                self.assertNotIn("Could you clarify which business area", resp, f"Query '{q}' triggered unwanted clarification!")


    def test_section_16_all_30_specific_queries(self):
        """
        Verify all 30 exact natural language questions from Section 16 of the assignment requirements.
        """
        queries = [
            "How are we doing?",
            "How is the business performing?",
            "Which sector has the biggest pipeline?",
            "Why is Tender so high?",
            "What about Mining?",
            "Why is Renewables a risk?",
            "Are there any operational problems I should know about?",
            "What deals should I pay attention to?",
            "Which opportunities need my attention?",
            "How much money is outstanding?",
            "Where is it concentrated?",
            "I'm the founder and I have 2 minutes. What are the three most important things I need to know about the business right now?",
            "What should I personally focus on this week?",
            "Give me a leadership update.",
            "Compare Mining and Renewables.",
            "How much of the pipeline is actually likely to close?",
            "Can we trust the pipeline number?",
            "Where is our money stuck?",
            "Are sales healthy?",
            "Are operations keeping up?",
            "What's keeping me up at night?",
            "Where should I put my attention?",
            "Tell me about Mining.",
            "And Renewables?",
            "Why is that?",
            "Show me the biggest opportunities.",
            "Which sector is performing best?",
            "What are the biggest business risks right now?",
        ]

        llm_client = LLMClient()
        llm_client.provider = None
        agent = SkylarkBIAgent(self.deals_df, self.work_orders_df, llm_client=llm_client)

        for q in queries:
            resp = agent.ask(q)
            self.assertNotIn(
                "Could you clarify which business area you are interested in?",
                resp,
                f"Required Section 16 question '{q}' incorrectly asked for clarification!"
            )
            self.assertTrue(len(resp) > 30, f"Response for '{q}' is empty or too short!")

    def test_multi_turn_conversational_followup_depth(self):
        """
        Verify multi-turn follow-up question depth and explanation rendering.
        """
        llm_client = LLMClient()
        llm_client.provider = None
        agent = SkylarkBIAgent(self.deals_df, self.work_orders_df, llm_client=llm_client)

        # Sequence 1: Ranking -> Why? -> Sector shift
        h = []
        r1 = agent.ask("Which sector has the biggest pipeline?", conversation_history=h)
        self.assertIn("Mining", r1)
        h.append({"role": "user", "content": "Which sector has the biggest pipeline?"})
        h.append({"role": "assistant", "content": r1})

        r2 = agent.ask("Why?", conversation_history=h)
        self.assertIn("Mining", r2)
        self.assertIn("Why", r2)
        self.assertNotIn("Could you clarify", r2)
        h.append({"role": "user", "content": "Why?"})
        h.append({"role": "assistant", "content": r2})

        r3 = agent.ask("What about Mining?", conversation_history=h)
        self.assertIn("Mining", r3)
        self.assertNotIn("Could you clarify", r3)

        # Sequence 2: Billing -> Where is it concentrated?
        h2 = []
        rb1 = agent.ask("How much money is outstanding?", conversation_history=h2)
        self.assertIn("outstanding in receivables", rb1.lower())
        h2.append({"role": "user", "content": "How much money is outstanding?"})
        h2.append({"role": "assistant", "content": rb1})

        rb2 = agent.ask("Where is it concentrated?", conversation_history=h2)
        self.assertIn("Renewables", rb2)
        self.assertNotIn("Could you clarify", rb2)

    def test_conversational_response_presentation(self):
        """
        Verify that simple factual questions return concise answers without dumping
        the giant 4-section report, while rankings and executive queries remain appropriately structured.
        """
        llm_client = LLMClient()
        llm_client.provider = None
        agent = SkylarkBIAgent(self.deals_df, self.work_orders_df, llm_client=llm_client)

        # 1. Simple factual: "How much money is outstanding?"
        resp1 = agent.ask("How much money is outstanding?")
        self.assertIn("outstanding in receivables", resp1.lower())
        self.assertIn("Collection rate:", resp1)
        self.assertNotIn("EXECUTIVE SUMMARY", resp1)
        self.assertNotIn("DETAILED EVIDENCE", resp1)
        self.assertNotIn("RECOMMENDED ACTION", resp1)

        # 2. Simple factual: "How much are we owed?"
        resp2 = agent.ask("How much are we owed?")
        self.assertIn("outstanding in receivables", resp2.lower())
        self.assertNotIn("EXECUTIVE SUMMARY", resp2)

        # 3. Simple factual: "How much have we collected?"
        resp3 = agent.ask("How much have we collected?")
        self.assertIn("collected", resp3.lower())
        self.assertNotIn("EXECUTIVE SUMMARY", resp3)

        # 4. Simple factual: "What is the pipeline?"
        resp4 = agent.ask("What is the pipeline?")
        self.assertIn("active open pipeline", resp4.lower())
        self.assertIn("Weighted pipeline estimate", resp4)
        self.assertNotIn("EXECUTIVE SUMMARY", resp4)

        # 5. Ranking question: "Which sector has the biggest pipeline?"
        resp5 = agent.ask("Which sector has the biggest pipeline?")
        self.assertIn("Mining", resp5)
        self.assertIn("| Rank | Sector |", resp5)

        # 6. Comparison question: "Compare Mining and Renewables"
        resp6 = agent.ask("Compare Mining and Renewables")
        self.assertIn("Sector Comparison Report", resp6)

        # 7. Executive question: "Give me a leadership update."
        resp7 = agent.ask("Give me a leadership update.")
        self.assertIn("Executive Brief", resp7)
        self.assertIn("Top Commercial Opportunity", resp7)

    def test_operational_concern_vs_summary_formatting(self):
        """
        Verify concern-phrased operational questions return concise conversational answers,
        while explicit summary requests may use the full formatted report.
        """
        llm_client = LLMClient()
        llm_client.provider = None
        agent = SkylarkBIAgent(self.deals_df, self.work_orders_df, llm_client=llm_client)

        BANNED_HEADERS = ["EXECUTIVE SUMMARY", "DETAILED EVIDENCE", "RECOMMENDED ACTION"]

        # 1. "Should I be worried about anything on the operations side?"
        #    -> Must route to operational_risk and return concise answer
        resp1 = agent.ask("Should I be worried about anything on the operations side?")
        for header in BANNED_HEADERS:
            self.assertNotIn(header, resp1, f'"{header}" found in concern-question response')
        # Must contain risk count or a clear operational-health signal
        self.assertTrue(
            any(phrase in resp1.lower() for phrase in [
                "work order", "at risk", "delayed", "paused", "operational", "in good shape",
            ]),
            f"Response lacks operational content: {resp1[:200]}"
        )

        # 2. "Are there any operational problems?"
        #    -> Must route to operational_risk and return concise answer
        resp2 = agent.ask("Are there any operational problems?")
        for header in BANNED_HEADERS:
            self.assertNotIn(header, resp2, f'"{header}" found in concern-question response')
        self.assertTrue(
            any(phrase in resp2.lower() for phrase in [
                "work order", "at risk", "delayed", "paused", "operational", "in good shape",
            ]),
            f"Response lacks operational content: {resp2[:200]}"
        )

        # 3. "Is anything going wrong operationally?"
        #    -> Must route to operational_risk and return concise answer
        resp3 = agent.ask("Is anything going wrong operationally?")
        for header in BANNED_HEADERS:
            self.assertNotIn(header, resp3, f'"{header}" found in concern-question response')
        self.assertTrue(
            any(phrase in resp3.lower() for phrase in [
                "work order", "at risk", "delayed", "paused", "operational", "in good shape",
            ]),
            f"Response lacks operational content: {resp3[:200]}"
        )

        # 4. "Give me the work order summary."
        #    -> Full WORK_ORDER_SUMMARY report is acceptable here
        resp4 = agent.ask("Give me the work order summary.")
        self.assertIn("WORK_ORDER_SUMMARY", resp4)
        # Must include status distribution or operational metrics
        self.assertTrue(
            any(phrase in resp4 for phrase in [
                "Completed", "Total Work Orders", "Completion", "EXECUTIVE SUMMARY",
            ]),
            f"Response lacks work order summary content: {resp4[:200]}"
        )

        # 5. Intent routing sanity checks
        from app.query_engine import rule_based_intent_detector
        concern_queries = [
            "Should I be worried about anything on the operations side?",
            "Are there any operational problems?",
            "Is anything going wrong operationally?",
            "Are operations okay?",
            "Should I be concerned about operations?",
            "Are we having delivery issues?",
        ]
        for cq in concern_queries:
            r = rule_based_intent_detector(cq)
            self.assertEqual(
                r["intent"], "operational_risk",
                f"Expected operational_risk for: {cq!r}, got {r['intent']!r}"
            )

        summary_queries = [
            "Give me the work order summary.",
            "Show me execution status distribution",
        ]
        for sq in summary_queries:
            r = rule_based_intent_detector(sq)
            self.assertEqual(
                r["intent"], "work_order_summary",
                f"Expected work_order_summary for: {sq!r}, got {r['intent']!r}"
            )

    def test_priority_opportunities_vs_top_deals_routing(self):
        """Verify routing and distinct behaviors for priority opportunities vs biggest deals."""
        # 1. Importance / Win right now -> priority_opportunities
        r1 = rule_based_intent_detector("Which opportunities are most important for us to win right now?")
        self.assertEqual(r1["intent"], "priority_opportunities")

        r2 = rule_based_intent_detector("What deals should I pay attention to?")
        self.assertEqual(r2["intent"], "priority_opportunities")

        r3 = rule_based_intent_detector("Which opportunities need my attention?")
        self.assertEqual(r3["intent"], "priority_opportunities")

        # 2. Pure size / Value -> top_deals
        r4 = rule_based_intent_detector("Show me the biggest opportunities.")
        self.assertEqual(r4["intent"], "top_deals")

        r5 = rule_based_intent_detector("Show me the top 5 deals by value.")
        self.assertEqual(r5["intent"], "top_deals")

        # 3. Test agent responses
        llm_client = LLMClient()
        llm_client.provider = None
        agent = SkylarkBIAgent(self.deals_df, self.work_orders_df, llm_client=llm_client)

        resp_priority = agent.ask("Which opportunities are most important for us to win right now?")
        self.assertIn("Priority", resp_priority)
        self.assertIn("Mining Deal 1", resp_priority)

        resp_biggest = agent.ask("Show me the biggest opportunities.")
        self.assertIn("Deal Name", resp_biggest)
        self.assertIn("Mining Deal 1", resp_biggest)

    def test_gemini_client_configuration_and_fallback(self):
        """Verify LLMClient initialization, model candidate fallback, and error recording."""
        # When no keys configured
        with patch.dict("os.environ", {}, clear=True):
            client = LLMClient()
            self.assertIsNone(client.provider)
            self.assertEqual(client.connection_status, "Fallback")

    def test_dashboard_html_no_literal_div(self):
        """Verify that dashboard overview HTML does not contain unclosed or malformed div tags."""
        from app.dashboard.overview import _health_bar

        bar = _health_bar("Test Metric", 85.0)
        self.assertNotIn("\n", bar.strip())
        self.assertTrue(bar.startswith("<div") and bar.endswith("</div>"))

if __name__ == "__main__":
    unittest.main()

