from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

class MarketBrandSummary(BaseModel):
    brand_id: str
    brand_name: str
    active_styles: int
    active_skus: int
    median_price: float
    ppi: float
    discount_ratio: float
    tranco_rank: Optional[int] = None

class CohortBenchmarks(BaseModel):
    total_active_products: Optional[int] = None
    total_active_skus: Optional[int] = None
    median_products: Optional[float] = None
    median_skus: Optional[float] = None
    median_variant_density: Optional[float] = None
    median_price_inr: Optional[float] = None
    median_price_iqr_inr: Optional[float] = None
    median_discount_ratio: Optional[float] = None
    median_discount_depth: Optional[float] = None

class MarketSnapshotResponse(BaseModel):
    category: str
    snapshot_date: str
    benchmarks: Dict[str, Any]
    brands: List[Dict[str, Any]]

class ComparisonBrandData(BaseModel):
    id: str
    name: str
    styles: int
    skus: int
    variant_density: float
    median_price: float
    ppi: float
    discount_ratio: float
    median_discount_depth: float
    avg_cohort_share: float

class BrandComparisonResponse(BaseModel):
    brand_a: ComparisonBrandData
    brand_b: ComparisonBrandData
    benchmarks: Dict[str, Any]

class PriceComparisonResponse(BaseModel):
    target: Dict[str, Any]
    comparisons: List[Dict[str, Any]]

class AssortmentComparisonResponse(BaseModel):
    target: Dict[str, Any]
    comparisons: List[Dict[str, Any]]

class DiscountComparisonResponse(BaseModel):
    target: Dict[str, Any]
    comparisons: List[Dict[str, Any]]

class BrandGapResponse(BaseModel):
    target_brand: Dict[str, Any]
    missing_categories: List[str]
    style_breadth_difference: int
    max_peer_styles: int
    variant_density_difference: float

class SearchTrendResponse(BaseModel):
    target_brand: Dict[str, Any]
    search_stats: Dict[str, Any]

class SearchSpikesResponse(BaseModel):
    spikes: List[Dict[str, Any]]
    min_threshold: int

class CategoryMixItem(BaseModel):
    category: str
    sku_count: int
    share_pct: float

class CategoryMixResponse(BaseModel):
    brand_id: str
    brand_name: str
    categories: List[CategoryMixItem]
