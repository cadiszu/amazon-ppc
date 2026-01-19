"""
Bulk Optimizer Service.
Generates Amazon Bulk Operations files for Bid and Budget optimizations.
"""

import pandas as pd
from io import BytesIO
from typing import List, Dict, Any

def generate_bid_changes_file(items: List[Dict[str, Any]]) -> BytesIO:
    """
    Generate bulk file for Bid Changes (e.g. Scale Up, High CPC Down).
    """
    rows = []
    
    for item in items:
        # Determine Record Type based on Targeting format
        # This is a heuristic - ideally we'd pass this info explicitly
        targeting = str(item.get('targeting', ''))
        record_type = "Keyword"
        if targeting.lower().startswith('b0') or 'asin=' in targeting.lower():
            record_type = "Product Target"
            
        row = {
            'Record Type': record_type,
            'Campaign Name': item.get('campaign_name'),
            'Campaign ID': item.get('campaign_id'),
            'Ad Group Name': item.get('ad_group_name', ''),
            'Ad Group ID': item.get('ad_group_id'),
            'Portfolio ID': item.get('portfolio_id'),
            'Keyword Text': targeting if record_type == "Keyword" else None,
            'Product Target': targeting if record_type == "Product Target" else None,
            'Match Type': item.get('match_type'),
            'Max Bid': item.get('suggested_bid'),
            'Operation': 'Update'
        }
        
        rows.append(row)
        
    df = pd.DataFrame(rows)
    
    # Reorder columns to Amazon standard preference (optional but good)
    columns = [
        'Record Type', 'Campaign Name', 'Campaign ID', 'Ad Group Name', 
        'Ad Group ID', 'Portfolio ID', 'Keyword Text', 'Product Target', 
        'Match Type', 'Max Bid', 'Operation'
    ]
    # Filter only columns that exist
    columns = [c for c in columns if c in df.columns]
    df = df[columns]
    
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Bid Changes')
        
    output.seek(0)
    return output


def generate_budget_changes_file(items: List[Dict[str, Any]]) -> BytesIO:
    """
    Generate bulk file for Campaign Budget Changes.
    """
    rows = []
    
    for item in items:
        row = {
            'Record Type': 'Campaign',
            'Campaign Name': item.get('campaign_name'),
            'Campaign ID': item.get('campaign_id'),
            'Daily Budget': item.get('suggested_budget'),
            'Operation': 'Update'
        }
        rows.append(row)
    
    df = pd.DataFrame(rows)
    
    columns = ['Record Type', 'Campaign Name', 'Campaign ID', 'Daily Budget', 'Operation']
    df = df[columns]
    
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Budget Changes')
        
    output.seek(0)
    return output
