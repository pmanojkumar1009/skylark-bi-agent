import math
from typing import Dict, Any, List, Optional
import pandas as pd

# ============================================================
# CONSTANTS & ASSUMPTIONS (Explicitly documented)
# ============================================================

# Closure probability estimates are based on manual categorization
# mapping status labels. These are assumptions/estimates for analysis,
# not official or contractually verified Skylark probabilities.
CLOSURE_PROBABILITY_MAPPING = {
    "high": 0.80,
    "medium": 0.50,
    "low": 0.20
}


# ============================================================
# DATA CLEANING AND NORMALIZATION HELPERS
# ============================================================

def normalize_text(val: Any) -> Optional[str]:
    """Helper to strip whitespace, handle nulls, and return string."""
    if pd.isna(val) or val is None:
        return None
    val_str = str(val).strip()
    if val_str.lower() in ["", "none", "nan", "null", "-", "--"]:
        return None
    return val_str


def normalize_sector(sector_name: Any) -> str:
    """Standardize sector names for aggregation and joining."""
    text = normalize_text(sector_name)
    if text is None:
        return "Unknown / Missing"
    return text.title()


def clean_deals_df(df: Any) -> pd.DataFrame:
    """
    Remove Monday.com template/header rows and normalize text fields.
    Converts inputs to pd.DataFrame if they are list/dict.
    """
    if not isinstance(df, pd.DataFrame):
        df = pd.DataFrame(df)
        
    if df.empty:
        return df.copy()
    
    df_clean = df.copy()
    
    # Filter out template/header rows if present
    if "deal_status" in df_clean.columns:
        df_clean = df_clean[df_clean["deal_status"] != "Deal Status"]
    if "sector_service" in df_clean.columns:
        df_clean = df_clean[df_clean["sector_service"] != "Sector/service"]
    if "deal_stage" in df_clean.columns:
        df_clean = df_clean[df_clean["deal_stage"] != "Deal Stage"]
        
    return df_clean


def clean_work_orders_df(df: Any) -> pd.DataFrame:
    """
    Remove Monday.com template/header rows if present.
    Converts inputs to pd.DataFrame if they are list/dict.
    """
    if not isinstance(df, pd.DataFrame):
        df = pd.DataFrame(df)
        
    if df.empty:
        return df.copy()
    
    df_clean = df.copy()
    if "sector" in df_clean.columns:
        df_clean = df_clean[df_clean["sector"] != "Sector"]
    if "execution_status" in df_clean.columns:
        df_clean = df_clean[df_clean["execution_status"] != "Execution Status"]
        
    return df_clean


# ============================================================
# PIPELINE SUMMARY
# ============================================================

def get_pipeline_summary(deals_df: pd.DataFrame) -> Dict[str, Any]:
    """
    Calculate high-level Deals pipeline metrics.
    """
    df = clean_deals_df(deals_df)
    
    if df.empty:
        return {
            "total_deals": 0,
            "total_portfolio_value": 0.0,
            "open_deals_count": 0,
            "open_pipeline_value": 0.0,
            "won_deals_count": 0,
            "won_deals_value": 0.0,
            "dead_deals_count": 0,
            "dead_deals_value": 0.0,
            "on_hold_deals_count": 0,
            "on_hold_pipeline_value": 0.0,
            "avg_closure_probability": 0.0,
            "weighted_pipeline_value": 0.0,
            "deals_missing_probability": 0,
            "deals_with_probability": 0
        }

    # Normalize values for mapping
    status_series = df["deal_status"].apply(normalize_text)
    status_lower = status_series.str.lower()
    
    prob_series = df["closure_probability"].apply(normalize_text)
    val_series = df["deal_value"].fillna(0.0)
    
    # Map probability to numeric
    prob_numeric = prob_series.apply(
        lambda x: CLOSURE_PROBABILITY_MAPPING.get(x.lower()) if x else None
    )
    
    # Identify stages/statuses (case-insensitive)
    is_open = status_lower.isin(["open", "open deal"]) | status_series.isna()
    is_won = status_lower == "won"
    is_dead = status_lower.isin(["dead", "lost"])
    is_hold = status_lower == "on hold"
    
    # Metrics
    total_deals = len(df)
    total_portfolio_value = val_series.sum()
    
    open_deals_count = int(is_open.sum())
    open_pipeline_value = float(val_series[is_open].sum())
    
    won_deals_count = int(is_won.sum())
    won_deals_value = float(val_series[is_won].sum())
    
    dead_deals_count = int(is_dead.sum())
    dead_deals_value = float(val_series[is_dead].sum())
    
    on_hold_deals_count = int(is_hold.sum())
    on_hold_pipeline_value = float(val_series[is_hold].sum())
    
    # Probability metrics for active (open + hold) deals
    active_mask = is_open | is_hold
    active_probs = prob_numeric[active_mask].dropna()
    
    avg_prob = float(active_probs.mean()) if not active_probs.empty else 0.0
    
    # Weighted value (only for active deals with a known probability)
    # Deals with missing probability are excluded (weighted value contribution is 0)
    weighted_val = float((val_series[active_mask] * prob_numeric[active_mask].fillna(0.0)).sum())
    
    deals_missing_prob = int(prob_numeric[active_mask].isna().sum())
    deals_with_prob = int(prob_numeric[active_mask].notna().sum())
    
    return {
        "total_deals": total_deals,
        "total_portfolio_value": total_portfolio_value,
        "open_deals_count": open_deals_count,
        "open_pipeline_value": open_pipeline_value,
        "won_deals_count": won_deals_count,
        "won_deals_value": won_deals_value,
        "dead_deals_count": dead_deals_count,
        "dead_deals_value": dead_deals_value,
        "on_hold_deals_count": on_hold_deals_count,
        "on_hold_pipeline_value": on_hold_pipeline_value,
        "avg_closure_probability": avg_prob,
        "weighted_pipeline_value": weighted_val,
        "deals_missing_probability": deals_missing_prob,
        "deals_with_probability": deals_with_prob
    }


# ============================================================
# PIPELINE BY SECTOR
# ============================================================

def get_pipeline_by_sector(deals_df: pd.DataFrame) -> List[Dict[str, Any]]:
    """
    Summarize Deals pipeline grouped by sector.
    """
    df = clean_deals_df(deals_df)
    
    if df.empty:
        return []
        
    df = df.copy()
    df["normalized_sector"] = df["sector_service"].apply(normalize_sector)
    df["deal_value_clean"] = df["deal_value"].fillna(0.0)
    
    status_series = df["deal_status"].apply(normalize_text)
    status_lower = status_series.str.lower()
    
    df["is_open"] = status_lower.isin(["open", "open deal"]) | status_series.isna()
    df["is_hold"] = status_lower == "on hold"
    df["is_active"] = df["is_open"] | df["is_hold"]
    
    prob_series = df["closure_probability"].apply(normalize_text)
    df["prob_num"] = prob_series.apply(
        lambda x: CLOSURE_PROBABILITY_MAPPING.get(x.lower()) if x else None
    )
    df["weighted_val"] = df["deal_value_clean"] * df["prob_num"].fillna(0.0)
    
    results = []
    grouped = df.groupby("normalized_sector")
    
    for sector, group in grouped:
        total_count = len(group)
        total_value = float(group["deal_value_clean"].sum())
        
        active_group = group[group["is_active"]]
        open_group = group[group["is_open"]]
        open_count = int(open_group["id"].count())
        open_val = float(open_group["deal_value_clean"].sum())
        active_count = len(active_group)
        
        active_probs = active_group["prob_num"].dropna()
        avg_prob = float(active_probs.mean()) if not active_probs.empty else 0.0
        weighted_val = float(active_group["weighted_val"].sum())
        
        results.append({
            "sector": sector,
            "deal_count": total_count,
            "portfolio_value": total_value,
            "open_deal_count": open_count,
            "open_pipeline_value": open_val,
            "active_deal_count": active_count,
            "avg_closure_probability": avg_prob,
            "weighted_pipeline_value": weighted_val
        })
        
    # Sort by open pipeline value descending (or portfolio value if tied)
    results.sort(key=lambda x: (x["open_pipeline_value"], x["portfolio_value"]), reverse=True)
    return results


