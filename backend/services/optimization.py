"""
Optimization Service.
Contains logic for generating actionable insights for the Decision Engine.
"""

import pandas as pd
from typing import List, Dict, Optional
from models.schemas import (
    BleedingSpendItem,
    HighACOSItem,
    ScaleOpportunityItem,
    BudgetSaturationItem,
    HealthScore
)

def analyze_bleeding_spend(
    df: pd.DataFrame, 
    min_spend: float = 10.0, 
    min_clicks: int = 5
) -> List[BleedingSpendItem]:
    """
    Identify search terms with zero sales and high spend.
    Rule: Spend >= min_spend AND Sales == 0 AND Clicks >= min_clicks AND Match Type != Exact
    """
    if df.empty:
        return []

    # Ensure required columns exist
    required = ['Spend', 'Sales', 'Clicks', 'Match Type']
    if not all(col in df.columns for col in required):
        return []

    # Filter for bleeding spend
    mask = (
        (df['Spend'] >= min_spend) & 
        (df['Sales'] == 0) & 
        (df['Clicks'] >= min_clicks) &
        (df['Match Type'] != 'Exact')
    )
    
    # If Targeting exists, filter out ASINs
    if 'Targeting' in df.columns:
        mask = mask & (~df['Targeting'].str.lower().str.startswith('b0', na=False))

    bleeding = df[mask].copy()
    
    results = []
    for idx, row in bleeding.iterrows():
        # Severity = Spend * Clicks (higher spend/clicks = more urgent)
        severity = row['Spend'] * row['Clicks']
        
        item = BleedingSpendItem(
            id=int(idx),
            search_term=row.get('Customer Search Term', 'Unknown'),
            campaign_name=row.get('Campaign Name', 'Unknown'),
            ad_group_name=row.get('Ad Group Name', 'Unknown'),
            match_type=row.get('Match Type', 'Unknown'),
            spend=row['Spend'],
            clicks=int(row['Clicks']),
            severity_score=severity,
            action_type="Negative"
        )
        results.append(item)
        
    return sorted(results, key=lambda x: x.severity_score, reverse=True)


def analyze_high_acos(
    df: pd.DataFrame, 
    target_acos: float = 30.0
) -> List[HighACOSItem]:
    """
    Identify high ACOS terms and diagnose root cause.
    Root Causes:
    - Low CTR: CTR < avg_ctr
    - High CPC: CPC > avg_cpc
    - Low CVR: CVR < avg_cvr
    """
    if df.empty:
        return []
        
    # Calculate account averages for benchmarks
    total_impressions = df['Impressions'].sum() if 'Impressions' in df.columns else 0
    total_clicks = df['Clicks'].sum() if 'Clicks' in df.columns else 0
    total_spend = df['Spend'].sum() if 'Spend' in df.columns else 0
    total_orders = df['Orders'].sum() if 'Orders' in df.columns else 0

    avg_ctr = total_clicks / total_impressions if total_impressions > 0 else 0
    avg_cpc = total_spend / total_clicks if total_clicks > 0 else 0
    avg_cvr = total_orders / total_clicks if total_clicks > 0 else 0
    
    # Filter for High ACOS
    if 'ACOS' not in df.columns or 'Spend' not in df.columns:
        return []

    mask = (df['ACOS'] > target_acos) & (df['Spend'] > 0)
    high_acos_df = df[mask].copy()
    
    results = []
    for idx, row in high_acos_df.iterrows():
        ctr = row.get('CTR', 0)
        cpc = row.get('CPC', 0)
        cvr = row.get('Conversion Rate', 0)
        
        # Diagnose Root Cause (prioritize in order)
        root_cause = "General Efficiency"
        value = 0.0
        benchmark = 0.0
        action = "Optimization"
        
        if cvr < avg_cvr * 0.7: # Significantly lower CVR
            root_cause = "Low CVR"
            value = cvr
            benchmark = avg_cvr
            action = "Review Listing/Target"
        elif cpc > avg_cpc * 1.3: # Significantly higher CPC
            root_cause = "High CPC"
            value = cpc
            benchmark = avg_cpc
            action = "Bid Down"
        elif ctr < avg_ctr * 0.7: # Significantly lower CTR
            root_cause = "Low CTR"
            value = ctr
            benchmark = avg_ctr
            action = "Negative"
            
        item = HighACOSItem(
            id=int(idx),
            search_term=row.get('Customer Search Term', 'Unknown'),
            targeting=row.get('Targeting'),
            match_type=row.get('Match Type'),
            campaign_name=row.get('Campaign Name', 'Unknown'),
            acos=row.get('ACOS', 0),
            spend=row.get('Spend', 0),
            sales=row.get('Sales', 0),
            root_cause=root_cause,
            value=value,
            avg_value=benchmark,
            action_type=action
        )
        results.append(item)
        
    return sorted(results, key=lambda x: x.spend, reverse=True)


