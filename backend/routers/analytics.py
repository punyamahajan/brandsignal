from fastapi import APIRouter, Query, HTTPException, Depends
from typing import Dict, Any, List, Optional

from backend.dependencies import get_analytics_tools
from src.tools.analytics_tools import AnalyticsToolsEngine, DEMO_BRAND_MAP
from dashboard.data_loader import load_snapshot_dates

router = APIRouter(prefix="/api/analytics", tags=["analytics"])

@router.get("/snapshot-dates", response_model=List[str])
def get_snapshot_dates(tools: AnalyticsToolsEngine = Depends(get_analytics_tools)):
    """Returns available catalog snapshot dates."""
    dates = load_snapshot_dates(tools.db_path)
    return dates or ["2026-09-29"]

@router.get("/brands")
def get_cohort_brands():
    """Returns list of active benchmark cohort brands."""
    return [{"id": b_id, "name": name} for b_id, name in DEMO_BRAND_MAP.items()]

@router.get("/market")
def get_market_snapshot(
    category: str = Query("D2C Footwear"),
    snapshot_date: str = Query("2026-09-29"),
    tools: AnalyticsToolsEngine = Depends(get_analytics_tools)
):
    """Returns macro-level cohort statistics, benchmarks, and active brand summaries."""
    data, evidence = tools.get_market_snapshot(category=category, snapshot_date=snapshot_date)
    return {
        "data": data,
        "evidence_ids": [e.evidence_id for e in evidence]
    }

@router.get("/compare")
def compare_brands(
    brand_a: str = Query(..., description="Target brand id (e.g. baccabucci)"),
    brand_b: str = Query(..., description="Comparison brand id (e.g. neemans)"),
    snapshot_date: str = Query("2026-09-29"),
    tools: AnalyticsToolsEngine = Depends(get_analytics_tools)
):
    """Provides side-by-side empirical comparison between two specific brands."""
    data, evidence = tools.compare_brands(target_brand=brand_a, comparison_brand=brand_b, snapshot_date=snapshot_date)
    if "error" in data:
        raise HTTPException(status_code=404, detail=data["error"])
    return {
        "data": data,
        "evidence_ids": [e.evidence_id for e in evidence]
    }

@router.get("/pricing")
def compare_pricing(
    target_brand: str = Query("baccabucci"),
    snapshot_date: str = Query("2026-09-29"),
    tools: AnalyticsToolsEngine = Depends(get_analytics_tools)
):
    """Compares listed median prices, price IQR spread, and Price Positioning Index."""
    data, evidence = tools.compare_prices(target_brand=target_brand, snapshot_date=snapshot_date)
    if "error" in data:
        raise HTTPException(status_code=404, detail=data["error"])
    return {
        "data": data,
        "evidence_ids": [e.evidence_id for e in evidence]
    }

@router.get("/assortment")
def compare_assortment(
    target_brand: str = Query("baccabucci"),
    snapshot_date: str = Query("2026-09-29"),
    tools: AnalyticsToolsEngine = Depends(get_analytics_tools)
):
    """Compares style breadth, SKU depth, and variant density."""
    data, evidence = tools.compare_assortment(target_brand=target_brand, snapshot_date=snapshot_date)
    if "error" in data:
        raise HTTPException(status_code=404, detail=data["error"])
    return {
        "data": data,
        "evidence_ids": [e.evidence_id for e in evidence]
    }

@router.get("/discounting")
def compare_discounting(
    target_brand: str = Query("baccabucci"),
    snapshot_date: str = Query("2026-09-29"),
    tools: AnalyticsToolsEngine = Depends(get_analytics_tools)
):
    """Compares promotional penetration and median markdown depth."""
    data, evidence = tools.compare_discounting(target_brand=target_brand, snapshot_date=snapshot_date)
    if "error" in data:
        raise HTTPException(status_code=404, detail=data["error"])
    return {
        "data": data,
        "evidence_ids": [e.evidence_id for e in evidence]
    }

@router.get("/gaps")
def find_brand_gaps(
    target_brand: str = Query("baccabucci"),
    snapshot_date: str = Query("2026-09-29"),
    tools: AnalyticsToolsEngine = Depends(get_analytics_tools)
):
    """Identifies observable category presence and assortment gaps vs peers."""
    data, evidence = tools.find_brand_gaps(target_brand=target_brand, snapshot_date=snapshot_date)
    if "error" in data:
        raise HTTPException(status_code=404, detail=data["error"])
    return {
        "data": data,
        "evidence_ids": [e.evidence_id for e in evidence]
    }

@router.get("/trends/{brand_id}")
def get_search_trends(
    brand_id: str,
    tools: AnalyticsToolsEngine = Depends(get_analytics_tools)
):
    """Returns 53-week search interest trajectory and stats for a brand."""
    data, evidence = tools.get_search_trends(brand_id=brand_id)
    if "error" in data:
        raise HTTPException(status_code=404, detail=data["error"])
    return {
        "data": data,
        "evidence_ids": [e.evidence_id for e in evidence]
    }

@router.get("/spikes")
def get_search_spikes(
    min_abs_delta: int = Query(5, ge=1),
    tools: AnalyticsToolsEngine = Depends(get_analytics_tools)
):
    """Returns observed week-over-week search movements (|Δ| >= threshold)."""
    data, evidence = tools.get_recent_changes(min_abs_delta=min_abs_delta)
    return {
        "data": data,
        "evidence_ids": [e.evidence_id for e in evidence]
    }

@router.get("/category-mix/{brand_id}")
def get_category_mix(
    brand_id: str,
    snapshot_date: str = Query("2026-09-29"),
    tools: AnalyticsToolsEngine = Depends(get_analytics_tools)
):
    """Returns standardized category mix breakdown."""
    data, evidence = tools.get_category_mix(brand_id=brand_id, snapshot_date=snapshot_date)
    if "error" in data:
        raise HTTPException(status_code=404, detail=data["error"])
    return {
        "data": data,
        "evidence_ids": [e.evidence_id for e in evidence]
    }