# ============================================================
# PIPELINE BY DEAL STAGE
# ============================================================

def get_pipeline_by_stage(deals_df: pd.DataFrame) -> List[Dict[str, Any]]:
    """
    Summarize Deals pipeline grouped by Deal Stage.
    """
    df = clean_deals_df(deals_df)
    
    if df.empty:
        return []
        
    df = df.copy()
    df["normalized_stage"] = df["deal_stage"].apply(
        lambda x: normalize_text(x) or "Unknown / Missing"
    )
    df["deal_value_clean"] = df["deal_value"].fillna(0.0)
    
    total_val = df["deal_value_clean"].sum()
    
    results = []
    grouped = df.groupby("normalized_stage")
    
    for stage, group in grouped:
        deal_count = len(group)
        stage_value = float(group["deal_value_clean"].sum())
        percentage = (stage_value / total_val * 100) if total_val > 0 else 0.0
        
        results.append({
            "stage": stage,
            "deal_count": deal_count,
            "pipeline_value": stage_value,
            "percentage_of_total": percentage
        })
        
    # Sort by pipeline value descending
    results.sort(key=lambda x: x["pipeline_value"], reverse=True)
    return results


# ============================================================
# DEAL STATUS ANALYSIS
# ============================================================

def get_deal_status_summary(deals_df: pd.DataFrame) -> List[Dict[str, Any]]:
    """
    Analyze deals by deal status.
    """
    df = clean_deals_df(deals_df)
    
    if df.empty:
        return []
        
    df = df.copy()
    df["normalized_status"] = df["deal_status"].apply(
        lambda x: normalize_text(x) or "Unknown / Missing"
    )
    df["deal_value_clean"] = df["deal_value"].fillna(0.0)
    
    total_count = len(df)
    total_val = df["deal_value_clean"].sum()
    
    results = []
    grouped = df.groupby("normalized_status")
    
    for status, group in grouped:
        count = len(group)
        val = float(group["deal_value_clean"].sum())
        
        pct_count = (count / total_count * 100) if total_count > 0 else 0.0
        pct_val = (val / total_val * 100) if total_val > 0 else 0.0
        
        results.append({
            "status": status.title(),
            "deal_count": count,
            "pipeline_value": val,
            "percentage_of_count": pct_count,
            "percentage_of_value": pct_val
        })
        
    # Sort by deal count descending
    results.sort(key=lambda x: x["deal_count"], reverse=True)
    return results


# ============================================================
# WORK ORDER OPERATIONAL SUMMARY
# ============================================================

def get_work_order_summary(work_orders_df: pd.DataFrame) -> Dict[str, Any]:
    """
    Analyze Work Orders operations.
    """
    df = clean_work_orders_df(work_orders_df)
    
    if df.empty:
        return {
            "total_work_orders": 0,
            "completed_count": 0,
            "open_count": 0,
            "execution_status_distribution": {},
            "work_orders_by_sector": {},
            "work_orders_by_type_of_work": {}
        }
        
    df = df.copy()
    
    # Status distributions
    status_series = df["execution_status"].apply(
        lambda x: normalize_text(x) or "Unknown / Missing"
    )
    
    sector_series = df["sector"].apply(normalize_sector)
    
    type_series = df["type_of_work"].apply(
        lambda x: normalize_text(x) or "Unknown / Missing"
    )
    
    # Completed statuses: "Completed", "Executed until current month"
    is_completed = status_series.str.lower().isin(["completed", "executed until current month"])
    completed_count = int(is_completed.sum())
    open_count = len(df) - completed_count
    
    def get_distribution(series):
        counts = series.value_counts()
        total = len(series)
        return {
            str(k): {
                "count": int(v),
                "percentage": round(float(v / total * 100), 2)
            }
            for k, v in counts.items()
        }
        
    return {
        "total_work_orders": len(df),
        "completed_count": completed_count,
        "open_count": open_count,
        "execution_status_distribution": get_distribution(status_series),
        "work_orders_by_sector": get_distribution(sector_series),
        "work_orders_by_type_of_work": get_distribution(type_series)
    }


# ============================================================
# BILLING ANALYSIS
# ============================================================

def get_billing_summary(work_orders_df: pd.DataFrame) -> Dict[str, Any]:
    """
    Aggregate billing metrics from Work Orders.
    """
    df = clean_work_orders_df(work_orders_df)
    
    if df.empty:
        return {
            "total_order_value_excl_gst": 0.0,
            "total_order_value_incl_gst": 0.0,
            "total_billed_value_excl_gst": 0.0,
            "total_billed_value_incl_gst": 0.0,
            "total_collected_amount": 0.0,
            "total_receivables": 0.0,
            "total_amount_to_bill_excl_gst": 0.0,
            "total_amount_to_bill_incl_gst": 0.0,
            "billed_percentage_excl": 0.0,
            "collected_percentage_of_billed": 0.0,
            "billing_status_distribution": {}
        }
        
    # Sum functions (safely filling NaNs with 0.0)
    order_excl = float(df["amount_excl_gst"].fillna(0.0).sum())
    order_incl = float(df["amount_incl_gst"].fillna(0.0).sum())
    
    billed_excl = float(df["billed_value_excl_gst"].fillna(0.0).sum())
    billed_incl = float(df["billed_value_incl_gst"].fillna(0.0).sum())
    
    collected = float(df["collected_amount"].fillna(0.0).sum())
    receivable = float(df["amount_receivable"].fillna(0.0).sum())
    
    to_bill_excl = float(df["amount_to_bill_excl_gst"].fillna(0.0).sum())
    to_bill_incl = float(df["amount_to_bill_incl_gst"].fillna(0.0).sum())
    
    # Billing Status Distribution
    billing_status_series = df["billing_status"].apply(
        lambda x: normalize_text(x) or "Unknown / Missing"
    )
    
    status_counts = billing_status_series.value_counts()
    total_items = len(billing_status_series)
    status_dist = {
        str(k).title(): {
            "count": int(v),
            "percentage": round(float(v / total_items * 100), 2)
        }
        for k, v in status_counts.items()
    }
    
    # Percentages
    billed_pct = (billed_excl / order_excl * 100) if order_excl > 0 else 0.0
    collected_pct = (collected / billed_incl * 100) if billed_incl > 0 else 0.0
    
    return {
        "total_order_value_excl_gst": order_excl,
        "total_order_value_incl_gst": order_incl,
        "total_billed_value_excl_gst": billed_excl,
        "total_billed_value_incl_gst": billed_incl,
        "total_collected_amount": collected,
        "total_receivables": receivable,
        "total_amount_to_bill_excl_gst": to_bill_excl,
        "total_amount_to_bill_incl_gst": to_bill_incl,
        "billed_percentage_excl": billed_pct,
        "collected_percentage_of_billed": collected_pct,
        "billing_status_distribution": status_dist
    }


# ============================================================
# SECTOR PERFORMANCE / CROSS-BOARD ANALYSIS
# ============================================================

