import unittest
import pandas as pd
import math
from app.analytics import (
    get_pipeline_summary,
    get_pipeline_by_sector,
    get_pipeline_by_stage,
    get_deal_status_summary,
    get_work_order_summary,
    get_billing_summary,
    get_sector_performance,
    get_data_quality_summary,
    get_leadership_summary
)

class TestBIAnalytics(unittest.TestCase):

    def setUp(self):
        # Sample deals records
        self.sample_deals = [
            {
                "id": "1",
                "name": "Deal A",
                "deal_status": "Open",
                "closure_probability": "High",
                "deal_value": 100000.0,
                "deal_stage": "A. Lead Generated",
                "sector_service": "Mining"
            },
            {
                "id": "2",
                "name": "Deal B",
                "deal_status": "Won",
                "closure_probability": None,
                "deal_value": 200000.0,
                "deal_stage": "G. Project Won",
                "sector_service": "powerline"  # test casing
            },
            {
                "id": "3",
                "name": "Deal C",
                "deal_status": "Dead",
                "closure_probability": "Low",
                "deal_value": 50000.0,
                "deal_stage": "L. Project Lost",
                "sector_service": "Mining"
            },
            {
                "id": "4",
                "name": "Deal D",
                "deal_status": "Open",
                "closure_probability": "Medium",
                "deal_value": 150000.0,
                "deal_stage": "E. Proposal/Commercials Sent",
                "sector_service": "Renewables"
            },
            {
                "id": "5",
                "name": "Deal E",
                "deal_status": "Open",
                "closure_probability": None,  # test missing
                "deal_value": 100000.0,
                "deal_stage": "E. Proposal/Commercials Sent",
                "sector_service": "Renewables"
            },
            # Monday.com header row to be filtered
            {
                "id": "header",
                "name": "Name",
                "deal_status": "Deal Status",
                "closure_probability": "Closure Probability",
                "deal_value": None,
                "deal_stage": "Deal Stage",
                "sector_service": "Sector/service"
            }
        ]
        self.deals_df = pd.DataFrame(self.sample_deals)

        # Sample work orders records
        self.sample_work_orders = [
            {
                "id": "101",
                "name": "WO A",
                "execution_status": "Completed",
                "sector": "Mining",
                "type_of_work": "Topography Survey: RGB",
                "amount_excl_gst": 10000.0,
                "amount_incl_gst": 11800.0,
                "billed_value_excl_gst": 10000.0,
                "billed_value_incl_gst": 11800.0,
                "collected_amount": 11800.0,
                "amount_receivable": 0.0,
                "amount_to_bill_excl_gst": 0.0,
                "amount_to_bill_incl_gst": 0.0,
                "billing_status": "Billed"
            },
            {
                "id": "102",
                "name": "WO B",
                "execution_status": "Ongoing",
                "sector": "powerline",  # test casing
                "type_of_work": "LiDAR Survey: LiDAR",
                "amount_excl_gst": 20000.0,
                "amount_incl_gst": 23600.0,
                "billed_value_excl_gst": 10000.0,
                "billed_value_incl_gst": 11800.0,
                "collected_amount": 5900.0,
                "amount_receivable": 5900.0,
                "amount_to_bill_excl_gst": 10000.0,
                "amount_to_bill_incl_gst": 11800.0,
                "billing_status": "Partially Billed"
            },
            {
                "id": "103",
                "name": "WO C",
                "execution_status": "Executed until current month",
                "sector": "Renewables",
                "type_of_work": "Topography Survey: RGB",
                "amount_excl_gst": 30000.0,
                "amount_incl_gst": 35400.0,
                "billed_value_excl_gst": 30000.0,
                "billed_value_incl_gst": 35400.0,
                "collected_amount": 0.0,
                "amount_receivable": 35400.0,
                "amount_to_bill_excl_gst": 0.0,
                "amount_to_bill_incl_gst": 0.0,
                "billing_status": "Billed"
            }
        ]
        self.work_orders_df = pd.DataFrame(self.sample_work_orders)

    def test_empty_datasets(self):
        """Verify that empty DataFrames do not crash the module."""
        empty_deals = pd.DataFrame()
        empty_wos = pd.DataFrame()

        self.assertEqual(get_pipeline_summary(empty_deals)["total_deals"], 0)
        self.assertEqual(len(get_pipeline_by_sector(empty_deals)), 0)
        self.assertEqual(len(get_pipeline_by_stage(empty_deals)), 0)
        self.assertEqual(len(get_deal_status_summary(empty_deals)), 0)
        
        wo_sum = get_work_order_summary(empty_wos)
        self.assertEqual(wo_sum["total_work_orders"], 0)
        
        bill_sum = get_billing_summary(empty_wos)
        self.assertEqual(bill_sum["total_order_value_excl_gst"], 0.0)

        perf = get_sector_performance(empty_deals, empty_wos)
        self.assertEqual(len(perf), 0)

        dq = get_data_quality_summary(empty_deals, empty_wos)
        self.assertEqual(dq["deals"]["total_records"], 0)
        self.assertEqual(dq["work_orders"]["total_records"], 0)

    def test_pipeline_summary(self):
        """Test calculation of high-level pipeline summary metrics."""
        summary = get_pipeline_summary(self.deals_df)
        
        # 5 real deals (excluding header)
        self.assertEqual(summary["total_deals"], 5)
        # 100k (A) + 200k (B) + 50k (C) + 150k (D) + 100k (E) = 600k portfolio value
        self.assertEqual(summary["total_portfolio_value"], 600000.0)
        
        # Open deals: Deal A, Deal D, Deal E. (3 open deals)
        self.assertEqual(summary["open_deals_count"], 3)
        self.assertEqual(summary["open_pipeline_value"], 350000.0) # 100k + 150k + 100k
        
        # Won deals: Deal B
        self.assertEqual(summary["won_deals_count"], 1)
        self.assertEqual(summary["won_deals_value"], 200000.0)
        
        # Dead deals: Deal C
        self.assertEqual(summary["dead_deals_count"], 1)
        self.assertEqual(summary["dead_deals_value"], 50000.0)

        # Average probability (only open/hold deals with known probability)
        # Open/hold: A (High=0.8), D (Medium=0.5), E (None/missing)
        # Avg = (0.8 + 0.5) / 2 = 0.65
        self.assertAlmostEqual(summary["avg_closure_probability"], 0.65)

        # Weighted pipeline value (only active deals with known probability)
        # A: 100k * 0.8 = 80k
        # D: 150k * 0.5 = 75k
        # E: 100k * 0 = 0 (excluded)
        # Total = 155k
        self.assertEqual(summary["weighted_pipeline_value"], 155000.0)
        
        self.assertEqual(summary["deals_missing_probability"], 1)
        self.assertEqual(summary["deals_with_probability"], 2)

    def test_pipeline_by_sector(self):
        """Test grouped pipeline metrics by sector."""
        by_sector = get_pipeline_by_sector(self.deals_df)
        
        # Sectors should be Title Cased: Powerline, Mining, Renewables
        sectors = [item["sector"] for item in by_sector]
        self.assertIn("Powerline", sectors)
        self.assertIn("Mining", sectors)
        self.assertIn("Renewables", sectors)
        
        # Check Mining: Deal A (100k, Open, High), Deal C (50k, Dead, Low).
        # Total count = 2, Portfolio value = 150k. Open count = 1.
        mining = next(item for item in by_sector if item["sector"] == "Mining")
        self.assertEqual(mining["deal_count"], 2)
        self.assertEqual(mining["portfolio_value"], 150000.0)
        self.assertEqual(mining["open_deal_count"], 1)
        self.assertEqual(mining["avg_closure_probability"], 0.80) # Deal A is the only active open deal (Deal C is Dead)
        self.assertEqual(mining["weighted_pipeline_value"], 80000.0) # 100k * 0.8

    def test_pipeline_by_stage(self):
        """Test grouping by Deal Stage."""
        by_stage = get_pipeline_by_stage(self.deals_df)
        self.assertEqual(len(by_stage), 4) # Lead Generated, Project Won, Project Lost, Proposal/Commercials Sent
        
        # Sum of percentages should equal 100%
        pct_sum = sum(item["percentage_of_total"] for item in by_stage)
        self.assertAlmostEqual(pct_sum, 100.0)

    def test_work_order_summary(self):
        """Test operations aggregation on Work Orders."""
        summary = get_work_order_summary(self.work_orders_df)
        
        self.assertEqual(summary["total_work_orders"], 3)
        # Completed + Executed until current month = 2
        self.assertEqual(summary["completed_count"], 2)
        self.assertEqual(summary["open_count"], 1)
        
        # Verify distributions
        dist_status = summary["execution_status_distribution"]
        self.assertEqual(dist_status["Completed"]["count"], 1)
        self.assertEqual(dist_status["Ongoing"]["count"], 1)
        
        # Casing normalization checks
        dist_sector = summary["work_orders_by_sector"]
        self.assertIn("Powerline", dist_sector)

    def test_billing_summary(self):
        """Test Work Orders financial aggregations."""
        billing = get_billing_summary(self.work_orders_df)
        
        # Order Value Excl GST: 10k + 20k + 30k = 60k
        self.assertEqual(billing["total_order_value_excl_gst"], 60000.0)
        # Order Value Incl GST: 11.8k + 23.6k + 35.4k = 70.8k
        self.assertEqual(billing["total_order_value_incl_gst"], 70800.0)
        
        # Billed Value Excl GST: 10k + 10k + 30k = 50k
        self.assertEqual(billing["total_billed_value_excl_gst"], 50000.0)
        
        # Billed percentage = 50k / 60k = 83.33%
        self.assertAlmostEqual(billing["billed_percentage_excl"], 83.33333333333333)
        
        # Collected: 11.8k + 5.9k + 0 = 17.7k
        self.assertEqual(billing["total_collected_amount"], 17700.0)
        
        # Receivable: 0 + 5.9k + 35.4k = 41.3k
        self.assertEqual(billing["total_receivables"], 41300.0)

    def test_sector_performance(self):
        """Test cross-board join on sector level."""
        perf = get_sector_performance(self.deals_df, self.sample_work_orders)
        
        # Sectors should be Powerline, Mining, Renewables
        self.assertEqual(len(perf), 3)
        
        mining = next(item for item in perf if item["sector"] == "Mining")
        self.assertEqual(mining["deals"]["count"], 2)
        self.assertEqual(mining["work_orders"]["count"], 1)
        self.assertEqual(mining["work_orders"]["order_value_excl_gst"], 10000.0)

    def test_data_quality_summary(self):
        """Test data quality warning calculations."""
        dq = get_data_quality_summary(self.deals_df, self.work_orders_df)
        
        # 5 real deals, 3 work orders
        self.assertEqual(dq["deals"]["total_records"], 5)
        self.assertEqual(dq["work_orders"]["total_records"], 3)
        
        # Closure probability missing on 2 deals (Deal B is Won, Deal E is Open)
        # 2 / 5 = 40.0%
        self.assertIn("closure_probability", dq["deals"]["missing_fields"])
        self.assertEqual(dq["deals"]["missing_fields"]["closure_probability"]["count"], 2)
        self.assertEqual(dq["deals"]["missing_fields"]["closure_probability"]["percentage"], 40.0)

        # Check caveat sentence
        self.assertIn("40.0% of deal records are missing closure probability.", dq["key_caveats"])

    def test_leadership_summary(self):
        """Test compiled executive leadership KPIs."""
        lead = get_leadership_summary(self.deals_df, self.work_orders_df)
        
        self.assertEqual(lead["pipeline_kpis"]["total_portfolio_value"], 600000.0)
        self.assertEqual(lead["operations_kpis"]["total_work_orders"], 3)
        self.assertEqual(lead["billing_kpis"]["total_receivables"], 41300.0)
        self.assertTrue(len(lead["data_quality_caveats"]) > 0)
    def test_owner_performance(self):
        """Test calculation of sales performance by deal owner."""
        from app.analytics import get_owner_performance
        results = get_owner_performance(self.deals_df)
        self.assertTrue(len(results) > 0)
        for r in results:
            self.assertIn("owner", r)
            self.assertIn("total_value", r)
            self.assertIn("win_rate_percentage", r)

    def test_stale_deals(self):
        """Test identification of stale deals lacking close dates or overdue."""
        from app.analytics import get_stale_deals
        stale = get_stale_deals(self.deals_df)
        self.assertTrue(len(stale) > 0)
        for d in stale:
            self.assertIn("reasons", d)
            self.assertTrue(len(d["reasons"]) > 0)

    def test_top_opportunities(self):
        """Test retrieval of top active sales opportunities."""
        from app.analytics import get_top_opportunities
        opps = get_top_opportunities(self.deals_df, limit=2)
        self.assertEqual(len(opps), 2)
        self.assertTrue(opps[0]["value"] >= opps[1]["value"])

    def test_business_health_summary(self):
        """Test business health scoring dimensions and factors."""
        from app.analytics import get_business_health_summary
        health = get_business_health_summary(self.deals_df, self.work_orders_df)
        self.assertIn("overall_score", health)
        self.assertIn("dimensions", health)
        dims = health["dimensions"]
        self.assertIn("sales", dims)
        self.assertIn("operations", dims)
        self.assertIn("finance", dims)
        self.assertIn("data_quality", dims)
        self.assertTrue(0.0 <= health["overall_score"] <= 100.0)

    def test_deterministic_insights(self):
        """Test heuristics insight engine."""
        from app.analytics import get_deterministic_insights
        insights = get_deterministic_insights(self.deals_df, self.work_orders_df)
        self.assertTrue(len(insights) > 0)
        for ins in insights:
            self.assertIn("type", ins)
            self.assertIn("title", ins)
            self.assertIn("metric", ins)
            self.assertIn("description", ins)
    def test_revenue_by_sector(self):
        """Test calculation of closed-won revenue by sector."""
        from app.analytics import get_revenue_by_sector
        rev = get_revenue_by_sector(self.deals_df)
        self.assertEqual(rev["total_won_revenue"], 200000.0) # Deal B is Won (200k) in Powerline
        self.assertEqual(rev["won_deals_count"], 1)
        self.assertEqual(rev["top_sector"], "Powerline")

    def test_customer_pipeline(self):
        """Test aggregation of customer pipeline."""
        from app.analytics import get_customer_pipeline
        cust = get_customer_pipeline(self.deals_df)
        self.assertTrue(len(cust["ranked_customers"]) > 0)
        self.assertEqual(cust["total_pipeline"], 600000.0)

    def test_operational_risk_summary(self):
        """Test work orders operational risk analysis."""
        from app.analytics import get_operational_risk_summary
        risk = get_operational_risk_summary(self.work_orders_df)
        self.assertEqual(risk["total_work_orders"], 3)
        self.assertIn("at_risk_count", risk)
        self.assertIn("sector_risk", risk)

    def test_priority_opportunities_ranking(self):
        """
        Verify that get_priority_opportunities ranks high-value late-stage high-probability
        deals above huge early-stage low-probability deals.
        """
        from app.analytics import get_top_opportunities, get_priority_opportunities

        test_deals = pd.DataFrame([
            {
                "id": "1",
                "name": "Huge Early Deal",
                "deal_status": "Open",
                "closure_probability": "Low",
                "deal_value": 20000000.0,
                "deal_stage": "A. Inbound/Outbound Leads",
                "sector_service": "Mining",
            },
            {
                "id": "2",
                "name": "Late Stage High Prob Deal",
                "deal_status": "Open",
                "closure_probability": "High",
                "deal_value": 8000000.0,
                "deal_stage": "F. Negotiations",
                "sector_service": "Renewables",
            }
        ])

        # 1. Pure value ranking -> Huge Early Deal is #1
        top_by_val = get_top_opportunities(test_deals)
        self.assertEqual(top_by_val[0]["name"], "Huge Early Deal")
        self.assertEqual(top_by_val[1]["name"], "Late Stage High Prob Deal")

        # 2. Priority ranking -> Late Stage High Prob Deal is #1
        top_by_priority = get_priority_opportunities(test_deals)
        self.assertEqual(top_by_priority[0]["name"], "Late Stage High Prob Deal")
        self.assertEqual(top_by_priority[1]["name"], "Huge Early Deal")
        self.assertTrue(top_by_priority[0]["priority_score"] > top_by_priority[1]["priority_score"])

if __name__ == "__main__":
    unittest.main()