def analyze_scale_opportunities(
    df: pd.DataFrame,
    target_acos: float = 30.0,
    min_orders: int = 3
) -> List[ScaleOpportunityItem]:
    """
    Find profitable terms ready to scale.
    Rule: ACOS <= Target * 0.8 AND Orders >= min_orders
    """
    if df.empty or 'ACOS' not in df.columns or 'Orders' not in df.columns:
        return []
        
    efficient_threshold = target_acos * 0.8
    
    mask = (
        (df['ACOS'] <= efficient_threshold) & 
        (df['Orders'] >= min_orders)
    )
    
    scale_df = df[mask].copy()
    
    results = []
    for idx, row in scale_df.iterrows():
        cpc = row.get('CPC', 0)
        # Suggest 20% bid increase
        suggested = cpc * 1.2
        
        item = ScaleOpportunityItem(
            id=int(idx),
            search_term=row.get('Customer Search Term', 'Unknown'),
            targeting=row.get('Targeting'),
            match_type=row.get('Match Type'),
            campaign_name=row.get('Campaign Name', 'Unknown'),
            acos=row.get('ACOS', 0),
            orders=int(row.get('Orders', 0)),
            conversion_rate=row.get('Conversion Rate', 0),
            current_bid=cpc, # Approx as CPC since we don't have actual bids in STR
            suggested_bid=suggested,
            action_type="Bid Increase"
        )
        results.append(item)
        
    return sorted(results, key=lambda x: x.orders, reverse=True)


def analyze_budget_saturation(
    str_df: pd.DataFrame,
    bulk_df: pd.DataFrame
) -> List[BudgetSaturationItem]:
    """
    Identify profitable campaigns that are limited by budget.
    Requires merge of Search Term Report (Performance) and Bulk File (Budgets).
    """
    if str_df.empty or bulk_df.empty:
        return []
        
    # Aggregate STR data by Campaign
    if 'Campaign Name' not in str_df.columns or 'Spend' not in str_df.columns or 'Sales' not in str_df.columns:
         return []

    campaign_metrics = str_df.groupby('Campaign Name').agg({
        'Spend': 'sum',
        'Sales': 'sum'
    }).reset_index()
    
    # Calculate Campaign ACOS
    campaign_metrics['ACOS'] = campaign_metrics.apply(
        lambda x: (x['Spend'] / x['Sales'] * 100) if x['Sales'] > 0 else 0, axis=1
    )
    
    # Merge with Bulk Data (Budgets)
    if 'Daily Budget' not in bulk_df.columns:
        return []

    merged = pd.merge(campaign_metrics, bulk_df, on='Campaign Name', how='inner')
    
    results = []
    for _, row in merged.iterrows():
        spend = row['Spend']
        budget = row['Daily Budget']
        acos = row['ACOS']
        
        if budget <= 0:
            continue
            
        utilization = spend / budget
        
        if acos < 30.0: # Hardcoded "Profitable" threshold for now
             item = BudgetSaturationItem(
                campaign_name=row['Campaign Name'],
                daily_budget=budget,
                spend=spend,
                utilization=0.0, # Placeholder
                acos=acos,
                suggested_budget=budget * 1.2,
                action_type="Budget Increase"
            )
             results.append(item)
            
    return sorted(results, key=lambda x: x.acos)


def calculate_health_score(df: pd.DataFrame) -> HealthScore:
    """
    Calculate overall PPC Health Score (0-100).
    """
    if df.empty:
        return HealthScore(
            score=0, 
            spend_efficiency_score=0, 
            acos_stability_score=0, 
            exact_match_score=0, 
            details={}
        )

    required = ['Spend', 'Sales', 'Match Type']
    if not all(col in df.columns for col in required):
         return HealthScore(
            score=0, 
            spend_efficiency_score=0, 
            acos_stability_score=0, 
            exact_match_score=0, 
            details={}
        )

    total_spend = df['Spend'].sum()
    total_sales = df['Sales'].sum()
    
    # 1. Spend Efficiency (Wasted Spend %)
    # Wasted = Spend with 0 sales
    wasted_spend = df[df['Sales'] == 0]['Spend'].sum()
    waste_ratio = wasted_spend / total_spend if total_spend > 0 else 0
    efficiency_score = max(0, 100 - (waste_ratio * 100))
    
    # 2. Exact Match Share
    exact_spend = df[df['Match Type'] == 'Exact']['Spend'].sum()
    exact_share = exact_spend / total_spend if total_spend > 0 else 0
    # Goal: 30-50% Exact is healthy, >80% is super healthy? Let's say higher is better for control.
    exact_score = min(100, exact_share * 100 * 1.5) # Scale up so 66% = 100
    
    # 3. ACOS Health (Inverse of ACOS vs Target)
    # Lower ACOS = Higher Score (capped at 100)
    overall_acos = (total_spend / total_sales * 100) if total_sales > 0 else 100
    acos_score = max(0, 100 - overall_acos)
    
    # Weighted Total
    # Efficiency 40%, Exact Share 30%, ACOS 30%
    final_score = int((efficiency_score * 0.4) + (exact_score * 0.3) + (acos_score * 0.3))
    
    return HealthScore(
        score=final_score,
        spend_efficiency_score=int(efficiency_score),
        acos_stability_score=int(acos_score),
        exact_match_score=int(exact_score),
        details={
            "wasted_spend": wasted_spend,
            "waste_ratio": waste_ratio,
            "overall_acos": overall_acos
        }
    )
