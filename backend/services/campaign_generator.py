"""
Auto Campaign Generator.
Generates Amazon-compliant bulk upload files for Sponsored Products Auto campaigns.
Uses official Amazon Advertising bulksheet column format.
"""

import pandas as pd
from io import BytesIO
from typing import List, Optional
from datetime import date


# Amazon Sponsored Products Bulksheet columns (official format)
BULK_COLUMNS = [
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
    'Start Date',
    'End Date',
    'Targeting Type',
    'State',
    'Daily Budget',
    'SKU',
    'ASIN (Informational only)',
    'Ad Group Default Bid',
    'Bid',
    'Keyword Text',
    'Match Type',
    'Bidding Strategy',
    'Placement',
    'Percentage',
]


def create_empty_row() -> dict:
    """Create an empty row with all columns."""
    return {col: '' for col in BULK_COLUMNS}


def generate_campaign_row(
    campaign_name: str,
    daily_budget: float,
    bidding_strategy: str,
    start_date: date,
    portfolio_id: Optional[str] = None
) -> dict:
    """Generate a campaign row for bulk upload."""
    row = create_empty_row()
    row.update({
        'Product': 'Sponsored Products',
        'Entity': 'Campaign',
        'Operation': 'Create',
        'Campaign ID': campaign_name,  # Use campaign name as temporary ID for new campaigns
        'Campaign Name': campaign_name,
        'State': 'enabled',
        'Daily Budget': daily_budget,
        'Start Date': start_date.strftime('%Y%m%d'),
        'Targeting Type': 'Auto',
        'Bidding Strategy': bidding_strategy,
    })
    if portfolio_id:
        row['Portfolio ID'] = portfolio_id
    return row


def generate_bidding_adjustment_row(
    campaign_name: str,
    placement: str,
    percentage: int
) -> dict:
    """
    Generate a bidding adjustment row for placement bid modifiers.
    
    Args:
        campaign_name: Name of the campaign (also used as temporary Campaign ID)
        placement: One of 'Placement Top', 'Placement Product Page', 'Placement Rest Of Search'
        percentage: Bid increase percentage (0-900)
    """
    row = create_empty_row()
    row.update({
        'Product': 'Sponsored Products',
        'Entity': 'Bidding Adjustment',
        'Operation': 'Create',
        'Campaign ID': campaign_name,  # Link to parent campaign
        'Campaign Name': campaign_name,
        'Placement': placement,
        'Percentage': percentage,
    })
    return row


def generate_ad_group_row(
    campaign_name: str,
    ad_group_name: str,
    default_bid: float
) -> dict:
    """Generate an ad group row for bulk upload."""
    row = create_empty_row()
    row.update({
        'Product': 'Sponsored Products',
        'Entity': 'Ad Group',
        'Operation': 'Create',
        'Campaign ID': campaign_name,  # Link to parent campaign
        'Ad Group ID': ad_group_name,  # Use ad group name as temporary ID
        'Campaign Name': campaign_name,
        'Ad Group Name': ad_group_name,
        'State': 'enabled',
        'Ad Group Default Bid': default_bid,
    })
    return row


def generate_product_ad_row(
    campaign_name: str,
    ad_group_name: str,
    sku: str
) -> dict:
    """Generate a product ad row for a SKU."""
    row = create_empty_row()
    row.update({
        'Product': 'Sponsored Products',
        'Entity': 'Product Ad',
        'Operation': 'Create',
        'Campaign ID': campaign_name,  # Link to parent campaign
        'Ad Group ID': ad_group_name,  # Link to parent ad group
        'Campaign Name': campaign_name,
        'Ad Group Name': ad_group_name,
        'State': 'enabled',
        'SKU': sku,
    })
    return row


def generate_auto_targeting_row(
    campaign_name: str,
    ad_group_name: str,
    targeting_type: str,
    bid: Optional[float] = None
) -> dict:
    """
    Generate an auto targeting row for bulk upload.
    
    Args:
        campaign_name: Name of the campaign (also used as Campaign ID)
        ad_group_name: Name of the ad group (also used as Ad Group ID)
        targeting_type: One of 'close-match', 'loose-match', 'substitutes', 'complements'
        bid: Optional bid override for this targeting type
    """
    row = create_empty_row()
    row.update({
        'Product': 'Sponsored Products',
        'Entity': 'Product Targeting',
        'Operation': 'Create',
        'Campaign ID': campaign_name,  # Link to parent campaign
        'Ad Group ID': ad_group_name,  # Link to parent ad group
        'Campaign Name': campaign_name,
        'Ad Group Name': ad_group_name,
        'State': 'enabled',
        'Keyword Text': f'auto-targeting={targeting_type}',
    })
    if bid:
        row['Bid'] = bid
    return row


