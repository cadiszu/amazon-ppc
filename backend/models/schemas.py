"""
Pydantic models for API request/response schemas.
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import date
from enum import Enum


class FileType(str, Enum):
    SEARCH_TERM_REPORT = "search_term_report"
    BULK_FILE = "bulk_file"


class UploadResponse(BaseModel):
    """Response after successful file upload."""
    session_id: str
    file_type: FileType
    row_count: int
    columns: List[str]
    date_range: Optional[dict] = None
    campaigns: List[str] = []
    message: str


class ValidationError(BaseModel):
    """File validation error details."""
    error: str
    missing_columns: List[str] = []
    details: Optional[str] = None


class KPIData(BaseModel):
    """Aggregated KPI metrics."""
    total_sales: float
    ad_spend: float
    roas: float
    acos: float
    orders: int
    impressions: int
    clicks: int
    ctr: float
    conversion_rate: float
    avg_cpc: float


class CampaignMetrics(BaseModel):
    """Campaign-level performance metrics."""
    campaign_name: str
    portfolio: Optional[str]
    impressions: int
    clicks: int
    spend: float
    sales: float
    orders: int
    acos: float
    roas: float


class MonthlyData(BaseModel):
    """Monthly aggregated data for charts."""
    month: str
    sales: float
    spend: float


class AnalysisConfig(BaseModel):
    """Configuration for search term analysis."""
    target_acos: float = Field(default=30.0, ge=0, le=100, description="Target ACOS threshold (%)")
    min_spend: float = Field(default=10.0, ge=0, description="Minimum spend for no-sales rule ($)")
    max_sales: float = Field(default=0.0, ge=0, description="Maximum sales for no-sales rule ($)")
    use_negative_phrase: bool = Field(default=False, description="Use Negative Phrase instead of Exact")
    exclude_branded: bool = Field(default=False, description="Exclude branded keywords")
    branded_terms: List[str] = Field(default=[], description="List of brand terms to exclude")
    include_poor_roas: bool = Field(default=False, description="Include converting keywords with poor ROAS")


class SearchTermResult(BaseModel):
    """Result of search term analysis."""
    id: int
    date: Optional[str]
    campaign_name: str
    campaign_id: Optional[str] = None
    ad_group_name: str
    ad_group_id: Optional[str] = None
    portfolio: Optional[str] = None
    portfolio_id: Optional[str] = None
    targeting: str
    match_type: str
    customer_search_term: str
    impressions: int
    clicks: int
    spend: float
    sales: float
    acos: Optional[float]
    orders: int
    rule_triggered: str
    is_asin: bool
    negative_match_type: str
    selected: bool = True


class AnalysisResponse(BaseModel):
    """Response from search term analysis."""
    total_flagged: int
    negative_keywords: int
    negative_asins: int
    results: List[SearchTermResult]


class NegativeExportRequest(BaseModel):
    """Request for generating negative bulk file."""
    session_id: str
    selected_ids: Optional[List[int]] = None
    items: Optional[List[Dict[str, Any]]] = None # Direct data from frontend
    use_negative_phrase: bool = False


class BidChangeRequest(BaseModel):
    """Request for generating bid optimization bulk file."""
    session_id: str
    # List of items to update. Each item usually comes from ScaleOpportunityItem or HighACOSItem.
    # We need minimal info to identify the target.
    items: List[Dict[str, Any]] 


class BudgetChangeRequest(BaseModel):
    """Request for generating budget optimization bulk file."""
    session_id: str
    items: List[Dict[str, Any]]


class AutoTargetingType(str, Enum):
    CLOSE_MATCH = "close-match"
    LOOSE_MATCH = "loose-match"
    SUBSTITUTES = "substitutes"
    COMPLEMENTS = "complements"


class BiddingStrategy(str, Enum):
    DYNAMIC_DOWN = "dynamic bids - down only"
    DYNAMIC_UP_DOWN = "dynamic bids - up and down"
    FIXED = "fixed bids"


class PlacementBidAdjustment(BaseModel):
    """Placement bid adjustment percentages for campaign level."""
    top_of_search: int = Field(default=0, ge=0, le=900, description="Top of Search bid adjustment %")
    product_pages: int = Field(default=0, ge=0, le=900, description="Product Pages bid adjustment %")
    rest_of_search: int = Field(default=0, ge=0, le=900, description="Rest of Search bid adjustment %")


class AdGroupConfig(BaseModel):
    """Configuration for an ad group in auto campaign."""
    ad_group_name: str
    default_bid: float = Field(ge=0.02)
    skus: List[str] = Field(default=[], description="List of SKUs to advertise in this ad group")
    close_match: bool = True
    close_match_bid: Optional[float] = None
    loose_match: bool = True
    loose_match_bid: Optional[float] = None
    substitutes: bool = True
    substitutes_bid: Optional[float] = None
    complements: bool = True
    complements_bid: Optional[float] = None


class AutoCampaignConfig(BaseModel):
    """Configuration for auto campaign generation."""
    campaign_name: str
    portfolio: Optional[str] = None
    daily_budget: float = Field(ge=1.0)
    bidding_strategy: BiddingStrategy = BiddingStrategy.DYNAMIC_DOWN
    start_date: date
    placement_bid_adjustment: Optional[PlacementBidAdjustment] = None
    ad_groups: List[AdGroupConfig]


class FilterOptions(BaseModel):
    """Available filter options from uploaded data."""
    campaigns: List[str]
    ad_groups: List[str]
    portfolios: List[str]
    date_range: dict


class BleedingSpendItem(BaseModel):
    """Item for Bleeding Spend widget (Immediate Negatives)."""
    id: Optional[int] = None
    search_term: str
    campaign_name: str
    ad_group_name: str
    campaign_id: Optional[str] = None
    ad_group_id: Optional[str] = None
    match_type: str
    spend: float
    clicks: int
    severity_score: float
    action_type: str = "Negative"


class HighACOSItem(BaseModel):
    """Item for High ACOS widget (Root Cause Analysis)."""
    id: Optional[int] = None
    search_term: str
    targeting: str # The actual keyword/ASIN targeted
    match_type: str
    campaign_name: str
    campaign_id: Optional[str] = None
    ad_group_id: Optional[str] = None
    acos: float
    spend: float
    sales: float
    root_cause: str # "Low CTR", "High CPC", "Low CVR"
    value: float # The bad metric value (e.g. the specific CTR)
    avg_value: float # The benchmark (e.g. avg CTR)
    action_type: str # "Negative", "Bid Down", "Review"


class ScaleOpportunityItem(BaseModel):
    """Item for Scale Opportunities widget."""
    id: Optional[int] = None
    search_term: str
    targeting: str
    match_type: str
    campaign_name: str
    campaign_id: Optional[str] = None
    ad_group_id: Optional[str] = None
    acos: float
    orders: int
    conversion_rate: float
    current_bid: Optional[float] = None
    suggested_bid: Optional[float] = None
    action_type: str = "Bid Increase"


class BudgetSaturationItem(BaseModel):
    """Item for Budget Saturation widget."""
    campaign_name: str
    daily_budget: float
    spend: float
    utilization: float # spend / budget
    acos: float
    suggested_budget: float
    action_type: str = "Budget Increase"


class HealthScore(BaseModel):
    """PPC Health Score metrics."""
    score: int
    spend_efficiency_score: int
    acos_stability_score: int
    exact_match_score: int
    details: Dict[str, float]


class DecisionCenterResponse(BaseModel):
    """Aggregated response for the Decision Center dashboard."""
    bleeding_spend: List[BleedingSpendItem]
    high_acos: List[HighACOSItem]
    scale_opportunities: List[ScaleOpportunityItem]
    budget_saturation: List[BudgetSaturationItem]
    health_score: HealthScore
    total_urgent_actions: int
    total_growth_actions: int
