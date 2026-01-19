"""
File parsing service for CSV and XLSX files.
Handles Amazon Search Term Reports and Bulk Operations files.
"""

import pandas as pd
from io import BytesIO
from typing import Tuple, List, Optional
import re


# Required columns for Search Term Report
SEARCH_TERM_REQUIRED_COLUMNS = [
    'Campaign Name',
    'Ad Group Name', 
    'Targeting',
    'Match Type',
    'Customer Search Term',
    'Impressions',
    'Clicks',
    'Spend',
]

# Column name mappings for normalization
COLUMN_MAPPINGS = {
    # Sales variations
    '7 day total sales': 'Sales',
    '7 day total sales ($)': 'Sales',
    'total sales': 'Sales',
    'sales': 'Sales',
    # ACOS variations
    'total advertising cost of sales (acos)': 'ACOS',
    'acos': 'ACOS',
    'advertising cost of sales': 'ACOS',
    # ROAS variations
    'total return on advertising spend (roas)': 'ROAS',
    'roas': 'ROAS',
    'return on advertising spend': 'ROAS',
    # Orders variations
    '7 day total orders (#)': 'Orders',
    '7 day total orders': 'Orders',
    'orders': 'Orders',
    # Units variations
    '7 day total units (#)': 'Units',
    '7 day total units': 'Units',
    'units': 'Units',
    # Conversion rate
    '7 day conversion rate': 'Conversion Rate',
    'conversion rate': 'Conversion Rate',
    # CPC variations
    'cost per click (cpc)': 'CPC',
    'cpc': 'CPC',
    'average cpc': 'CPC',
    # CTR variations
    'click-thru rate (ctr)': 'CTR',
    'click-through rate': 'CTR',
    'ctr': 'CTR',
    # Portfolio
    'portfolio name': 'Portfolio',
    'portfolio': 'Portfolio',
    'portfolio id': 'Portfolio ID',
    # Bulk File Standardizations
    'campaign name': 'Campaign Name',
    'campaign': 'Campaign Name',
    'ad group name': 'Ad Group Name',
    # 'ad group': 'Ad Group Name',  <-- REMOVED: In Bulk Files, "Ad Group" is the ID column
    'campaign id': 'Campaign ID',
    'ad group id': 'Ad Group ID',
    'keyword text': 'Keyword Text',
    'match type': 'Match Type',
    'record type': 'Record Type',
    'entity': 'Record Type', 
    'product targeting expression': 'Product Targeting Expression',
}


def detect_file_type(filename: str) -> str:
    """Detect file type from filename extension."""
    ext = filename.lower().split('.')[-1]
    if ext == 'csv':
        return 'csv'
    elif ext in ['xlsx', 'xls']:
        return 'xlsx'
    else:
        raise ValueError(f"Unsupported file type: {ext}. Please upload CSV or XLSX files.")


def parse_file(content: bytes, filename: str) -> pd.DataFrame:
    """Parse file content into a DataFrame."""
    file_type = detect_file_type(filename)
    
    if file_type == 'csv':
        df = pd.read_csv(BytesIO(content))
    else:
        try:
            # Read all sheets to find the correct one
            sheets = pd.read_excel(BytesIO(content), sheet_name=None)
            
            # Prioritize "Sponsored Products Campaigns" sheet (standard Bulk File)
            if 'Sponsored Products Campaigns' in sheets:
                df = sheets['Sponsored Products Campaigns']
            # Fallback for older formats or if not found
            elif 'Sponsored Products' in sheets:
                 df = sheets['Sponsored Products']
            else:
                # Default to first sheet
                df = list(sheets.values())[0]
        except Exception:
            # Fallback if sheet_name=None fails
            df = pd.read_excel(BytesIO(content))
    
    return df