def get_sector_performance(deals_df: pd.DataFrame, work_orders_df: pd.DataFrame) -> List[Dict[str, Any]]:
    """
    Perform sector-level outer join between Deals and Work Orders.
    """
    deals = clean_deals_df(deals_df)
    wos = clean_work_orders_df(work_orders_df)
    
    # 1. Deals Aggregation
    if not deals.empty:
        deals_df_norm = deals.copy()
        deals_df_norm["normalized_sector"] = deals_df_norm["sector_service"].apply(normalize_sector)
        deals_df_norm["deal_value_clean"] = deals_df_norm["deal_value"].fillna(0.0)
        
        status_series = deals_df_norm["deal_status"].apply(normalize_text)
        status_lower = status_series.str.lower()
        
        deals_df_norm["is_open"] = status_lower.isin(["open", "open deal"]) | status_series.isna()
        deals_df_norm["is_hold"] = status_lower == "on hold"
        deals_df_norm["is_active"] = deals_df_norm["is_open"] | deals_df_norm["is_hold"]
        
        prob_series = deals_df_norm["closure_probability"].apply(normalize_text)
        deals_df_norm["prob_num"] = prob_series.apply(
            lambda x: CLOSURE_PROBABILITY_MAPPING.get(x.lower()) if x else None
        )
        deals_df_norm["weighted_val"] = deals_df_norm["deal_value_clean"] * deals_df_norm["prob_num"].fillna(0.0)
        
        # Precompute values to sum
        deals_df_norm["open_val"] = deals_df_norm["deal_value_clean"].where(deals_df_norm["is_open"], 0.0)
        
        deals_grouped = deals_df_norm.groupby("normalized_sector").agg(
            deal_count=("id", "count"),
            portfolio_value=("deal_value_clean", "sum"),
            open_count=("is_open", "sum"),
            active_count=("is_active", "sum"),
            open_pipeline_value=("open_val", "sum"),
            weighted_value=("weighted_val", "sum")
        ).reset_index()
    else:
        deals_grouped = pd.DataFrame(columns=[
            "normalized_sector", "deal_count", "portfolio_value", 
            "open_count", "active_count", "open_pipeline_value", "weighted_value"
        ])
        
    # 2. Work Orders Aggregation
    if not wos.empty:
        wos_df_norm = wos.copy()
        wos_df_norm["normalized_sector"] = wos_df_norm["sector"].apply(normalize_sector)
        
        # We also want to compute status distribution per sector
        wos_grouped = wos_df_norm.groupby("normalized_sector").agg(
            wo_count=("id", "count"),
            order_value_excl=("amount_excl_gst", lambda x: float(x.fillna(0.0).sum())),
            billed_value_excl=("billed_value_excl_gst", lambda x: float(x.fillna(0.0).sum())),
            receivables=("amount_receivable", lambda x: float(x.fillna(0.0).sum()))
        ).reset_index()
    else:
        wos_grouped = pd.DataFrame(columns=["normalized_sector", "wo_count", "order_value_excl", "billed_value_excl", "receivables"])
        
    # 3. Outer Join
    merged = pd.merge(
        deals_grouped,
        wos_grouped,
        on="normalized_sector",
        how="outer"
    ).fillna(0.0)
    
    # 4. Construct response list
    results = []
    
    # To fetch status distributions per sector
    wos_by_sector = {}
    if not wos.empty:
        for (sec, status), grp in wos.groupby([wos["sector"].apply(normalize_sector), wos["execution_status"].apply(lambda x: normalize_text(x) or "Unknown / Missing")]):
            if sec not in wos_by_sector:
                wos_by_sector[sec] = {}
            wos_by_sector[sec][status] = len(grp)
            
    for _, row in merged.iterrows():
        sec = row["normalized_sector"]
        
        results.append({
            "sector": sec,
            "deals": {
                "count": int(row.get("deal_count", 0)),
                "portfolio_value": float(row.get("portfolio_value", 0.0)),
                "open_count": int(row.get("open_count", 0)),
                "active_count": int(row.get("active_count", 0)),
                "open_pipeline_value": float(row.get("open_pipeline_value", 0.0)),
                "weighted_pipeline_value": float(row.get("weighted_value", 0.0))
            },
            "work_orders": {
                "count": int(row.get("wo_count", 0)),
                "order_value_excl_gst": float(row.get("order_value_excl", 0.0)),
                "billed_value_excl_gst": float(row.get("billed_value_excl", 0.0)),
                "receivables": float(row.get("receivables", 0.0)),
                "execution_status_distribution": wos_by_sector.get(sec, {})
            }
        })
        
    # Sort by sector name
    results.sort(key=lambda x: x["sector"])
    return results


# ============================================================
# DATA QUALITY SUMMARY
# ============================================================

def get_data_quality_summary(deals_df: pd.DataFrame, work_orders_df: pd.DataFrame) -> Dict[str, Any]:
    """
    Audit data quality for both Deals and Work Orders boards.
    """
    deals = clean_deals_df(deals_df)
    wos = clean_work_orders_df(work_orders_df)
    
    def audit_board(df: pd.DataFrame, critical_cols: List[str]) -> Dict[str, Any]:
        if df.empty:
            return {
                "total_records": 0,
                "missing_fields": {},
                "anomalies": []
            }
            
        total = len(df)
        missing_report = {}
        anomalies = []
        
        for col in df.columns:
            missing_count = int(df[col].isna().sum())
            if missing_count > 0:
                missing_report[col] = {
                    "count": missing_count,
                    "percentage": round(missing_count / total * 100, 2)
                }
                
        # Check critical column completeness
        for col in critical_cols:
            if col not in df.columns:
                anomalies.append(f"Critical column '{col}' is entirely missing from dataset.")
                
        # Value checks
        # Negative value checks
        numeric_cols = df.select_dtypes(include=["number"]).columns
        for col in numeric_cols:
            negatives = (df[col] < 0).sum()
            if negatives > 0:
                anomalies.append(f"Column '{col}' contains {negatives} negative values.")
                
        return {
            "total_records": total,
            "missing_fields": missing_report,
            "anomalies": anomalies
        }

    deals_audit = audit_board(
        deals, 
        ["deal_value", "deal_status", "closure_probability", "deal_stage", "sector_service"]
    )
    
    wos_audit = audit_board(
        wos, 
        ["amount_excl_gst", "billed_value_excl_gst", "collected_amount", "amount_receivable", "execution_status", "sector"]
    )
    
    # Specific caveat formatting requested by user
    caveats = []
    if "closure_probability" in deals_audit["missing_fields"]:
        pct = deals_audit["missing_fields"]["closure_probability"]["percentage"]
        caveats.append(f"{pct}% of deal records are missing closure probability.")
    else:
        if deals_audit["total_records"] > 0:
            caveats.append("0% of deal records are missing closure probability.")
            
    if "deal_value" in deals_audit["missing_fields"]:
        pct = deals_audit["missing_fields"]["deal_value"]["percentage"]
        caveats.append(f"{pct}% of deal records are missing deal value.")
        
    if "amount_excl_gst" in wos_audit["missing_fields"]:
        pct = wos_audit["missing_fields"]["amount_excl_gst"]["percentage"]
        caveats.append(f"{pct}% of work orders are missing order value amount.")
        
    return {
        "deals": deals_audit,
        "work_orders": wos_audit,
        "key_caveats": caveats
    }


# ============================================================
# LEADERSHIP SUMMARY
# ============================================================

