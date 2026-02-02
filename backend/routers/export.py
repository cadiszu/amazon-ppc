"""
Export router.
Generates Amazon-compliant bulk upload files for negatives and auto campaigns.
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from typing import List
from datetime import date

from models.schemas import NegativeExportRequest, AutoCampaignConfig, BidChangeRequest, BudgetChangeRequest
from services.negative_generator import generate_negatives_bulk_file
from services.campaign_generator import generate_auto_campaign_bulk_file, validate_ad_group_config
from routers.upload import sessions

router = APIRouter()


@router.post("/negatives")
async def export_negatives(request: NegativeExportRequest):
    """
    Generate and download bulk upload file for negative keywords/ASINs.
    """
    session_id = request.session_id
    selected_items = []
    
    try:
        # CASE 1: Direct items from frontend (Most robust - use exactly what's on screen)
        if request.items:
            for i in request.items:
                # Map frontend keys to generator keys
                item = i.copy()
                # Normalize Search Term
                if 'search_term' in item and 'customer_search_term' not in item:
                    item['customer_search_term'] = item['search_term']
                
                # Ensure names are present
                if 'campaign_name' not in item and 'Campaign Name' in item:
                    item['campaign_name'] = item['Campaign Name']
                if 'ad_group_name' not in item and 'Ad Group Name' in item:
                    item['ad_group_name'] = item['Ad Group Name']
                    
                # Determine is_asin if missing
                if 'is_asin' not in item:
                    from services.parser import is_asin
                    item['is_asin'] = is_asin(item.get('customer_search_term', ''))
                    
                selected_items.append(item)
                
        # CASE 2: Selected IDs (Requires backend session)
        else:
            results_key = f"{session_id}_results"
            results_df = None
            
            if results_key in sessions:
                results_df = sessions[results_key]
                if request.selected_ids:
                    results_df = results_df[results_df['id'].isin(request.selected_ids)]
            else:
                # Fallback path for Decision Center items if they weren't stored in 'results'
                from routers.upload import get_session
                from services.parser import is_asin
                try:
                    df = get_session(session_id)
                except Exception:
                     # Re-raise nicely
                     raise HTTPException(status_code=404, detail="Session not found")
                     
                if request.selected_ids:
                    selected_indices = [int(i) for i in request.selected_ids]
                    valid_ids = [i for i in selected_indices if i in df.index]
                    if not valid_ids:
                         raise HTTPException(status_code=400, detail="No valid items selected")
                    results_df = df.loc[valid_ids].copy()
                    results_df['id'] = results_df.index
                else:
                    results_df = df.copy()
                    results_df['id'] = results_df.index
                
                results_df['customer_search_term'] = results_df.get('Customer Search Term', '')
                results_df['campaign_name'] = results_df.get('Campaign Name', '')
                results_df['ad_group_name'] = results_df.get('Ad Group Name', '')
                results_df['is_asin'] = results_df['customer_search_term'].apply(is_asin)

            if len(results_df) == 0:
                raise HTTPException(status_code=400, detail="No items selected for export")
                
            # --- ID Mapping Logic (Only if using Backend data source) ---
            bulk_key = f"{session_id}_bulk"
            campaign_id_map = {}
            ad_group_id_map = {}
            portfolio_id_map = {}
            
            if bulk_key in sessions:
                try:
                    from services.parser import normalize_columns
                    bulk_df = sessions[bulk_key]
                    if 'Entity' in bulk_df.columns and 'Record Type' not in bulk_df.columns:
                        bulk_df = bulk_df.rename(columns={'Entity': 'Record Type'})
                    bulk_df = normalize_columns(bulk_df)
                    
                    def clean_id(val):
                        if pd.isna(val): return None
                        s = str(val).strip()
                        if s.endswith('.0'): return s[:-2]
                        return s

                    cid_map = {}
                    pid_map = {}
                    def add_to_campaign_maps(df_subset, name_col, id_col, port_col=None):
                        for _, row in df_subset.iterrows():
                            c_name = str(row[name_col]).lower().strip()
                            cid_map[c_name] = clean_id(row[id_col])
                            if port_col and port_col in row and pd.notna(row[port_col]):
                                pid_map[c_name] = clean_id(row[port_col])

                    if 'Campaign Name' in bulk_df.columns and 'Campaign ID' in bulk_df.columns:
                        add_to_campaign_maps(bulk_df.dropna(subset=['Campaign Name', 'Campaign ID']), 
                                           'Campaign Name', 'Campaign ID', 
                                           'Portfolio ID' if 'Portfolio ID' in bulk_df.columns else None)
                    
                    campaign_id_map = cid_map
                    portfolio_id_map = pid_map

                    ag_id_col = 'Ad Group ID'
                    if 'Ad Group ID' not in bulk_df.columns and 'Ad Group' in bulk_df.columns:
                        ag_id_col = 'Ad Group'
                    
                    if ag_id_col in bulk_df.columns and 'Ad Group Name' in bulk_df.columns:
                        ag_data = bulk_df[['Campaign Name', 'Ad Group Name', ag_id_col]].dropna().drop_duplicates()
                        for _, row in ag_data.iterrows():
                            c_name = str(row['Campaign Name']).lower().strip()
                            an_name = str(row['Ad Group Name']).lower().strip()
                            ad_group_id_map[(c_name, an_name)] = clean_id(row[ag_id_col])
                except Exception:
                    pass

            selected_items = results_df.to_dict(orient='records')
            for item in selected_items:
                c_name = (item.get('campaign_name') or item.get('Campaign Name') or '').lower().strip()
                a_name = (item.get('ad_group_name') or item.get('Ad Group Name') or '').lower().strip()
                if c_name in campaign_id_map: item['campaign_id'] = campaign_id_map[c_name]
                if c_name in portfolio_id_map: item['portfolio_id'] = portfolio_id_map[c_name]
                if (c_name, a_name) in ad_group_id_map: item['ad_group_id'] = ad_group_id_map[(c_name, a_name)]

        # Generate bulk file
        output = generate_negatives_bulk_file(
            selected_items=selected_items,
            use_negative_phrase=request.use_negative_phrase
        )
        
    except Exception as e:
        print(f"CRITICAL EXPORT ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")
    
    # Return as downloadable file
    filename = f"negative_keywords_{date.today().strftime('%Y%m%d')}.xlsx"
    
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.post("/auto-campaign")
async def export_auto_campaign(config: AutoCampaignConfig):
    """
    Generate and download bulk upload file for an auto campaign.
    """
    # Validate ad groups
    all_errors = []
    for i, ag in enumerate(config.ad_groups):
        errors = validate_ad_group_config(ag.model_dump())
        if errors:
            all_errors.extend([f"Ad Group {i+1}: {e}" for e in errors])
    
    if all_errors:
        raise HTTPException(status_code=400, detail="; ".join(all_errors))
    
    # Generate bulk file
    output = generate_auto_campaign_bulk_file(
        campaign_name=config.campaign_name,
        daily_budget=config.daily_budget,
        bidding_strategy=config.bidding_strategy.value,
        start_date=config.start_date,
        ad_groups=[ag.model_dump() for ag in config.ad_groups],
        portfolio=config.portfolio,
        placement_bid_adjustment=config.placement_bid_adjustment.model_dump() if config.placement_bid_adjustment else None
    )
    
    # Return as downloadable file
    safe_name = config.campaign_name.replace(' ', '_').replace('/', '_')[:50]
    filename = f"auto_campaign_{safe_name}_{date.today().strftime('%Y%m%d')}.xlsx"
    
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.post("/negatives/preview")
async def preview_negatives(request: NegativeExportRequest):
    """
    Preview the negative keywords/ASINs that would be exported.
    Returns the data without generating a file.
    """
    session_id = request.session_id
    results_key = f"{session_id}_results"
    
    if results_key not in sessions:
        raise HTTPException(
            status_code=404,
            detail="No analysis results found. Please run search term analysis first."
        )
    
    results_df = sessions[results_key]
    
    # Filter to selected IDs
    if request.selected_ids:
        results_df = results_df[results_df['id'].isin(request.selected_ids)]
    
    # Group by type
    keywords = results_df[~results_df['is_asin']].to_dict(orient='records')
    asins = results_df[results_df['is_asin']].to_dict(orient='records')
    
    return {
        "total": len(results_df),
        "negative_keywords": {
            "count": len(keywords),
            "items": keywords
        },
        "negative_asins": {
            "count": len(asins),
            "items": asins
        },
        "match_type": "Negative Phrase" if request.use_negative_phrase else "Negative Exact"
    }


@router.post("/bid-optimization")
async def export_bid_optimization(request: BidChangeRequest):
    """
    Generate bulk file for Bid optimizations (Scale Up / High CPC Down).
    """
    from services.bulk_optimizer import generate_bid_changes_file
    
    output = generate_bid_changes_file(request.items)
    
    filename = f"bid_changes_{date.today().strftime('%Y%m%d')}.xlsx"
    
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.post("/budget-optimization")
async def export_budget_optimization(request: BudgetChangeRequest):
    """
    Generate bulk file for Budget optimizations.
    """
    from services.bulk_optimizer import generate_budget_changes_file
    
    output = generate_budget_changes_file(request.items)
    
    filename = f"budget_changes_{date.today().strftime('%Y%m%d')}.xlsx"
    
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