def normalize_column_name(col: str) -> str:
    """Normalize column name for matching."""
    normalized = col.lower().strip()
    return COLUMN_MAPPINGS.get(normalized, col)


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize column names using mapping."""
    new_columns = {}
    for col in df.columns:
        normalized = col.lower().strip()
        if normalized in COLUMN_MAPPINGS:
            new_columns[col] = COLUMN_MAPPINGS[normalized]
        else:
            new_columns[col] = col
    
    return df.rename(columns=new_columns)


def validate_search_term_report(df: pd.DataFrame) -> Tuple[bool, List[str]]:
    """
    Validate that the DataFrame contains required columns for Search Term Report.
    Returns (is_valid, missing_columns).
    """
    # Normalize for comparison
    df_columns_lower = [col.lower().strip() for col in df.columns]
    
    missing = []
    for required in SEARCH_TERM_REQUIRED_COLUMNS:
        req_lower = required.lower().strip()
        
        # Handle aliases
        if req_lower == 'ad group name' and 'ad group' in df_columns_lower:
            continue
            
        if req_lower not in df_columns_lower:
            missing.append(required)
    
    return len(missing) == 0, missing


def clean_percentage(value) -> Optional[float]:
    """Clean percentage values (remove % sign, convert to float)."""
    if pd.isna(value):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        value = value.replace('%', '').replace(',', '').strip()
        try:
            return float(value)
        except ValueError:
            return None
    return None


def clean_currency(value) -> float:
    """Clean currency values (remove $, commas, convert to float)."""
    if pd.isna(value):
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        value = value.replace('$', '').replace(',', '').strip()
        try:
            return float(value)
        except ValueError:
            return 0.0
    return 0.0


def clean_integer(value) -> int:
    """Clean integer values."""
    if pd.isna(value):
        return 0
    if isinstance(value, (int, float)):
        return int(value)
    if isinstance(value, str):
        value = value.replace(',', '').strip()
        try:
            return int(float(value))
        except ValueError:
            return 0
    return 0


def process_search_term_report(df: pd.DataFrame) -> pd.DataFrame:
    """
    Process and clean a Search Term Report DataFrame.
    Normalizes columns and cleans data types.
    """
    # Normalize column names
    df = normalize_columns(df)
    
    # Handle Ad Group alias for STR specifically (Case Insensitive)
    ad_group_col = None
    for col in df.columns:
        if col.lower().strip() == 'ad group':
            ad_group_col = col
            break
            
    if ad_group_col and 'Ad Group Name' not in df.columns:
        df = df.rename(columns={ad_group_col: 'Ad Group Name'})
    
    # Clean numeric columns
    if 'Impressions' in df.columns:
        df['Impressions'] = df['Impressions'].apply(clean_integer)
    
    if 'Clicks' in df.columns:
        df['Clicks'] = df['Clicks'].apply(clean_integer)
    
    if 'Spend' in df.columns:
        df['Spend'] = df['Spend'].apply(clean_currency)
    
    if 'Sales' in df.columns:
        df['Sales'] = df['Sales'].apply(clean_currency)
    
    if 'Orders' in df.columns:
        df['Orders'] = df['Orders'].apply(clean_integer)
    
    if 'Units' in df.columns:
        df['Units'] = df['Units'].apply(clean_integer)
    
    if 'ACOS' in df.columns:
        df['ACOS'] = df['ACOS'].apply(clean_percentage)
    
    if 'ROAS' in df.columns:
        df['ROAS'] = df['ROAS'].apply(clean_percentage)
    
    if 'CTR' in df.columns:
        df['CTR'] = df['CTR'].apply(clean_percentage)
    
    if 'CPC' in df.columns:
        df['CPC'] = df['CPC'].apply(clean_currency)
    
    if 'Conversion Rate' in df.columns:
        df['Conversion Rate'] = df['Conversion Rate'].apply(clean_percentage)
    
    # Parse date column if present
    if 'Date' in df.columns:
        df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
    
    # Fill NaN values for numeric columns
    numeric_cols = ['Impressions', 'Clicks', 'Spend', 'Sales', 'Orders', 'Units']
    for col in numeric_cols:
        if col in df.columns:
            df[col] = df[col].fillna(0)
    
    return df


def is_asin(value: str) -> bool:
    """Check if a value is an ASIN (starts with b0 or B0)."""
    if not isinstance(value, str):
        return False
    value = value.strip().lower()
    return value.startswith('b0') and len(value) == 10


def get_date_range(df: pd.DataFrame) -> dict:
    """Get date range from DataFrame."""
    if 'Date' not in df.columns:
        return {"start": None, "end": None}
    
    dates = df['Date'].dropna()
    if len(dates) == 0:
        return {"start": None, "end": None}
    
    return {
        "start": dates.min().strftime('%Y-%m-%d') if pd.notna(dates.min()) else None,
        "end": dates.max().strftime('%Y-%m-%d') if pd.notna(dates.max()) else None
    }


def get_unique_campaigns(df: pd.DataFrame) -> List[str]:
    """Get unique campaign names from DataFrame."""
    if 'Campaign Name' not in df.columns:
        return []
    return df['Campaign Name'].dropna().unique().tolist()


def get_unique_ad_groups(df: pd.DataFrame) -> List[str]:
    """Get unique ad group names from DataFrame."""
    if 'Ad Group Name' not in df.columns:
        return []
    return df['Ad Group Name'].dropna().unique().tolist()


def get_unique_portfolios(df: pd.DataFrame) -> List[str]:
    """Get unique portfolio names from DataFrame."""
    if 'Portfolio' not in df.columns:
        return []
    return df['Portfolio'].dropna().unique().tolist()


def process_bulk_file(df: pd.DataFrame) -> pd.DataFrame:
    """
    Process Amazon Bulk Operations file to extract campaign budgets.
    Returns DataFrame with ['Campaign Name', 'Daily Budget', 'Campaign ID'].
    """
    # Normalize columns
    df = normalize_columns(df)
    
    # Check for required columns - lenient check as names vary
    # Amazon Bulk file typically has 'Record Type', 'Campaign', 'Daily Budget'
    
    # Map common variations
    column_map = {
        'campaign': 'Campaign',
        'campaign name': 'Campaign',
        'record type': 'Record Type',
        'daily budget': 'Daily Budget',
        'campaign daily budget': 'Daily Budget'
    }
    
    df = df.rename(columns=lambda x: column_map.get(x.lower().strip(), x))
    
    if 'Record Type' not in df.columns or 'Daily Budget' not in df.columns:
        # If standard columns missing, try to detect structure
        if 'Entity' in df.columns: # Newer bulk format sometimes used "Entity"
             df = df.rename(columns={'Entity': 'Record Type'})
    
    # Ensure Campaign column exists
    if 'Campaign' not in df.columns and 'Campaign Name' in df.columns:
         df['Campaign'] = df['Campaign Name']
    
    # Filter for Campaign records
    if 'Record Type' in df.columns:
        campaigns = df[df['Record Type'] == 'Campaign'].copy()
    else:
        # Fallback: records where Daily Budget is present
        campaigns = df[df['Daily Budget'].notna()].copy()
    
    if campaigns.empty:
        return pd.DataFrame(columns=['Campaign Name', 'Daily Budget'])
    
    # Select relevant columns
    cols = ['Campaign', 'Daily Budget']
    if 'Campaign ID' in df.columns:
        cols.append('Campaign ID')
        
    # Create result
    result = campaigns[cols].rename(columns={'Campaign': 'Campaign Name'})
    
    # Clean budget column
    result['Daily Budget'] = result['Daily Budget'].apply(clean_currency)
    
    return result


def enrich_with_ids(items: List[object], bulk_df: pd.DataFrame) -> int:
    """
    Enrich a list of items (objects or dicts) with Campaign ID, Ad Group ID, and Portfolio ID 
    from a Bulk File DataFrame.
    Returns the number of items enriched with at least an Ad Group ID.
    """
    if bulk_df.empty or not items:
        return 0

    try:
        # Prepare Bulk DF for mapping
        bdf = bulk_df.copy()
        if 'Entity' in bdf.columns and 'Record Type' not in bdf.columns:
            bdf = bdf.rename(columns={'Entity': 'Record Type'})
        bdf = normalize_columns(bdf)

        # Helper to clean IDs (remove .0 from floats)
        def clean_id(val):
            if pd.isna(val):
                return None
            s = str(val).strip()
            if s.endswith('.0'):
                return s[:-2]
            return s

        # 1. Campaign IDs & Portfolio IDs
        cid_map = {}
        pid_map = {}
        
        # Helper to add to maps
        def add_to_campaign_maps(df_subset, name_col, id_col, port_col=None):
            for _, row in df_subset.iterrows():
                c_name = str(row[name_col]).lower().strip()
                cid_map[c_name] = clean_id(row[id_col])
                if port_col and port_col in row and pd.notna(row[port_col]):
                    pid_map[c_name] = clean_id(row[port_col])

        # Primary: Campaign Name
        if 'Campaign Name' in bdf.columns and 'Campaign ID' in bdf.columns:
            cols = ['Campaign Name', 'Campaign ID']
            if 'Portfolio ID' in bdf.columns:
                cols.append('Portfolio ID')
            c_data = bdf[cols].dropna(subset=['Campaign Name', 'Campaign ID']).drop_duplicates()
            add_to_campaign_maps(c_data, 'Campaign Name', 'Campaign ID', 'Portfolio ID' if 'Portfolio ID' in bdf.columns else None)
            
        # Secondary: Campaign Name (Informational only)
        c_info_col = next((c for c in bdf.columns if c.lower().strip() == 'campaign name (informational only)'), None)
        if c_info_col and 'Campaign ID' in bdf.columns:
            cols = [c_info_col, 'Campaign ID']
            if 'Portfolio ID' in bdf.columns:
                cols.append('Portfolio ID')
            c_data_info = bdf[cols].dropna(subset=[c_info_col, 'Campaign ID']).drop_duplicates()
            add_to_campaign_maps(c_data_info, c_info_col, 'Campaign ID', 'Portfolio ID' if 'Portfolio ID' in bdf.columns else None)

        # 2. Ad Group IDs
        ag_id_col = 'Ad Group ID'
        if 'Ad Group ID' not in bdf.columns and 'Ad Group' in bdf.columns:
            if 'Ad Group Name' in bdf.columns:
                ag_id_col = 'Ad Group'
        
        agid_map = {}
        if ag_id_col in bdf.columns:
            # Primary Source: Ad Group Name
            if 'Campaign Name' in bdf.columns and 'Ad Group Name' in bdf.columns:
                ag_data = bdf[['Campaign Name', 'Ad Group Name', ag_id_col]].dropna().drop_duplicates()
                for _, row in ag_data.iterrows():
                    cn = str(row['Campaign Name']).lower().strip()
                    an = str(row['Ad Group Name']).lower().strip()
                    agid_map[(cn, an)] = clean_id(row[ag_id_col])
            
            # Secondary Source: Informational Columns
            c_info_col = next((c for c in bdf.columns if c.lower().strip() == 'campaign name (informational only)'), None)
            a_info_col = next((c for c in bdf.columns if c.lower().strip() == 'ad group name (informational only)'), None)
            
            if c_info_col and a_info_col:
                ag_data_info = bdf[[c_info_col, a_info_col, ag_id_col]].dropna().drop_duplicates()
                for _, row in ag_data_info.iterrows():
                    cn = str(row[c_info_col]).lower().strip()
                    an = str(row[a_info_col]).lower().strip()
                    agid_map[(cn, an)] = clean_id(row[ag_id_col])

        # Inject into items
        count = 0
        for item in items:
            # Handle both dicts and objects (Pydantic models)
            is_dict = isinstance(item, dict)
            
            if is_dict:
                c_name = str(item.get('campaign_name', '')).lower().strip()
                a_name = str(item.get('ad_group_name', '')).lower().strip()
            else:
                c_name = str(getattr(item, 'campaign_name', '')).lower().strip()
                a_name = str(getattr(item, 'ad_group_name', '')).lower().strip()
            
            cid = None
            pid = None
            agid = None
            
            if c_name in cid_map:
                cid = cid_map[c_name]
            
            if c_name in pid_map:
                pid = pid_map[c_name]
            
            if (c_name, a_name) in agid_map:
                agid = agid_map[(c_name, a_name)]
                count += 1
            
            if is_dict:
                if cid: item['campaign_id'] = cid
                if pid: item['portfolio_id'] = pid
                if agid: item['ad_group_id'] = agid
            else:
                if cid: setattr(item, 'campaign_id', cid)
                if pid: setattr(item, 'portfolio_id', pid)
                if agid: setattr(item, 'ad_group_id', agid)
        
        return count
        
    except Exception as e:
        print(f"ID Enrichment Failed: {e}")
        return 0