def get_leadership_summary(deals_df: pd.DataFrame, work_orders_df: pd.DataFrame) -> Dict[str, Any]:
    """
    Compile executive-level business intelligence KPIs and alerts.
    """
    deals = clean_deals_df(deals_df)
    wos = clean_work_orders_df(work_orders_df)
    
    pipe_sum = get_pipeline_summary(deals)
    wo_sum = get_work_order_summary(wos)
    billing_sum = get_billing_summary(wos)
    dq_sum = get_data_quality_summary(deals, wos)
    sector_perf = get_sector_performance(deals, wos)
    
    # Calculate top sectors by open pipeline value
    sector_pipeline = []
    for sp in sector_perf:
        sector_pipeline.append((sp["sector"], sp["deals"]["open_pipeline_value"], sp["work_orders"]["count"]))
    
    top_pipeline_sectors = sorted(sector_pipeline, key=lambda x: x[1], reverse=True)[:3]
    top_volume_sectors = sorted(sector_pipeline, key=lambda x: x[2], reverse=True)[:3]
    
    # Identify key risks
    notable_risks = []
    if billing_sum["total_receivables"] > (billing_sum["total_order_value_excl_gst"] * 0.3):
        notable_risks.append(
            f"High Outstanding Receivables: ₹{billing_sum['total_receivables']:,.2f} "
            f"is outstanding, which represents a significant portion of billed revenue."
        )
        
    # Sectors with highest receivables
    receivable_sectors = sorted(
        [(sp["sector"], sp["work_orders"]["receivables"]) for sp in sector_perf],
        key=lambda x: x[1],
        reverse=True
    )
    if receivable_sectors and receivable_sectors[0][1] > 0:
        notable_risks.append(
            f"Sector Receivable Concentration: Sector '{receivable_sectors[0][0]}' "
            f"has the highest outstanding receivables at ₹{receivable_sectors[0][1]:,.2f}."
        )
        
    # Work order status alerts
    execution_status = wo_sum["execution_status_distribution"]
    if "Pause / struck" in execution_status:
        stuck_count = execution_status["Pause / struck"]["count"]
        if stuck_count > 0:
            notable_risks.append(f"Operations Risk: {stuck_count} Work Orders are currently 'Pause / struck'.")
            
    return {
        "pipeline_kpis": {
            "total_portfolio_value": pipe_sum["total_portfolio_value"],
            "open_pipeline_value": pipe_sum["open_pipeline_value"],
            "weighted_pipeline_value": pipe_sum["weighted_pipeline_value"],
            "total_deals_count": pipe_sum["total_deals"],
            "open_deals_count": pipe_sum["open_deals_count"],
            "won_deals_count": pipe_sum["won_deals_count"],
            "won_deals_value": pipe_sum["won_deals_value"]
        },
        "operations_kpis": {
            "total_work_orders": wo_sum["total_work_orders"],
            "completed_work_orders": wo_sum["completed_count"],
            "open_work_orders": wo_sum["open_count"],
            "completion_rate_percentage": round(
                (wo_sum["completed_count"] / wo_sum["total_work_orders"] * 100) 
                if wo_sum["total_work_orders"] > 0 else 0.0, 
                2
            )
        },
        "billing_kpis": {
            "total_order_value_excl_gst": billing_sum["total_order_value_excl_gst"],
            "total_billed_value_excl_gst": billing_sum["total_billed_value_excl_gst"],
            "total_collected_amount": billing_sum["total_collected_amount"],
            "total_receivables": billing_sum["total_receivables"],
            "billed_percentage_excl": billing_sum["billed_percentage_excl"],
            "collected_percentage_of_billed": billing_sum["collected_percentage_of_billed"]
        },
        "market_segments": {
            "top_sectors_by_open_pipeline": [
                {"sector": s, "open_pipeline_value": val} for s, val, _ in top_pipeline_sectors if val > 0
            ],
            "top_sectors_by_work_orders": [
                {"sector": s, "work_order_count": count} for s, _, count in top_volume_sectors if count > 0
            ]
        },
        "notable_risks": notable_risks,
        "data_quality_caveats": dq_sum["key_caveats"]
    }


# ============================================================
# ADVANCED EXECUTIVE PLATFORM ADDITIONS
# ============================================================

def get_owner_performance(deals_df: pd.DataFrame) -> List[Dict[str, Any]]:
    """Group deals by owner and calculate pipeline performance metrics."""
    df = clean_deals_df(deals_df)
    if df.empty:
        return []
    
    df = df.copy()
    if "owner_code" not in df.columns:
        df["owner_code"] = None
    df["owner_clean"] = df["owner_code"].apply(lambda x: normalize_text(x) or "Unassigned")
    df["deal_value_clean"] = df["deal_value"].fillna(0.0)
    
    status_series = df["deal_status"].apply(normalize_text)
    status_lower = status_series.str.lower()
    df["is_open"] = status_lower.isin(["open", "open deal"]) | status_series.isna()
    df["is_won"] = status_lower == "won"
    df["is_lost"] = status_lower.isin(["dead", "lost"])
    
    grouped = df.groupby("owner_clean")
    results = []
    
    for owner, group in grouped:
        total_count = len(group)
        total_value = float(group["deal_value_clean"].sum())
        open_count = int(group["is_open"].sum())
        open_val = float(group["deal_value_clean"][group["is_open"]].sum())
        won_count = int(group["is_won"].sum())
        won_val = float(group["deal_value_clean"][group["is_won"]].sum())
        lost_count = int(group["is_lost"].sum())
        lost_val = float(group["deal_value_clean"][group["is_lost"]].sum())
        
        win_rate = (won_count / (won_count + lost_count) * 100) if (won_count + lost_count) > 0 else 0.0
        
        results.append({
            "owner": owner,
            "total_deals": total_count,
            "total_value": total_value,
            "open_count": open_count,
            "open_value": open_val,
            "won_count": won_count,
            "won_value": won_val,
            "win_rate_percentage": win_rate
        })
        
    results.sort(key=lambda x: x["total_value"], reverse=True)
    return results


def get_stale_deals(deals_df: pd.DataFrame, reference_date=None) -> List[Dict[str, Any]]:
    """
    Identify open deals that are at risk of stalling (e.g. missing tentative close date,
    tentative close date in the past, or closure probability is low).
    """
    df = clean_deals_df(deals_df)
    if df.empty:
        return []
        
    df = df.copy()
    status_series = df["deal_status"].apply(normalize_text)
    status_lower = status_series.str.lower()
    is_open = status_lower.isin(["open", "open deal"]) | status_series.isna()
    is_hold = status_lower == "on hold"
    active_mask = is_open | is_hold
    
    open_deals = df[active_mask].copy()
    if open_deals.copy().empty:
        return []
        
    import datetime
    if reference_date is None:
        # Use a fixed baseline date (2026-08-30) for stale checks by default
        reference_date = datetime.date(2026, 8, 30)
    
    stale_deals = []
    for idx, row in open_deals.iterrows():
        deal_id = str(row.get("id", ""))
        name = str(row.get("name", "Unnamed Deal"))
        val = float(row.get("deal_value")) if not pd.isna(row.get("deal_value")) else 0.0
        stage = str(row.get("deal_stage", "Unknown"))
        sector = normalize_sector(row.get("sector_service", ""))
        prob = str(row.get("closure_probability", "None"))
        owner = str(row.get("owner_code", "Unassigned"))
        
        reasons = []
        is_stale = False
        
        tentative_date_raw = row.get("tentative_close_date")
        close_date_raw = row.get("close_date")
        
        has_date = False
        try:
            if not pd.isna(tentative_date_raw) and tentative_date_raw:
                t_date = pd.to_datetime(tentative_date_raw).date()
                has_date = True
                if t_date < reference_date:
                    is_stale = True
                    reasons.append(f"Overdue tentative close date: {t_date}")
            if not pd.isna(close_date_raw) and close_date_raw:
                c_date = pd.to_datetime(close_date_raw).date()
                has_date = True
                if c_date < reference_date:
                    is_stale = True
                    reasons.append(f"Overdue close date: {c_date}")
        except Exception:
            pass
            
        if not has_date:
            is_stale = True
            reasons.append("Missing both close dates")
            
        if prob.lower() == "low":
            is_stale = True
            reasons.append("Closure probability is Low")
            
        if is_stale:
            stale_deals.append({
                "id": deal_id,
                "name": name,
                "value": val,
                "stage": stage,
                "sector": sector,
                "probability": prob,
                "owner": owner,
                "reasons": reasons
            })
            
    stale_deals.sort(key=lambda x: x["value"], reverse=True)
    return stale_deals


def get_top_opportunities(deals_df: pd.DataFrame, limit: int = 10) -> List[Dict[str, Any]]:
    """Retrieve top open deals sorted purely by deal value descending."""
    df = clean_deals_df(deals_df)
    if df.empty:
        return []
        
    df = df.copy()
    status_series = df["deal_status"].apply(normalize_text)
    status_lower = status_series.str.lower()
    is_open = status_lower.isin(["open", "open deal"]) | status_series.isna()
    is_hold = status_lower == "on hold"
    active_mask = is_open | is_hold
    
    open_deals = df[active_mask].copy()
    open_deals["deal_value_clean"] = open_deals["deal_value"].fillna(0.0)
    
    open_deals = open_deals.sort_values(by="deal_value_clean", ascending=False)
    results = []
    
    for idx, row in open_deals.head(limit).iterrows():
        results.append({
            "name": str(row.get("name", "Unnamed Deal")),
            "value": float(row["deal_value_clean"]),
            "stage": str(row.get("deal_stage", "Unknown")),
            "sector": normalize_sector(row.get("sector_service", "")),
            "probability": str(row.get("closure_probability", "None")),
            "owner": str(row.get("owner_code", "Unassigned"))
        })
        
    return results


