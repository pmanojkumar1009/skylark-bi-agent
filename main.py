import sys
import os
import argparse
from typing import Dict, Any, List
import pandas as pd

from app.config import (
    DEALS_BOARD_ID,
    WORK_ORDERS_BOARD_ID,
)

from app.monday_client import MondayClient

from app.data_processor import (
    DEALS_COLUMNS,
    WORK_ORDER_COLUMNS,
    process_board,
    create_dataframe,
)

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

from app.ai_agent import SkylarkBIAgent, LLMClient


def format_rupees(val: float) -> str:
    """Format float values as Indian Rupees (₹) with thousand separators."""
    return f"₹{val:,.2f}"


def print_dashboard_report(
    pipe_sum, pipe_sec, pipe_stg, deal_stat, wo_sum, billing_sum, sector_perf, dq_sum, lead_sum
):
    """Print the formatted analytical BI report to console."""
    print("\n" + "=" * 70)
    print("BUSINESS INTELLIGENCE REPORT")
    print("=" * 70)

    # --- A. PIPELINE SUMMARY ---
    print("\n" + "-" * 50)
    print("A. PIPELINE SUMMARY")
    print("-" * 50)
    print(f"Total Portfolio Deals:       {pipe_sum['total_deals']}")
    print(f"Total Portfolio Value:       {format_rupees(pipe_sum['total_portfolio_value'])}")
    print(f"Active Open Deals:           {pipe_sum['open_deals_count']}")
    print(f"Active Open Pipeline Value:  {format_rupees(pipe_sum['open_pipeline_value'])}")
    print(f"On Hold Deals Count:         {pipe_sum['on_hold_deals_count']}")
    print(f"On Hold Pipeline Value:      {format_rupees(pipe_sum['on_hold_pipeline_value'])}")
    print(f"Closed Won Deals Count:      {pipe_sum['won_deals_count']}")
    print(f"Closed Won Portfolio Value:  {format_rupees(pipe_sum['won_deals_value'])}")
    print(f"Closed Dead/Lost Deals:      {pipe_sum['dead_deals_count']}")
    print(f"Closed Dead/Lost Value:      {format_rupees(pipe_sum['dead_deals_value'])}")
    print("\nASSUMPTION-BASED PIPELINE PROBABILITY (ESTIMATES ONLY):")
    print(f"  Active Deals with Explicit Probability: {pipe_sum['deals_with_probability']}")
    print(f"  Active Deals with Missing Probability:  {pipe_sum['deals_missing_probability']}")
    print(f"  Average Active Closure Probability:     {pipe_sum['avg_closure_probability'] * 100:.1f}%")
    print(f"  Weighted Pipeline Value (Est.):        {format_rupees(pipe_sum['weighted_pipeline_value'])}")
    print("  *Caveat: Deals missing probability are excluded from weighted pipeline.")

    # --- B. PIPELINE BY SECTOR ---
    print("\n" + "-" * 50)
    print("B. PIPELINE BY SECTOR / SERVICE")
    print("-" * 50)
    print(f"{'Sector / Service':<25} | {'Count':<5} | {'Portfolio Value':<18} | {'Open Count':<10} | {'Weighted Val (Est.)':<18}")
    print("-" * 83)
    for row in pipe_sec:
        print(
            f"{row['sector']:<25} | {row['deal_count']:<5} | "
            f"{format_rupees(row['portfolio_value']):<18} | {row['open_deal_count']:<10} | "
            f"{format_rupees(row['weighted_pipeline_value']):<18}"
        )

    # --- C. PIPELINE BY DEAL STAGE ---
    print("\n" + "-" * 50)
    print("C. PIPELINE BY DEAL STAGE")
    print("-" * 50)
    print(f"{'Deal Stage':<30} | {'Count':<5} | {'Pipeline Value':<18} | {'% of Total':<10}")
    print("-" * 70)
    for row in pipe_stg:
        print(
            f"{row['stage'][:30]:<30} | {row['deal_count']:<5} | "
            f"{format_rupees(row['pipeline_value']):<18} | {row['percentage_of_total']:.1f}%"
        )

    # --- D. DEAL STATUS ANALYSIS ---
    print("\n" + "-" * 50)
    print("D. DEAL STATUS ANALYSIS")
    print("-" * 50)
    print(f"{'Deal Status':<15} | {'Count':<5} | {'% Count':<8} | {'Pipeline Value':<18} | {'% Value':<8}")
    print("-" * 62)
    for row in deal_stat:
        print(
            f"{row['status']:<15} | {row['deal_count']:<5} | {row['percentage_of_count']:.1f}%   | "
            f"{format_rupees(row['pipeline_value']):<18} | {row['percentage_of_value']:.1f}%"
        )

    # --- E. WORK ORDER OPERATIONAL SUMMARY ---
    print("\n" + "-" * 50)
    print("E. WORK ORDER OPERATIONAL SUMMARY")
    print("-" * 50)
    print(f"Total Work Orders:      {wo_sum['total_work_orders']}")
    print(f"Completed Work Orders:  {wo_sum['completed_count']}")
    print(f"Open Work Orders:       {wo_sum['open_count']}")
    print("\nEXECUTION STATUS DISTRIBUTION:")
    for k, v in wo_sum["execution_status_distribution"].items():
        print(f"  - {k:<30}: {v['count']:<3} ({v['percentage']:.1f}%)")

    # --- F. BILLING ANALYSIS ---
    print("\n" + "-" * 50)
    print("F. BILLING & FINANCIAL ANALYSIS")
    print("-" * 50)
    print(f"Total Order Value (Excl. GST):       {format_rupees(billing_sum['total_order_value_excl_gst'])}")
    print(f"Total Order Value (Incl. GST):       {format_rupees(billing_sum['total_order_value_incl_gst'])}")
    print(f"Total Billed Value (Excl. GST):      {format_rupees(billing_sum['total_billed_value_excl_gst'])}")
    print(f"Total Billed Value (Incl. GST):      {format_rupees(billing_sum['total_billed_value_incl_gst'])}")
    print(f"Total Collected Revenue (Incl. GST): {format_rupees(billing_sum['total_collected_amount'])}")
    print(f"Total Outstanding Receivables:       {format_rupees(billing_sum['total_receivables'])}")
    print(f"Total Amount to be Billed (Excl.):   {format_rupees(billing_sum['total_amount_to_bill_excl_gst'])}")
    print(f"Total Amount to be Billed (Incl.):   {format_rupees(billing_sum['total_amount_to_bill_incl_gst'])}")
    print(f"Billed Percentage of Contract (Excl): {billing_sum['billed_percentage_excl']:.1f}%")
    print(f"Collection Percentage of Billed:     {billing_sum['collected_percentage_of_billed']:.1f}%")
    print("\nBILLING STATUS DISTRIBUTION:")
    for k, v in billing_sum["billing_status_distribution"].items():
        print(f"  - {k:<25}: {v['count']:<3} ({v['percentage']:.1f}%)")

    # --- G. SECTOR PERFORMANCE / CROSS-BOARD ---
    print("\n" + "-" * 50)
    print("G. SECTOR PERFORMANCE (CROSS-BOARD ANALYSIS)")
    print("-" * 50)
    header = f"{'Sector':<20} | {'Deals (Open/Tot)':<17} | {'Deal Val (Tot)':<16} | {'WO Count':<8} | {'WO Value (Excl)':<16} | {'Billed Excl':<14} | {'Receivables':<14}"
    print(header)
    print("-" * len(header))
    for sp in sector_perf:
        deals_info = f"{sp['deals']['open_count']}/{sp['deals']['count']}"
        print(
            f"{sp['sector'][:20]:<20} | {deals_info:<17} | "
            f"{format_rupees(sp['deals']['portfolio_value']):<16} | {sp['work_orders']['count']:<8} | "
            f"{format_rupees(sp['work_orders']['order_value_excl_gst']):<16} | "
            f"{format_rupees(sp['work_orders']['billed_value_excl_gst']):<14} | "
            f"{format_rupees(sp['work_orders']['receivables']):<14}"
        )

    # --- H. DATA QUALITY SUMMARY ---
    print("\n" + "-" * 50)
    print("H. DATA QUALITY SUMMARY")
    print("-" * 50)
    print("CRITICAL MISSING DATA CAVEATS:")
    for caveat in dq_sum["key_caveats"]:
        print(f"  [WARNING] {caveat}")
    
    print("\nDEALS BOARD FIELD COMPLETENESS AUDIT:")
    for col, data in sorted(dq_sum["deals"]["missing_fields"].items(), key=lambda x: x[1]["percentage"], reverse=True)[:5]:
        print(f"  - Column '{col}' is missing in {data['count']} records ({data['percentage']:.1f}%)")
        
    print("\nWORK ORDERS BOARD FIELD COMPLETENESS AUDIT:")
    for col, data in sorted(dq_sum["work_orders"]["missing_fields"].items(), key=lambda x: x[1]["percentage"], reverse=True)[:5]:
        print(f"  - Column '{col}' is missing in {data['count']} records ({data['percentage']:.1f}%)")
        
    if dq_sum["deals"]["anomalies"] or dq_sum["work_orders"]["anomalies"]:
        print("\nDETECTED DATA ANOMALIES:")
        for anomaly in dq_sum["deals"]["anomalies"] + dq_sum["work_orders"]["anomalies"]:
            print(f"  - {anomaly}")

    # --- I. LEADERSHIP SUMMARY ---
    print("\n" + "-" * 50)
    print("I. LEADERSHIP SUMMARY (EXECUTIVE OVERVIEW)")
    print("-" * 50)
    print("KEY PERFORMANCE INDICATORS:")
    print(f"  - Total Active Pipeline Value:     {format_rupees(lead_sum['pipeline_kpis']['open_pipeline_value'])}")
    print(f"  - Total Weighted Pipeline (Est.):  {format_rupees(lead_sum['pipeline_kpis']['weighted_pipeline_value'])}")
    print(f"  - Closed Won Value (Portfolio):    {format_rupees(lead_sum['pipeline_kpis']['won_deals_value'])}")
    print(f"  - Operations Completion Rate:      {lead_sum['operations_kpis']['completion_rate_percentage']:.1f}% "
          f"({lead_sum['operations_kpis']['completed_work_orders']}/{lead_sum['operations_kpis']['total_work_orders']} work orders completed)")
    print(f"  - Total Billed Value (Contract):   {format_rupees(lead_sum['billing_kpis']['total_billed_value_excl_gst'])}")
    print(f"  - Total Outstanding Receivables:   {format_rupees(lead_sum['billing_kpis']['total_receivables'])}")
    print(f"  - Total Revenue Collected:         {format_rupees(lead_sum['billing_kpis']['total_collected_amount'])}")
    print(f"  - Collection-to-Billed Rate:       {lead_sum['billing_kpis']['collected_percentage_of_billed']:.1f}%")
    
    print("\nTOP MARKET SEGMENTS:")
    print("  - By Open Pipeline:")
    for s in lead_sum["market_segments"]["top_sectors_by_open_pipeline"]:
        print(f"    * {s['sector']}: {format_rupees(s['open_pipeline_value'])}")
    print("  - By Operations Volume (Work Orders):")
    for s in lead_sum["market_segments"]["top_sectors_by_work_orders"]:
        print(f"    * {s['sector']}: {s['work_order_count']} work orders")

    print("\nNOTABLE RISKS & ALERTS:")
    for risk in lead_sum["notable_risks"]:
        print(f"  [RISK] {risk}")
    if not lead_sum["notable_risks"]:
        print("  - No immediate high-risk alerts detected.")

    print("\n" + "=" * 70)


