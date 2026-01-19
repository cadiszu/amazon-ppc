
import pandas as pd
import numpy as np

def normalize_columns(df):
    COLUMN_MAPPINGS = {
        'campaign name': 'Campaign Name',
        'campaign': 'Campaign Name',
        'ad group name': 'Ad Group Name',
        # 'ad group': 'Ad Group Name',  <-- REMOVED
        'campaign id': 'Campaign ID',
        'ad group id': 'Ad Group ID',
        'portfolio id': 'Portfolio ID',
        'record type': 'Record Type',
        'entity': 'Record Type'
    }
    
    df.columns = [c.strip() for c in df.columns]
    
    renames = {}
    for col in df.columns:
        clean = col.lower().strip()
        if clean in COLUMN_MAPPINGS:
            renames[col] = COLUMN_MAPPINGS[clean]
            
    return df.rename(columns=renames)

def test_extraction(data, name):
    print(f"\n--- Testing {name} ---")
    df = pd.DataFrame(data)
    print(f"Original Columns: {df.columns.tolist()}")
    
    bdf = normalize_columns(df)
    print(f"Normalized Columns: {bdf.columns.tolist()}")
    
    # Logic from analysis.py
    cid_map = {}
    if 'Campaign Name' in bdf.columns and 'Campaign ID' in bdf.columns:
        c_data = bdf[['Campaign Name', 'Campaign ID']].dropna().drop_duplicates()
        cid_map = {str(n).lower().strip(): str(id) for n, id in zip(c_data['Campaign Name'], c_data['Campaign ID'])}
    
    print(f"Campaign Map Size: {len(cid_map)}")
    
    ag_id_col = 'Ad Group ID'
    if 'Ad Group ID' not in bdf.columns and 'Ad Group' in bdf.columns:
         if 'Ad Group Name' in bdf.columns:
             ag_id_col = 'Ad Group'
    
    print(f"Selected AG ID Col: {ag_id_col}")
    
    agid_map = {}
    if ag_id_col in bdf.columns:
        cols = ['Campaign Name', 'Ad Group Name', ag_id_col]
        print(f"Using columns: {cols}")
        if all(c in bdf.columns for c in cols):
            ag_data = bdf[cols].dropna().drop_duplicates()
            print(f"Ad Group Data Rows: {len(ag_data)}")
            print(ag_data)
            
            for _, row in ag_data.iterrows():
                cn = str(row['Campaign Name']).lower().strip()
                an = str(row['Ad Group Name']).lower().strip()
                agid_map[(cn, an)] = str(row[ag_id_col])
        else:
            print(f"Missing columns: {[c for c in cols if c not in bdf.columns]}")
            
    print(f"Ad Group Map Size: {len(agid_map)}")
    if len(agid_map) > 0:
        print(f"Sample: {list(agid_map.items())[0]}")

# Scenario 1: Screenshot (Ad Group column is ID)
data_screenshot = {
    'Entity': ['Campaign', 'Ad group', 'Product Ad'],
    'Campaign ID': ['111', '111', '111'],
    'Ad Group': [None, '222', '222'],  # ID column named "Ad Group"
    'Campaign Name': ['Camp A', 'Camp A', 'Camp A'],
    'Ad Group Name': [None, 'AG 1', 'AG 1']
}

# Scenario 2: User Text (Ad Group ID column exists)
data_text = {
    'Entity': ['Campaign', 'Ad group', 'Product Ad'],
    'Campaign ID': ['111', '111', '111'],
    'Ad Group ID': [None, '222', '222'], # ID column named "Ad Group ID"
    'Campaign name': ['Camp A', 'Camp A', 'Camp A'], # mixed case
    'Ad group name': [None, 'AG 1', 'AG 1'] # mixed case
}

test_extraction(data_screenshot, "Screenshot Scenario")
test_extraction(data_text, "User Text Scenario")
