"""
Negative Keyword and Product Target Generator.
Generates Amazon-compliant bulk upload files for negatives.
"""

import pandas as pd
from io import BytesIO
from typing import List
from services.parser import is_asin


# Standard Amazon Bulk Upload Columns (v2.0 / Extended)
BULK_HEADERS = [
    'Product',
    'Entity',
    'Operation',
    'Campaign ID',
    'Ad Group ID',
    'Portfolio ID',
    'Ad ID',
    'Keyword ID',
    'Product Targeting ID',
    'Campaign Name',
    'Ad Group Name',
    'Campaign Name (Informational only)',
    'Ad Group Name (Informational only)',
    'Portfolio Name (Informational only)',
    'Start Date',
    'End Date',
    'Targeting Type',
    'State',
    'Campaign State (Informational only)',
    'Ad Group State (Informational only)',
    'Daily Budget',
    'SKU',
    'ASIN (Informational only)',
    'Eligibility Status (Informational only)',
    'Reason for Ineligibility (Informational only)',
    'Ad Group Default Bid',
    'Ad Group Default Bid (Informational only)',
    'Bid',
    'Keyword Text',
    'Match Type',
    'Bidding Strategy',
    'Placement',
    'Percentage',
    'Product Targeting Expression',
    'Resolved Product Targeting Expression (Informational only)',
    'Impressions',
    'Clicks',
    'Click-through Rate',
    'Spend',
    'Sales',
    'Orders',
    'Units',
    'Conversion Rate',
    'ACOS',
    'CPC',
    'ROAS'
]


def classify_negative_type(search_term: str) -> str:
    """
    Classify whether a search term should be a negative keyword or negative product target.
    """
    if is_asin(search_term):
        return 'negative_product'
    return 'negative_keyword'


def generate_empty_row() -> dict:
    """Create a row with all headers empty."""
    return {col: None for col in BULK_HEADERS}


def generate_negatives_bulk_file(
    selected_items: List[dict],
    use_negative_phrase: bool = False
) -> BytesIO:
    """
    Generate an Amazon-compliant bulk upload file for negative keywords and product targets.
    Uses the single-sheet format with specific headers.
    """
    rows = []
    
    match_type = 'Negative Phrase' if use_negative_phrase else 'Negative Exact'
    
    for item in selected_items:
        search_term = item.get('customer_search_term', '').replace('/', ' ')
        campaign_name = item.get('campaign_name', '')
        # Remove extra quotes if present in campaign name
        campaign_name = campaign_name.strip("'").strip('"')
        
        ad_group_name = item.get('ad_group_name', '')
        campaign_id = item.get('campaign_id', '')
        ad_group_id = item.get('ad_group_id', '')
        portfolio_id = item.get('portfolio_id', '')
        item_is_asin = item.get('is_asin', False)
        
        row = generate_empty_row()
        
        # Common fields for Negative Keyword and Product Targeting
        row['Product'] = 'Sponsored Products'
        row['Operation'] = 'Create'
        
        # IDs mapping
        if campaign_id:
            row['Campaign ID'] = campaign_id
        if ad_group_id:
            row['Ad Group ID'] = ad_group_id
        if portfolio_id:
            row['Portfolio ID'] = portfolio_id
            
        # Names mapping
        row['Campaign Name'] = campaign_name
        row['Ad Group Name'] = ad_group_name
        
        row['State'] = 'Enabled'
        
        if item_is_asin:
            # Negative Product Targeting
            row['Entity'] = 'Negative Product Targeting' # User macro uses this
            # row['Entity'] = 'Ad Group Negative Product Targeting' # 2.0 Standard
            # Following macro: "Negative Product Targeting"
            
            # Targeting Expression
            # Macro: asin="B0..."
            row['Product Targeting Expression'] = f'asin="{search_term.upper()}"'
            
        else:
            # Negative Keyword
            row['Entity'] = 'Negative Keyword' # User macro uses this
            # row['Entity'] = 'Ad Group Negative Keyword' # 2.0 Standard
            # Following macro: "Negative Keyword"
            
            row['Keyword Text'] = search_term
            row['Match Type'] = match_type
            
        rows.append(row)
    
    # Create DataFrame
    output = BytesIO()
    
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        if not rows:
            # Empty template
            df = pd.DataFrame(columns=BULK_HEADERS)
        else:
            df = pd.DataFrame(rows, columns=BULK_HEADERS)
            
        # Write to "Sponsored Products Campaigns" sheet (Standard for Bulk 2.0)
        # Or "Bulk" as in macro? Macro reads from Bulk, writes to "Working" then likely used for upload.
        # Standard sheet name is "Sponsored Products Campaigns".
        df.to_excel(writer, sheet_name='Sponsored Products Campaigns', index=False)
    
    output.seek(0)
    return output


def generate_negatives_csv(
    selected_items: List[dict],
    use_negative_phrase: bool = False
) -> BytesIO:
    """
    Generate a CSV bulk upload file for negative keywords.
    """
    # Simply reuse the Excel logic but save as CSV
    # Note: CSV usually doesn't have sheets, but structure is same rows
    excel_io = generate_negatives_bulk_file(selected_items, use_negative_phrase)
    df = pd.read_excel(excel_io)
    
    output = BytesIO()
    df.to_csv(output, index=False)
    output.seek(0)
    return output