def generate_auto_campaign_bulk_file(
    campaign_name: str,
    daily_budget: float,
    bidding_strategy: str,
    start_date: date,
    ad_groups: List[dict],
    portfolio: Optional[str] = None,
    placement_bid_adjustment: Optional[dict] = None
) -> BytesIO:
    """
    Generate an Amazon-compliant bulk upload file for an auto campaign.
    
    Args:
        campaign_name: Name of the campaign
        daily_budget: Daily budget in dollars
        bidding_strategy: Bidding strategy (e.g., 'dynamic bids - down only')
        start_date: Campaign start date
        ad_groups: List of ad group configurations, each containing:
            - ad_group_name: str
            - default_bid: float
            - skus: List[str] (SKUs to advertise)
            - close_match: bool
            - close_match_bid: Optional[float]
            - loose_match: bool
            - loose_match_bid: Optional[float]
            - substitutes: bool
            - substitutes_bid: Optional[float]
            - complements: bool
            - complements_bid: Optional[float]
        portfolio: Optional portfolio name/ID
        placement_bid_adjustment: Optional dict with:
            - top_of_search: int (0-900)
            - product_pages: int (0-900)
            - rest_of_search: int (0-900)
    
    Returns:
        BytesIO object containing the Excel file
    """
    rows = []
    
    # 1. Campaign row
    rows.append(generate_campaign_row(
        campaign_name=campaign_name,
        daily_budget=daily_budget,
        bidding_strategy=bidding_strategy,
        start_date=start_date,
        portfolio_id=portfolio
    ))
    
    # 2. Bidding Adjustment rows (placement bid modifiers)
    if placement_bid_adjustment:
        if placement_bid_adjustment.get('top_of_search', 0) > 0:
            rows.append(generate_bidding_adjustment_row(
                campaign_name=campaign_name,
                placement='Placement Top',
                percentage=placement_bid_adjustment['top_of_search']
            ))
        if placement_bid_adjustment.get('product_pages', 0) > 0:
            rows.append(generate_bidding_adjustment_row(
                campaign_name=campaign_name,
                placement='Placement Product Page',
                percentage=placement_bid_adjustment['product_pages']
            ))
        if placement_bid_adjustment.get('rest_of_search', 0) > 0:
            rows.append(generate_bidding_adjustment_row(
                campaign_name=campaign_name,
                placement='Placement Rest Of Search',
                percentage=placement_bid_adjustment['rest_of_search']
            ))
    
    # 3. Ad Group rows, Product Ad rows, and targeting rows
    for ag in ad_groups:
        ag_name = ag.get('ad_group_name', '')
        default_bid = ag.get('default_bid', 0.75)
        skus = ag.get('skus', [])
        
        # Add ad group row
        rows.append(generate_ad_group_row(
            campaign_name=campaign_name,
            ad_group_name=ag_name,
            default_bid=default_bid
        ))
        
        # Add product ad rows for each SKU
        for sku in skus:
            if sku and sku.strip():
                rows.append(generate_product_ad_row(
                    campaign_name=campaign_name,
                    ad_group_name=ag_name,
                    sku=sku.strip()
                ))
        
        # Add auto targeting rows for enabled types
        if ag.get('close_match', False):
            rows.append(generate_auto_targeting_row(
                campaign_name=campaign_name,
                ad_group_name=ag_name,
                targeting_type='close-match',
                bid=ag.get('close_match_bid')
            ))
        
        if ag.get('loose_match', False):
            rows.append(generate_auto_targeting_row(
                campaign_name=campaign_name,
                ad_group_name=ag_name,
                targeting_type='loose-match',
                bid=ag.get('loose_match_bid')
            ))
        
        if ag.get('substitutes', False):
            rows.append(generate_auto_targeting_row(
                campaign_name=campaign_name,
                ad_group_name=ag_name,
                targeting_type='substitutes',
                bid=ag.get('substitutes_bid')
            ))
        
        if ag.get('complements', False):
            rows.append(generate_auto_targeting_row(
                campaign_name=campaign_name,
                ad_group_name=ag_name,
                targeting_type='complements',
                bid=ag.get('complements_bid')
            ))
    
    # Create DataFrame with Amazon column order
    df = pd.DataFrame(rows, columns=BULK_COLUMNS)
    
    # Write to Excel
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Sponsored Products Campaigns', index=False)
    
    output.seek(0)
    return output


def validate_ad_group_config(ad_group: dict) -> List[str]:
    """Validate ad group configuration and return list of errors."""
    errors = []
    
    if not ad_group.get('ad_group_name'):
        errors.append('Ad group name is required')
    
    default_bid = ad_group.get('default_bid', 0)
    if default_bid < 0.02:
        errors.append('Default bid must be at least $0.02')
    
    # Check that at least one targeting type is enabled
    has_targeting = any([
        ad_group.get('close_match', False),
        ad_group.get('loose_match', False),
        ad_group.get('substitutes', False),
        ad_group.get('complements', False)
    ])
    
    if not has_targeting:
        errors.append('At least one targeting type must be enabled')
    
    return errors