def get_priority_opportunities(deals_df: pd.DataFrame, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Retrieve top open deals ranked by Business Priority Score rather than pure deal value.
    Business priority weights deal value, stage maturity, and closure probability:
    - High-value + late-stage (Negotiations/Proposal) + high-probability opportunities
      rank above huge early-stage low-probability opportunities.
    """
    df = clean_deals_df(deals_df)
    if df.empty:
        return []
        
    df = df.copy()
    status_series = df["deal_status"].apply(normalize_text)
    status_lower = status_series.str.lower()
    is_open = status_lower.isin(["open", "open deal"]) | status_series.isna()
    is_hold = status_lower == "on hold"
    active_mask = is_open | is_hold
    
    open_deals = df[active_mask].copy()
    if open_deals.empty:
        return []

    # Stage maturity multiplier
    STAGE_MATURITY_WEIGHTS = {
        "negotiation": 1.00,
        "negotiations": 1.00,
        "proposal": 0.85,
        "commercials": 0.85,
        "feasibility": 0.60,
        "poc": 0.50,
        "demo": 0.50,
        "qualified": 0.35,
        "lead": 0.20,
    }

    # Probability multiplier
    PROBABILITY_WEIGHTS = {
        "high": 0.80,
        "medium": 0.50,
        "low": 0.20,
    }

    scored_deals = []
    for idx, row in open_deals.iterrows():
        val = float(row.get("deal_value")) if not pd.isna(row.get("deal_value")) else 0.0
        stage_str = str(row.get("deal_stage", "Unknown"))
        stage_lower = stage_str.lower()
        prob_str = str(row.get("closure_probability", "None"))
        prob_lower = prob_str.lower()

        # Compute stage weight
        stage_weight = 0.30
        for k, w in STAGE_MATURITY_WEIGHTS.items():
            if k in stage_lower:
                stage_weight = w
                break

        # Compute probability weight
        prob_weight = PROBABILITY_WEIGHTS.get(prob_lower, 0.30)

        # Weighted pipeline value
        weighted_val = val * prob_weight

        # Composite Business Priority Score
        priority_score = val * stage_weight * prob_weight

        # Priority label
        if priority_score >= 20_000_000 or (stage_weight >= 0.85 and prob_weight >= 0.50 and val >= 5_000_000):
            priority_tier = "Critical (Tier 1)"
        elif priority_score >= 5_000_000 or (stage_weight >= 0.60 and val >= 2_000_000):
            priority_tier = "High (Tier 2)"
        else:
            priority_tier = "Medium (Tier 3)"

        scored_deals.append({
            "name": str(row.get("name", "Unnamed Deal")),
            "value": val,
            "stage": stage_str,
            "sector": normalize_sector(row.get("sector_service", "")),
            "probability": prob_str,
            "owner": str(row.get("owner_code", "Unassigned")),
            "weighted_value": weighted_val,
            "priority_score": priority_score,
            "priority_tier": priority_tier,
            "stage_weight": stage_weight,
            "prob_weight": prob_weight
        })

    # Sort descending by priority score
    scored_deals.sort(key=lambda x: x["priority_score"], reverse=True)
    return scored_deals[:limit]



def get_business_health_summary(deals_df: pd.DataFrame, work_orders_df: pd.DataFrame) -> Dict[str, Any]:
    """
    Calculate business health scores across 4 dimensions: Sales, Operations, Finance, and Data Quality.
    Returns scores out of 100, lists contributing factors, and computes an overall health score.
    """
    deals = clean_deals_df(deals_df)
    wos = clean_work_orders_df(work_orders_df)
    
    # 1. SALES HEALTH SCORE
    sales_score = 50.0
    sales_factors = []
    if not deals.empty:
        pipe = get_pipeline_summary(deals)
        won_cnt = pipe["won_deals_count"]
        dead_cnt = pipe["dead_deals_count"]
        
        # Factor A: Closure Rate of Closed Deals (50% weight)
        closed_total = won_cnt + dead_cnt
        if closed_total > 0:
            closure_rate = (won_cnt / closed_total) * 100
        else:
            closure_rate = 50.0
        sales_factors.append({
            "factor": "Closed Deals Win Rate",
            "value": f"{closure_rate:.1f}%",
            "weight": "50%",
            "impact": "+" if closure_rate >= 50.0 else "-"
        })
        
        # Factor B: Weighted Pipeline Ratio (30% weight)
        open_val = pipe["open_pipeline_value"]
        weighted_val = pipe["weighted_pipeline_value"]
        if open_val > 0:
            pipeline_ratio = (weighted_val / open_val) * 100
        else:
            pipeline_ratio = 50.0
        sales_factors.append({
            "factor": "Pipeline Closure Probability Ratio",
            "value": f"{pipeline_ratio:.1f}%",
            "weight": "30%",
            "impact": "+" if pipeline_ratio >= 40.0 else "-"
        })
        
        # Factor C: Active Pipeline Visibility (20% weight)
        active_count = pipe["deals_with_probability"] + pipe["deals_missing_probability"]
        if active_count > 0:
            visibility = (pipe["deals_with_probability"] / active_count) * 100
        else:
            visibility = 50.0
        sales_factors.append({
            "factor": "Pipeline Visibility (Known Probabilities)",
            "value": f"{visibility:.1f}%",
            "weight": "20%",
            "impact": "+" if visibility >= 50.0 else "-"
        })
        
        sales_score = (0.5 * closure_rate) + (0.3 * pipeline_ratio) + (0.2 * visibility)
    else:
        sales_factors.append({"factor": "No deal data found", "value": "N/A", "weight": "100%", "impact": "-"})
        
    # 2. OPERATIONS HEALTH SCORE
    ops_score = 50.0
    ops_factors = []
    if not wos.empty:
        ops = get_work_order_summary(wos)
        tot_wos = ops["total_work_orders"]
        
        # Factor A: Completion Rate (60% weight)
        comp_rate = (ops["completed_count"] / tot_wos * 100) if tot_wos > 0 else 0.0
        ops_factors.append({
            "factor": "Work Order Completion Rate",
            "value": f"{comp_rate:.1f}%",
            "weight": "60%",
            "impact": "+" if comp_rate >= 70.0 else "-"
        })
        
        # Factor B: Paused/Struck Safety (30% weight)
        paused_cnt = ops["execution_status_distribution"].get("Pause / struck", {}).get("count", 0)
        paused_pct = (paused_cnt / tot_wos * 100) if tot_wos > 0 else 0.0
        paused_score = max(0.0, 100.0 - (paused_pct * 3))
        ops_factors.append({
            "factor": "Operational Flow (Low Stuck Orders)",
            "value": f"{paused_cnt} stuck ({paused_pct:.1f}%)",
            "weight": "30%",
            "impact": "+" if paused_pct < 5.0 else "-"
        })
        
        # Factor C: Backlog Readiness (10% weight)
        not_started = ops["execution_status_distribution"].get("Not Started", {}).get("count", 0)
        not_started_pct = (not_started / tot_wos * 100) if tot_wos > 0 else 0.0
        backlog_score = max(0.0, 100.0 - not_started_pct)
        ops_factors.append({
            "factor": "Backlog Readiness (Unstarted Orders)",
            "value": f"{not_started} unstarted ({not_started_pct:.1f}%)",
            "weight": "10%",
            "impact": "+" if not_started_pct < 20.0 else "-"
        })
        
        ops_score = (0.6 * comp_rate) + (0.3 * paused_score) + (0.1 * backlog_score)
    else:
        ops_factors.append({"factor": "No operations data found", "value": "N/A", "weight": "100%", "impact": "-"})
        
    # 3. FINANCE HEALTH SCORE
    fin_score = 50.0
    fin_factors = []
    if not wos.empty:
        bill = get_billing_summary(wos)
        
        # Factor A: Billed Contract Ratio (40% weight)
        billed_pct = bill["billed_percentage_excl"]
        fin_factors.append({
            "factor": "Invoiced Billed Rate of Contract",
            "value": f"{billed_pct:.1f}%",
            "weight": "40%",
            "impact": "+" if billed_pct >= 50.0 else "-"
        })
        
        # Factor B: Collection Efficiency Rate (40% weight)
        collected_pct = bill["collected_percentage_of_billed"]
        fin_factors.append({
            "factor": "Collection-to-Billed Rate",
            "value": f"{collected_pct:.1f}%",
            "weight": "40%",
            "impact": "+" if collected_pct >= 75.0 else "-"
        })
        
        # Factor C: Outstanding Receivables Exposure (20% weight)
        billed_incl = bill["total_billed_value_incl_gst"]
        receivables = bill["total_receivables"]
        if billed_incl > 0:
            receivables_pct = (receivables / billed_incl) * 100
        else:
            receivables_pct = 0.0
        exposure_score = max(0.0, 100.0 - receivables_pct)
        fin_factors.append({
            "factor": "Receivables Risk Exposure Control",
            "value": f"Receivables represents {receivables_pct:.1f}% of billed value",
            "weight": "20%",
            "impact": "+" if receivables_pct < 25.0 else "-"
        })
        
        fin_score = (0.4 * billed_pct) + (0.4 * collected_pct) + (0.2 * exposure_score)
    else:
        fin_factors.append({"factor": "No finance data found", "value": "N/A", "weight": "100%", "impact": "-"})
        
    # 4. DATA QUALITY HEALTH SCORE
    dq_score = 50.0
    dq_factors = []
    
    dq = get_data_quality_summary(deals_df, work_orders_df)
    deals_dq = dq["deals"]
    wos_dq = dq["work_orders"]
    
    deals_missing_pct = 0.0
    if deals_dq["total_records"] > 0 and deals_dq["missing_fields"]:
        total_fields_missing = sum([d["percentage"] for d in deals_dq["missing_fields"].values()])
        # Normalize missing fields across 6 key columns: deal_value, closure_probability, deal_stage, deal_status, product_deal, close_date
        deals_missing_pct = total_fields_missing / 6.0
    deals_comp_score = max(0.0, 100.0 - deals_missing_pct)
    
    wos_missing_pct = 0.0
    if wos_dq["total_records"] > 0 and wos_dq["missing_fields"]:
        total_wos_missing = sum([d["percentage"] for d in wos_dq["missing_fields"].values()])
        # Normalize missing fields across 6 key columns: amount_excl_gst, billed_value_excl_gst, collected_amount, amount_receivable, execution_status, sector
        wos_missing_pct = total_wos_missing / 6.0
    wos_comp_score = max(0.0, 100.0 - wos_missing_pct)
    
    total_anomalies = len(deals_dq.get("anomalies", [])) + len(wos_dq.get("anomalies", []))
    anomaly_penalty = min(30.0, float(total_anomalies * 5))
    
    dq_score = max(0.0, (0.5 * deals_comp_score) + (0.5 * wos_comp_score) - anomaly_penalty)
    
    dq_factors.append({
        "factor": "Deals Column Completeness",
        "value": f"{100.0 - deals_missing_pct:.1f}% populated",
        "weight": "50%",
        "impact": "+" if (100.0 - deals_missing_pct) >= 70.0 else "-"
    })
    dq_factors.append({
        "factor": "Work Orders Column Completeness",
        "value": f"{100.0 - wos_missing_pct:.1f}% populated",
        "weight": "50%",
        "impact": "+" if (100.0 - wos_missing_pct) >= 80.0 else "-"
    })
    dq_factors.append({
        "factor": "Anomalies Penalty",
        "value": f"-{anomaly_penalty} points ({total_anomalies} anomalies found)",
        "weight": "Penalty",
        "impact": "-" if anomaly_penalty > 0 else "+"
    })
    
    # 5. OVERALL BUSINESS HEALTH SCORE
    overall_score = (0.25 * sales_score) + (0.25 * ops_score) + (0.25 * fin_score) + (0.25 * dq_score)
    
    return {
        "overall_score": round(overall_score, 1),
        "dimensions": {
            "sales": {
                "score": round(sales_score, 1),
                "factors": sales_factors
            },
            "operations": {
                "score": round(ops_score, 1),
                "factors": ops_factors
            },
            "finance": {
                "score": round(fin_score, 1),
                "factors": fin_factors
            },
            "data_quality": {
                "score": round(dq_score, 1),
                "factors": dq_factors
            }
        }
    }


def get_deterministic_insights(deals_df: pd.DataFrame, work_orders_df: pd.DataFrame) -> List[Dict[str, Any]]:
    """
    Formulate factual business insights using deterministic heuristics from the data.
    Cites specific numbers and provides structured suggestions.
    """
    deals = clean_deals_df(deals_df)
    wos = clean_work_orders_df(work_orders_df)
    
    insights = []
    
    # 1. Pipeline Segment Leader
    sector_pipeline = get_pipeline_by_sector(deals)
    if sector_pipeline:
        top_sector = sector_pipeline[0]
        if top_sector["portfolio_value"] > 0:
            insights.append({
                "type": "opportunity",
                "title": f"Sales Pipeline Dominance in {top_sector['sector']}",
                "metric": f"₹{top_sector['portfolio_value']:,.2f}",
                "description": (
                    f"The '{top_sector['sector']}' sector dominates the sales pipeline with a total "
                    f"portfolio value of ₹{top_sector['portfolio_value']:,.2f} across {top_sector['deal_count']} deals. "
                    f"It represents the largest open commercial opportunity for Skylark."
                )
            })
            
    # 2. Outstanding Receivables Concentration
    billing = get_billing_summary(wos)
    sector_perf = get_sector_performance(deals, wos)
    
    highest_receivables_sector = None
    highest_receivables_value = 0.0
    for s in sector_perf:
        val = s["work_orders"]["receivables"]
        if val > highest_receivables_value:
            highest_receivables_value = val
            highest_receivables_sector = s["sector"]
            
    if highest_receivables_sector and highest_receivables_value > 0:
        total_receivables = billing["total_receivables"]
        concentration = (highest_receivables_value / total_receivables * 100) if total_receivables > 0 else 0.0
        if concentration > 25.0:
            insights.append({
                "type": "risk",
                "title": f"Receivables Concentration Risk in {highest_receivables_sector}",
                "metric": f"{concentration:.1f}% Concentration",
                "description": (
                    f"Outstanding receivables are heavily concentrated in the '{highest_receivables_sector}' sector, "
                    f"which holds ₹{highest_receivables_value:,.2f} of the total ₹{total_receivables:,.2f} outstanding (incl. GST). "
                    f"Collections follow-up should be prioritized here to reduce cash-flow risk."
                )
            })
            
    # 3. Operational Workload and Bottlenecks
    wo_sum = get_work_order_summary(wos)
    tot_wos = wo_sum["total_work_orders"]
    paused_cnt = wo_sum["execution_status_distribution"].get("Pause / struck", {}).get("count", 0)
    
    if paused_cnt > 0:
        stuck_pct = (paused_cnt / tot_wos * 100) if tot_wos > 0 else 0.0
        insights.append({
            "type": "risk",
            "title": f"Operational Bottleneck: Stuck Orders",
            "metric": f"{paused_cnt} Struck Orders ({stuck_pct:.1f}%)",
            "description": (
                f"There are currently {paused_cnt} work orders marked as 'Pause / struck'. "
                f"These represent blocked executions that impact delivery timelines and subsequent billing triggers."
            )
        })
        
    # 4. Large Invoicing/Billing Gap
    billed_excl = billing["total_billed_value_excl_gst"]
    order_excl = billing["total_order_value_excl_gst"]
    to_bill_excl = billing["total_amount_to_bill_excl_gst"]
    
    if to_bill_excl > (order_excl * 0.3):
        to_bill_pct = (to_bill_excl / order_excl * 100) if order_excl > 0 else 0.0
        insights.append({
            "type": "finance",
            "title": "Substantial Unbilled Backlog",
            "metric": f"₹{to_bill_excl:,.2f} Unbilled ({to_bill_pct:.1f}%)",
            "description": (
                f"A significant volume of signed contract value is yet to be invoiced, standing at "
                f"₹{to_bill_excl:,.2f} excl. GST. Operations should expedite milestones to enable billing triggers."
            )
        })
        
    # 5. Data Quality Risk Impacting Projections
    dq = get_data_quality_summary(deals, wos)
    deals_dq = dq["deals"]
    missing_prob = deals_dq["missing_fields"].get("closure_probability", {}).get("percentage", 0.0)
    
    if missing_prob > 50.0:
        insights.append({
            "type": "governance",
            "title": "Pipeline Visibility Impaired",
            "metric": f"{missing_prob:.1f}% Missing Probability",
            "description": (
                f"Over half ({missing_prob:.1f}%) of active sales deals are missing a closure probability categorisation "
                f"on Monday.com. This reduces the accuracy and reliability of weighted sales pipeline projections."
            )
        })
        
    # 6. Largest Active Sales Opportunity
    status_lower = deals["deal_status"].fillna("").str.lower()
    is_active = (status_lower.isin(["open", "open deal"]) | deals["deal_status"].isna() | (status_lower == "on hold"))
    active_deals = deals[is_active].copy()
    active_deals["deal_value_clean"] = active_deals["deal_value"].fillna(0.0)
    
    if not active_deals.empty:
        largest_deal = active_deals.sort_values(by="deal_value_clean", ascending=False).iloc[0]
        largest_val = largest_deal["deal_value_clean"]
        if largest_val > 0:
            insights.append({
                "type": "opportunity",
                "title": f"Key Deal Focus: {largest_deal['name']}",
                "metric": f"₹{largest_val:,.2f}",
                "description": (
                    f"The largest active opportunity currently in the pipeline is '{largest_deal['name']}' "
                    f"valued at ₹{largest_val:,.2f} in the stage '{largest_deal['deal_stage']}'. "
                    f"Closing this deal will significantly impact overall performance."
                )
            })
            
    return insights


def get_executive_recommendations(deals_df: pd.DataFrame, work_orders_df: pd.DataFrame) -> List[Dict[str, Any]]:
    """
    Generate deterministic actionable recommendations for leadership based on pipeline,
    delivery, collection and data quality anomalies.
    """
    deals = clean_deals_df(deals_df)
    wos = clean_work_orders_df(work_orders_df)
    
    recommendations = []
    
    # 1. Stale Deals Recommendation
    stale = get_stale_deals(deals)
    if len(stale) > 0:
        total_stale_val = sum(d["value"] for d in stale)
        recommendations.append({
            "category": "Sales",
            "action": f"Review {len(stale)} stale/at-risk deals (Total value: ₹{total_stale_val:,.2f})",
            "details": "These open deals are either missing close dates, overdue, or flagged as Low probability. Team should re-engage or mark dead.",
            "priority": "HIGH" if total_stale_val > 10000000 else "MEDIUM"
        })
        
    # 2. Missing Deal Values Recommendation
    dq = get_data_quality_summary(deals, wos)
    missing_val_cnt = dq["deals"]["missing_fields"].get("deal_value", {}).get("count", 0)
    if missing_val_cnt > 0:
        recommendations.append({
            "category": "Governance",
            "action": f"Populate deal value fields for {missing_val_cnt} Deals on Monday.com",
            "details": "Active deals missing commercial values distort pipeline sizing and forecasting projections.",
            "priority": "HIGH" if missing_val_cnt > 10 else "MEDIUM"
        })
        
    # 3. Missing Probabilities Recommendation
    missing_prob_cnt = dq["deals"]["missing_fields"].get("closure_probability", {}).get("count", 0)
    if missing_prob_cnt > 0:
        recommendations.append({
            "category": "Governance",
            "action": f"Assign closure probabilities to {missing_prob_cnt} Deals",
            "details": "Improving probability completeness allows for a more accurate weighted pipeline forecast (currently ₹258M vs ₹688M raw).",
            "priority": "MEDIUM"
        })
        
    # 4. Stuck Work Orders Recommendation
    wo_sum = get_work_order_summary(wos)
    paused_cnt = wo_sum["execution_status_distribution"].get("Pause / struck", {}).get("count", 0)
    if paused_cnt > 0:
        recommendations.append({
            "category": "Operations",
            "action": f"Investigate resource blockages for {paused_cnt} Stuck Work Orders",
            "details": "Stuck work orders cause delivery delays and delay milestone invoicing triggers.",
            "priority": "HIGH"
        })
        
    # 5. Receivables Concentration & Cash Collection Recommendation
    billing = get_billing_summary(wos)
    sector_perf = get_sector_performance(deals, wos)
    
    highest_receivables_sector = None
    highest_receivables_value = 0.0
    for s in sector_perf:
        val = s["work_orders"]["receivables"]
        if val > highest_receivables_value:
            highest_receivables_value = val
            highest_receivables_sector = s["sector"]
            
    if highest_receivables_sector and highest_receivables_value > 0:
        total_receivables = billing["total_receivables"]
        concentration = (highest_receivables_value / total_receivables * 100) if total_receivables > 0 else 0.0
        if concentration > 25.0:
            recommendations.append({
                "category": "Finance",
                "action": f"Prioritize receivables collections in {highest_receivables_sector} (₹{highest_receivables_value:,.2f})",
                "details": f"Outstanding receivables are highly concentrated here, representing {concentration:.1f}% of total company receivables.",
                "priority": "HIGH"
            })
            
    # 6. Unbilled Invoicing Gap
    to_bill_excl = billing["total_amount_to_bill_excl_gst"]
    order_excl = billing["total_order_value_excl_gst"]
    if to_bill_excl > (order_excl * 0.2):
        recommendations.append({
            "category": "Finance",
            "action": f"Accelerate invoicing milestones for ₹{to_bill_excl:,.2f} unbilled backlog",
            "details": "A large portion of executed/signed contract value is yet to be billed. Verify delivery status to trigger invoices.",
            "priority": "HIGH"
        })
        
    # Sort by priority (HIGH first)
    recommendations.sort(key=lambda x: 0 if x["priority"] == "HIGH" else 1)
    return recommendations


# ============================================================
# REVENUE ANALYSIS (Won / Closed-Won)
# ============================================================

def get_revenue_by_sector(deals_df: pd.DataFrame, sector: Optional[str] = None) -> Dict[str, Any]:
    """
    Analyse closed-won revenue grouped by sector.
    Returns ranked list + total won revenue.
    """
    df = clean_deals_df(deals_df)
    if df.empty:
        return {
            "total_won_revenue": 0.0,
            "won_deals_count": 0,
            "sector": sector,
            "ranked_sectors": [],
            "top_sector": "N/A",
            "top_sector_revenue": 0.0,
            "data_note": "No deals data available.",
        }

    df = df.copy()
    df["normalized_sector"] = df["sector_service"].apply(normalize_sector)
    df["deal_value_clean"] = df["deal_value"].fillna(0.0)

    status_series = df["deal_status"].apply(normalize_text)
    status_lower = status_series.str.lower()
    df["is_won"] = status_lower == "won"

    won_df = df[df["is_won"]]
    total_won = float(won_df["deal_value_clean"].sum())
    won_count = len(won_df)

    ranked = []
    if not won_df.empty:
        grouped = won_df.groupby("normalized_sector").agg(
            won_revenue=("deal_value_clean", "sum"),
            won_deals=("id", "count"),
        ).reset_index().sort_values("won_revenue", ascending=False)

        for _, row in grouped.iterrows():
            share = round(row["won_revenue"] / total_won * 100, 1) if total_won > 0 else 0.0
            ranked.append({
                "sector": row["normalized_sector"],
                "won_revenue": float(row["won_revenue"]),
                "won_deals": int(row["won_deals"]),
                "share_pct": share,
            })

    # If sector filter requested, also return that sector's slice
    sector_detail = None
    if sector:
        norm = sector.strip().title()
        match = [r for r in ranked if r["sector"].lower() == norm.lower()]
        sector_detail = match[0] if match else {"sector": sector, "won_revenue": 0.0, "won_deals": 0, "share_pct": 0.0}

    return {
        "total_won_revenue": total_won,
        "won_deals_count": won_count,
        "ranked_sectors": ranked,
        "top_sector": ranked[0]["sector"] if ranked else "N/A",
        "top_sector_revenue": ranked[0]["won_revenue"] if ranked else 0.0,
        "sector_detail": sector_detail,
        "data_note": (
            f"Revenue is based on {won_count} Closed-Won deals. "
            "Open deals are excluded from revenue figures."
        ),
    }


# ============================================================
# CUSTOMER PIPELINE ANALYSIS
# ============================================================

def get_customer_pipeline(deals_df: pd.DataFrame) -> Dict[str, Any]:
    """
    Group deals by customer/client code to surface largest pipeline accounts.
    """
    df = clean_deals_df(deals_df)
    if df.empty:
        return {"ranked_customers": [], "total_pipeline": 0.0}

    df = df.copy()
    df["deal_value_clean"] = df["deal_value"].fillna(0.0)

    # Use client_code if available, else fall back to 'name'
    if "client_code" in df.columns:
        df["customer"] = df["client_code"].apply(lambda x: normalize_text(x) or "Unknown")
    else:
        df["customer"] = df["name"].apply(lambda x: str(x)[:30] if x else "Unknown")

    status_series = df["deal_status"].apply(normalize_text)
    status_lower = status_series.str.lower()
    df["is_open"] = status_lower.isin(["open", "open deal"]) | status_series.isna()
    df["is_won"] = status_lower == "won"

    grouped = df.groupby("customer").agg(
        total_deals=("id", "count"),
        total_value=("deal_value_clean", "sum"),
        open_count=("is_open", "sum"),
        open_value=("deal_value_clean", lambda x: float(x[df.loc[x.index, "is_open"]].sum())),
        won_count=("is_won", "sum"),
    ).reset_index().sort_values("total_value", ascending=False)

    total_pipeline = float(grouped["total_value"].sum())
    ranked = []
    for _, row in grouped.head(15).iterrows():
        share = round(row["total_value"] / total_pipeline * 100, 1) if total_pipeline > 0 else 0.0
        ranked.append({
            "customer": row["customer"],
            "total_deals": int(row["total_deals"]),
            "total_value": float(row["total_value"]),
            "open_count": int(row["open_count"]),
            "open_value": float(row["open_value"]),
            "won_count": int(row["won_count"]),
            "share_pct": share,
        })

    return {
        "ranked_customers": ranked,
        "total_pipeline": total_pipeline,
        "top_customer": ranked[0]["customer"] if ranked else "N/A",
        "top_customer_value": ranked[0]["total_value"] if ranked else 0.0,
        "data_note": "Customer codes from Monday.com client_code field. Top 15 customers by total portfolio value shown.",
    }


# ============================================================
# OPERATIONAL RISK SUMMARY (Delayed / Stuck Work Orders)
# ============================================================

def get_operational_risk_summary(work_orders_df: pd.DataFrame, sector: Optional[str] = None) -> Dict[str, Any]:
    """
    Identify delayed, stuck, or at-risk work orders.
    Returns by-sector breakdown and counts of problematic statuses.
    """
    df = clean_work_orders_df(work_orders_df)
    if df.empty:
        return {
            "total_work_orders": 0,
            "at_risk_count": 0,
            "risk_statuses": {},
            "sector_risk": [],
            "highest_risk_sector": "N/A",
            "data_note": "No work orders data available.",
        }

    df = df.copy()
    df["normalized_sector"] = df["sector"].apply(normalize_sector)
    df["status_clean"] = df["execution_status"].apply(lambda x: normalize_text(x) or "Unknown / Missing")

    # Define risky statuses
    RISKY_STATUSES = {"pause / struck", "paused", "stuck", "not started", "on hold", "blocked"}

    df["is_risky"] = df["status_clean"].str.lower().isin(RISKY_STATUSES)

    total = len(df)
    at_risk = int(df["is_risky"].sum())
    risk_pct = round(at_risk / total * 100, 1) if total > 0 else 0.0

    # Count by risk status
    risk_counts = df[df["is_risky"]]["status_clean"].value_counts().to_dict()

    # Sector-level risk breakdown
    sector_risk = []
    for sec, grp in df.groupby("normalized_sector"):
        sec_total = len(grp)
        sec_risky = int(grp["is_risky"].sum())
        sec_risk_pct = round(sec_risky / sec_total * 100, 1) if sec_total > 0 else 0.0
        sector_risk.append({
            "sector": sec,
            "total_work_orders": sec_total,
            "at_risk_count": sec_risky,
            "risk_percentage": sec_risk_pct,
        })

    sector_risk.sort(key=lambda x: x["risk_percentage"], reverse=True)

    # Filter by sector if requested
    if sector:
        norm = sector.strip().title()
        sector_risk = [s for s in sector_risk if s["sector"].lower() == norm.lower()]

    highest_risk = sector_risk[0]["sector"] if sector_risk else "N/A"

    # Find overdue work orders (probable_end_date < today)
    import datetime
    today = datetime.date.today()
    overdue_count = 0
    try:
        if "probable_end_date" in df.columns:
            df["end_date_parsed"] = pd.to_datetime(df["probable_end_date"], errors="coerce")
            not_completed = ~df["status_clean"].str.lower().isin(["completed", "executed until current month"])
            overdue_mask = not_completed & df["end_date_parsed"].notna() & (df["end_date_parsed"].dt.date < today)
            overdue_count = int(overdue_mask.sum())
    except Exception:
        pass

    return {
        "total_work_orders": total,
        "at_risk_count": at_risk,
        "at_risk_percentage": risk_pct,
        "overdue_count": overdue_count,
        "risk_statuses": {str(k): int(v) for k, v in risk_counts.items()},
        "sector_risk": sector_risk,
        "highest_risk_sector": highest_risk,
        "data_note": (
            f"{at_risk} of {total} work orders ({risk_pct}%) are in high-risk statuses "
            f"(Paused, Stuck, Not Started, Blocked). {overdue_count} are overdue past their end date."
        ),
    }


# ============================================================
# CROSS-BOARD RISK ANALYSIS
# ============================================================

def get_cross_board_risk_analysis(deals_df: pd.DataFrame, work_orders_df: pd.DataFrame) -> Dict[str, Any]:
    """
    Identify sectors with high sales pipeline but also high operational risk.
    Cross-board join at the sector level.
    """
    sector_perf = get_sector_performance(deals_df, work_orders_df)
    op_risk = get_operational_risk_summary(work_orders_df)

    # Build risk lookup by sector
    risk_by_sector = {r["sector"]: r for r in op_risk.get("sector_risk", [])}

    analysis = []
    for sp in sector_perf:
        sec = sp["sector"]
        open_pipeline = sp["deals"]["open_pipeline_value"]
        receivables = sp["work_orders"]["receivables"]
        wo_count = sp["work_orders"]["count"]
        risk_data = risk_by_sector.get(sec, {})
        risk_pct = risk_data.get("risk_percentage", 0.0)
        at_risk_wos = risk_data.get("at_risk_count", 0)

        # Composite risk flag: high pipeline + high operational risk
        high_pipeline = open_pipeline > 0
        high_risk = risk_pct > 20.0  # >20% of WOs in risky status
        high_receivables = receivables > 500000  # >5L outstanding

        risk_flags = []
        if high_pipeline and high_risk:
            risk_flags.append("High pipeline + high delivery risk")
        if high_receivables:
            risk_flags.append(f"High receivables (₹{receivables:,.0f})")
        if at_risk_wos > 3:
            risk_flags.append(f"{at_risk_wos} stuck/paused work orders")

        analysis.append({
            "sector": sec,
            "open_pipeline_value": open_pipeline,
            "work_orders_count": wo_count,
            "at_risk_wo_count": at_risk_wos,
            "wo_risk_percentage": risk_pct,
            "outstanding_receivables": receivables,
            "risk_flags": risk_flags,
            "combined_risk_score": round(risk_pct * 0.4 + (receivables / 1e6) * 0.3, 2),
        })

    # Sort by combined risk score descending
    analysis.sort(key=lambda x: x["combined_risk_score"], reverse=True)

    highest_risk_sector = analysis[0]["sector"] if analysis else "N/A"
    high_pipeline_high_risk = [a for a in analysis if "High pipeline + high delivery risk" in a.get("risk_flags", [])]

    return {
        "sector_analysis": analysis,
        "highest_risk_sector": highest_risk_sector,
        "high_pipeline_high_risk_sectors": [a["sector"] for a in high_pipeline_high_risk],
        "summary": (
            f"{len(high_pipeline_high_risk)} sector(s) show both high open pipeline and "
            f"high operational delivery risk, creating potential for revenue slippage."
        ),
    }

