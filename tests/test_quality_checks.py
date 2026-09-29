import pytest
import pandas as pd
from src.cleaning.quality_checker import CatalogQualityChecker

def test_quality_checker_valid_dataset():
    checker = CatalogQualityChecker(drift_threshold_pct=25.0)
    df_valid = pd.DataFrame([{
        "snapshot_date": "2026-09-29",
        "variant_id": 9001,
        "brand_id": "neemans",
        "product_id": 5001,
        "product_title": "Classic Sneaker",
        "category_std": "Sneakers",
        "selling_price_inr": 2499.00,
        "compare_at_price_inr": 3499.00,
        "is_discounted": True,
        "is_available": True,
        "collection_timestamp": "2026-09-29T12:00:00Z"
    }])

    report = checker.check_catalog_snapshot(df_valid, previous_count=5000)
    assert report.is_valid is True
    assert len(report.errors) == 0
    assert report.metrics["total_records"] == 1
    assert report.metrics["duplicate_variant_count"] == 0

def test_quality_checker_catches_negative_price():
    checker = CatalogQualityChecker()
    df_bad = pd.DataFrame([{
        "snapshot_date": "2026-09-29",
        "variant_id": 9002,
        "brand_id": "neemans",
        "product_id": 5002,
        "product_title": "Bad Price Shoe",
        "category_std": "Sneakers",
        "selling_price_inr": -100.00,  # Negative!
        "compare_at_price_inr": None,
        "is_discounted": False,
        "is_available": True,
        "collection_timestamp": "2026-09-29T12:00:00Z"
    }])

    report = checker.check_catalog_snapshot(df_bad)
    assert report.is_valid is False
    assert any("non-positive selling price" in err for err in report.errors)

def test_quality_checker_catches_product_drift_warning():
    checker = CatalogQualityChecker(drift_threshold_pct=25.0)
    df = pd.DataFrame([{
        "snapshot_date": "2026-09-29",
        "variant_id": 9003,
        "brand_id": "plaeto",
        "product_id": 5003,
        "product_title": "Drift Test",
        "category_std": "Sneakers",
        "selling_price_inr": 1500.00,
        "compare_at_price_inr": None,
        "is_discounted": False,
        "is_available": True,
        "collection_timestamp": "2026-09-29T12:00:00Z"
    }])

    # If previous count was 10, current is 1 -> 90% drift!
    report = checker.check_catalog_snapshot(df, previous_count=10)
    assert report.is_valid is True  # Warning does not invalidate dataset
    assert len(report.warnings) == 1
    assert "shifted by 90.0%" in report.warnings[0]
