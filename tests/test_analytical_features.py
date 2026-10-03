import pytest
import numpy as np
import pandas as pd
from src.features.assortment_features import AssortmentFeatureExtractor
from src.features.pricing_features import PricingFeatureExtractor
from src.features.feature_pipeline import AnalyticalFeatureBuilder

def test_assortment_metrics_calculation():
    """Validates active_product_count, active_sku_count, and variant_density."""
    df_sample = pd.DataFrame([
        {"product_id": 101, "variant_id": 1001, "category_std": "Sneakers", "is_available": True},
        {"product_id": 101, "variant_id": 1002, "category_std": "Sneakers", "is_available": True},
        {"product_id": 101, "variant_id": 1003, "category_std": "Sneakers", "is_available": False},
        {"product_id": 102, "variant_id": 1004, "category_std": "Boots", "is_available": True},
    ])

    summary = AssortmentFeatureExtractor.compute_assortment_summary(df_sample)
    assert summary["active_product_count"] == 2
    assert summary["active_sku_count"] == 4
    assert summary["variant_density"] == 2.0  # 4 / 2

def test_pricing_metrics_calculation():
    """Validates median price and IQR price."""
    # Prices: 1000, 2000, 3000, 4000, 5000 -> Median = 3000, P25 = 2000, P75 = 4000, IQR = 2000
    df_sample = pd.DataFrame([
        {"selling_price_inr": 1000.0, "compare_at_price_inr": None},
        {"selling_price_inr": 2000.0, "compare_at_price_inr": None},
        {"selling_price_inr": 3000.0, "compare_at_price_inr": None},
        {"selling_price_inr": 4000.0, "compare_at_price_inr": None},
        {"selling_price_inr": 5000.0, "compare_at_price_inr": None},
    ])

    summary = PricingFeatureExtractor.compute_brand_pricing_summary(df_sample)
    assert summary["price_median_inr"] == 3000.0
    assert summary["price_p25_inr"] == 2000.0
    assert summary["price_p75_inr"] == 4000.0
    assert summary["price_iqr_inr"] == 2000.0

def test_price_positioning_index():
    """
    Validates Price Positioning Index (PPI):
    PPI = brand median / cohort median
    - 1.00 means equal to cohort median
    - >1.00 means above cohort median (premium)
    - <1.00 means below cohort median (value)
    """
    # 4 brands with medians: 1000, 2000, 3000, 4000 -> cohort median = (2000 + 3000) / 2 = 2500.0
    brand_medians = {
        "brand_a": 1000.0,
        "brand_b": 2000.0,
        "brand_c": 3000.0,
        "brand_d": 4000.0
    }
    ppi_map = PricingFeatureExtractor.compute_cohort_price_positioning(brand_medians)
    assert ppi_map["brand_a"] == 0.40  # 1000 / 2500 (< 1)
    assert ppi_map["brand_b"] == 0.80  # 2000 / 2500 (< 1)
    assert ppi_map["brand_c"] == 1.20  # 3000 / 2500 (> 1)
    assert ppi_map["brand_d"] == 1.60  # 4000 / 2500 (> 1)

    # Parity test: equal medians
    parity_medians = {"b1": 2000.0, "b2": 2000.0}
    ppi_parity = PricingFeatureExtractor.compute_cohort_price_positioning(parity_medians)
    assert ppi_parity["b1"] == 1.00
    assert ppi_parity["b2"] == 1.00

def test_discounting_metrics():
    """
    Validates:
    - discounted_catalog_ratio: % of active SKUs with compare_at > price
    - median_discount_depth_pct: median markdown % for discounted SKUs only
    """
    df_sample = pd.DataFrame([
        # Discounted SKUs
        {"selling_price_inr": 800.0, "compare_at_price_inr": 1000.0},   # 20% discount
        {"selling_price_inr": 1500.0, "compare_at_price_inr": 2000.0},  # 25% discount
        {"selling_price_inr": 2100.0, "compare_at_price_inr": 3000.0},  # 30% discount
        # Non-discounted SKUs
        {"selling_price_inr": 2500.0, "compare_at_price_inr": 2500.0},  # 0% discount
        {"selling_price_inr": 1800.0, "compare_at_price_inr": None},    # No compare_at
    ])

    summary = PricingFeatureExtractor.compute_brand_pricing_summary(df_sample)
    # 3 out of 5 are discounted -> 60.0%
    assert summary["discounted_sku_count"] == 3
    assert summary["discounted_catalog_ratio"] == 60.0
    # Depths: [20%, 25%, 30%] -> median = 25.0%
    assert summary["median_discount_depth_pct"] == 25.0

