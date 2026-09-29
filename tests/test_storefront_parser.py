import pytest
from src.cleaning.storefront_cleaner import StorefrontCleaner

def test_category_standardization():
    cleaner = StorefrontCleaner()
    assert cleaner.standardize_category("Flip Flops", "Classic Slippers") == "Flip Flop/Slide"
    assert cleaner.standardize_category("Casual Shoes", "High Top Streetwear Sneakers") == "Sneakers"
    assert cleaner.standardize_category("Loafers", "Men's Knit Slip-On") == "Slip-on/Loafer"
    assert cleaner.standardize_category("Athletic", "Engineered Running Shoe") == "Running/Athletic"
    assert cleaner.standardize_category("Formal", "Oxford Brown") == "Formal/School"

def test_cleaner_handles_valid_variant():
    cleaner = StorefrontCleaner()
    raw_sample = [{
        "collection_timestamp": "2026-09-29T12:00:00Z",
        "snapshot_date": "2026-09-29",
        "brand": "neemans",
        "product_id": 1001,
        "product_title": "Wool Jogger",
        "product_type": "Sneakers",
        "handle": "wool-jogger",
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-02T00:00:00Z",
        "sku": "WJ-BLK-8",
        "variant_id": 5001,
        "variant_title": "Black / UK 8",
        "price": "2999.00",
        "compare_at_price": "3999.00",
        "available": True,
        "source_url": "https://neemans.com/products/wool-jogger",
        "raw_payload_ref": "data/raw/storefront/neemans/2026-09-29/page_1.json"
    }]

    df_cleaned, rejected, stats = cleaner.clean_records(raw_sample)
    assert len(df_cleaned) == 1
    assert len(rejected) == 0
    assert stats["passed"] == 1
    row = df_cleaned.iloc[0]
    assert row["selling_price_inr"] == 2999.00
    assert row["compare_at_price_inr"] == 3999.00
    assert bool(row["is_discounted"]) is True
    assert row["discount_amount_inr"] == 1000.00
    assert row["discount_pct"] == 25.01
    assert row["category_std"] == "Sneakers"
