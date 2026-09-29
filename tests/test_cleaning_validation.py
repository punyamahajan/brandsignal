import pytest
import pandas as pd
from src.cleaning.storefront_cleaner import StorefrontCleaner

def test_inverted_discount_correction():
    """If compare_at_price < price, it must correct compare_at_price to None and is_discounted to False."""
    cleaner = StorefrontCleaner()
    bad_discount_sample = [{
        "collection_timestamp": "2026-09-29T12:00:00Z",
        "snapshot_date": "2026-09-29",
        "brand": "baccabucci",
        "product_id": 2001,
        "product_title": "Street High Top",
        "product_type": "Sneakers",
        "handle": "street-high-top",
        "sku": "BB-01",
        "variant_id": 6001,
        "price": "2499.00",
        "compare_at_price": "1999.00",  # Inverted! compare < price
        "available": True,
        "source_url": "https://baccabucci.com/products/street-high-top",
        "raw_payload_ref": "ref.json"
    }]

    df_cleaned, rejected, stats = cleaner.clean_records(bad_discount_sample)
    assert len(df_cleaned) == 1
    assert stats["inverted_discount_corrected"] == 1
    row = df_cleaned.iloc[0]
    assert row["selling_price_inr"] == 2499.00
    assert pd.isna(row["compare_at_price_inr"])
    assert bool(row["is_discounted"]) == False
    assert pd.isna(row["discount_amount_inr"])

def test_rejection_of_invalid_and_missing_prices():
    cleaner = StorefrontCleaner()
    bad_price_sample = [
        {
            "snapshot_date": "2026-09-29",
            "brand": "plaeto",
            "product_id": 3001,
            "variant_id": 7001,
            "price": "0.00",  # Zero price
            "raw_payload_ref": "ref.json"
        },
        {
            "snapshot_date": "2026-09-29",
            "brand": "plaeto",
            "product_id": 3002,
            "variant_id": 7002,
            "price": "invalid_str",  # Corrupted price
            "raw_payload_ref": "ref.json"
        },
        {
            "snapshot_date": "2026-09-29",
            "brand": "plaeto",
            "product_id": None,  # Missing product ID
            "variant_id": 7003,
            "price": "1499.00",
            "raw_payload_ref": "ref.json"
        }
    ]

    df_cleaned, rejected, stats = cleaner.clean_records(bad_price_sample)
    assert len(df_cleaned) == 0
    assert len(rejected) == 3
    assert stats["rejected_invalid_price"] == 2
    assert stats["rejected_missing_ids"] == 1

def test_duplicate_variant_removal():
    cleaner = StorefrontCleaner()
    duplicates_sample = [
        {
            "snapshot_date": "2026-09-29",
            "brand": "elevarsports",
            "product_id": 4001,
            "variant_id": 8001,
            "price": "3499.00",
            "raw_payload_ref": "ref.json"
        },
        {
            "snapshot_date": "2026-09-29",
            "brand": "elevarsports",
            "product_id": 4001,
            "variant_id": 8001,  # Exact duplicate
            "price": "3499.00",
            "raw_payload_ref": "ref.json"
        }
    ]

    df_cleaned, rejected, stats = cleaner.clean_records(duplicates_sample)
    assert len(df_cleaned) == 1
    assert stats["duplicates_removed"] == 1