def test_division_by_zero_protection():
    """Ensures feature extractors guard against zero divisions gracefully."""
    df_empty = pd.DataFrame()
    assort_res = AssortmentFeatureExtractor.compute_assortment_summary(df_empty)
    assert assort_res["active_product_count"] == 0
    assert assort_res["active_sku_count"] == 0
    assert assort_res["variant_density"] == 0.0

    pricing_res = PricingFeatureExtractor.compute_brand_pricing_summary(df_empty)
    assert pricing_res["price_median_inr"] is None
    assert pricing_res["discounted_catalog_ratio"] == 0.0
    assert pricing_res["median_discount_depth_pct"] is None

    ppi_empty = PricingFeatureExtractor.compute_cohort_price_positioning({})
    assert ppi_empty == {}

def test_null_and_missing_handling():
    """Verifies that missing compare_at and prices are not fabricated."""
    df_nulls = pd.DataFrame([
        {"selling_price_inr": 1500.0, "compare_at_price_inr": None},
        {"selling_price_inr": 2500.0, "compare_at_price_inr": None},
    ])
    summary = PricingFeatureExtractor.compute_brand_pricing_summary(df_nulls)
    assert summary["discounted_sku_count"] == 0
    assert summary["discounted_catalog_ratio"] == 0.0
    assert summary["median_discount_depth_pct"] is None

def test_impossible_price_and_discount_values():
    """Verifies that negative prices and inverted discounts are not treated as discounts."""
    df_bad = pd.DataFrame([
        # Negative / zero selling price
        {"selling_price_inr": -100.0, "compare_at_price_inr": 500.0},
        {"selling_price_inr": 0.0, "compare_at_price_inr": 500.0},
        # Inverted discount: compare_at < price (must NOT be counted as discounted)
        {"selling_price_inr": 2000.0, "compare_at_price_inr": 1500.0},
        # Valid discount
        {"selling_price_inr": 1000.0, "compare_at_price_inr": 2000.0},
    ])
    summary = PricingFeatureExtractor.compute_brand_pricing_summary(df_bad)
    # Only the last SKU is legitimately discounted
    assert summary["discounted_sku_count"] == 1
    assert summary["median_discount_depth_pct"] == 50.0

def test_tranco_missing_values_and_status():
    """Verifies Tranco unranked and missing status handling."""
    df_catalog = pd.DataFrame([
        {"snapshot_date": "2026-09-29", "brand_id": "baccabucci", "product_id": 1, "variant_id": 1, "selling_price_inr": 1000.0, "compare_at_price_inr": 1200.0, "category_std": "Sneakers", "is_available": True},
        {"snapshot_date": "2026-09-29", "brand_id": "plaeto", "product_id": 2, "variant_id": 2, "selling_price_inr": 1500.0, "compare_at_price_inr": 1800.0, "category_std": "Sneakers", "is_available": True},
    ])
    df_tranco = pd.DataFrame([
        {"observation_date": "2026-09-29", "brand_id": "baccabucci", "domain": "baccabucci.com", "tranco_global_rank": 88548},
        # plaeto has no rank / empty
    ])

    df_feat, _ = AnalyticalFeatureBuilder.build_snapshot_features(
        df_catalog=df_catalog,
        df_tranco=df_tranco
    )
    b_bacca = df_feat[df_feat["brand_id"] == "baccabucci"].iloc[0]
    assert b_bacca["tranco_global_rank"] == 88548
    assert b_bacca["tranco_status"] == "RANKED"

    b_plaeto = df_feat[df_feat["brand_id"] == "plaeto"].iloc[0]
    assert pd.isna(b_plaeto["tranco_global_rank"])
    assert b_plaeto["tranco_status"] == "UNRANKED_OUTSIDE_TOP_1M"

def test_duplicate_brand_snapshot_records():
    """Verifies that duplicate records in the analytical builder are deduplicated per snapshot_date + brand_id."""
    df_catalog = pd.DataFrame([
        {"snapshot_date": "2026-09-29", "brand_id": "neemans", "product_id": 1, "variant_id": 1, "selling_price_inr": 2000.0, "compare_at_price_inr": 2500.0, "category_std": "Sneakers", "is_available": True},
        {"snapshot_date": "2026-09-29", "brand_id": "neemans", "product_id": 1, "variant_id": 2, "selling_price_inr": 2000.0, "compare_at_price_inr": 2500.0, "category_std": "Sneakers", "is_available": True},
    ])
    df_feat, _ = AnalyticalFeatureBuilder.build_snapshot_features(df_catalog=df_catalog)
    # Must yield exactly 1 row for neemans on 2026-09-29
    assert len(df_feat) == 1
    assert df_feat.iloc[0]["active_product_count"] == 1
    assert df_feat.iloc[0]["active_sku_count"] == 2