def main():
    # Setup argument parser
    parser = argparse.ArgumentParser(description="Skylark Drones Business Intelligence Agent")
    parser.add_argument("--query", type=str, help="Run a single natural-language query and exit immediately.")
    args = parser.parse_args()

    print("=" * 70)
    print("SKYLARK BI AGENT - DATA ENGINE & CONVERSATIONAL AI")
    print("=" * 70)

    client = MondayClient()

    # --------------------------------------------------------
    # 1. Fetch Deals
    # --------------------------------------------------------
    print("\n[1/3] Fetching Deals from Monday.com...")
    deals_items = client.get_deals()
    deals = process_board(deals_items, DEALS_COLUMNS)
    deals_df = create_dataframe(deals)
    print(f"✓ Deals loaded: {len(deals_df)}")

    # --------------------------------------------------------
    # 2. Fetch Work Orders
    # --------------------------------------------------------
    print("\n[2/3] Fetching Work Orders from Monday.com...")
    work_order_items = client.get_work_orders()
    work_orders = process_board(work_order_items, WORK_ORDER_COLUMNS)
    work_orders_df = create_dataframe(work_orders)
    print(f"✓ Work Orders loaded: {len(work_orders_df)}")

    if deals_df.empty or work_orders_df.empty:
        print("\n[!] Error: Unable to continue. One of the datasets is empty.")
        return

    # --------------------------------------------------------
    # Initialize Agent
    # --------------------------------------------------------
    print("\n[3/3] Initializing Conversational BI Agent...")
    llm_client = LLMClient()
    agent = SkylarkBIAgent(deals_df, work_orders_df, llm_client=llm_client)
    print("✓ BI Agent ready.")

    # --------------------------------------------------------
    # Single Query Mode
    # --------------------------------------------------------
    if args.query:
        print(f"\nQUERY: '{args.query}'")
        print("-" * 70)
        response = agent.ask(args.query)
        print("\nAGENT RESPONSE:")
        print(response)
        print("\n" + "=" * 70)
        return

    # --------------------------------------------------------
    # Dashboard & Interactive Mode
    # --------------------------------------------------------
    # First, run analytics for the dashboard
    pipe_sum = get_pipeline_summary(deals_df)
    pipe_sec = get_pipeline_by_sector(deals_df)
    pipe_stg = get_pipeline_by_stage(deals_df)
    deal_stat = get_deal_status_summary(deals_df)
    wo_sum = get_work_order_summary(work_orders_df)
    billing_sum = get_billing_summary(work_orders_df)
    sector_perf = get_sector_performance(deals_df, work_orders_df)
    dq_sum = get_data_quality_summary(deals_df, work_orders_df)
    lead_sum = get_leadership_summary(deals_df, work_orders_df)

    print_dashboard_report(
        pipe_sum, pipe_sec, pipe_stg, deal_stat, wo_sum, billing_sum, sector_perf, dq_sum, lead_sum
    )
    print("DATA PIPELINE & ANALYTICS LAYER SUCCESSFUL ✓")
    print("=" * 70)

    # Start Interactive Session
    print("\n" + "=" * 70)
    print("INTERACTIVE CONVERSATIONAL BI AGENT SESSION")
    print("=" * 70)
    print("You can now ask natural-language questions about deals, operations, billing,")
    print("or sectors (e.g. 'How is Mining performing?').")
    print("Type 'exit' or 'quit' to terminate the session.")
    print("-" * 70)

    while True:
        try:
            query = input("\nQuery > ").strip()
            if not query:
                continue
            if query.lower() in ["exit", "quit"]:
                print("Closing interactive BI session. Goodbye!")
                break
                
            print("\nProcessing...")
            response = agent.ask(query)
            print("\nAGENT RESPONSE:")
            print(response)
            print("\n" + "-" * 70)
            
        except KeyboardInterrupt:
            print("\nSession interrupted. Goodbye!")
            break
        except Exception as e:
            print(f"\nAn error occurred during query execution: {e}")


if __name__ == "__main__":
    main()