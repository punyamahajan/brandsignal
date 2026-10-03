import pytest
import pandas as pd
import numpy as np
import os
import duckdb

from dashboard.data_loader import (
    get_db_connection,
    load_snapshot_dates,
    load_brand_features,
    compute_cohort_benchmarks,
    load_category_mix,
    load_price_quantiles,
    load_search_demand_series,
    load_search_summary_stats,
    load_search_spikes,
    format_metric_value
)
from dashboard.charts import (
    build_catalog_scale_chart,
    build_variant_density_chart,
    build_price_positioning_chart,
    build_discount_dual_chart,
    build_price_distribution_chart,
    build_assortment_scatter_chart,
    build_discount_scatter_chart,
    build_category_mix_chart,
    build_search_trends_chart,
    build_cohort_search_share_chart
)

def test_database_connection():
    """Verifies that the database connection opens and queries without error."""
    conn = get_db_connection()
    assert conn is not None
    res = conn.execute("SELECT 1").fetchone()
    assert res[0] == 1
    conn.close()

def test_expected_analytical_tables():
    """Verifies that all required analytical and fact tables exist in DuckDB."""
    conn = get_db_connection()
    tables = [row[0] for row in conn.execute("SHOW TABLES").fetchall()]
    conn.close()

    required_tables = [
        "dim_brand",
        "fact_catalog_snapshot",
        "fact_brand_snapshot_features",
        "fact_brand_category_mix",
        "fact_search_demand"
    ]
    for tbl in required_tables:
        assert tbl in tables, f"Expected table {tbl} missing from database"

def test_snapshot_date_handling():
    """Verifies that catalog snapshot dates are retrieved and include 2026-09-29."""
    dates = load_snapshot_dates()
    assert isinstance(dates, list)
    assert len(dates) > 0
    assert "2026-09-29" in dates

def test_metric_retrieval_and_cohort_benchmarks():
    """Verifies that analytical features and cohort benchmarks calculate deterministically."""
    df_feat = load_brand_features(snapshot_date="2026-09-29")
    assert len(df_feat) == 4
    expected_brands = {"neemans", "baccabucci", "elevarsports", "plaeto"}
    assert set(df_feat["brand_id"]) == expected_brands

    benchmarks = compute_cohort_benchmarks(df_feat)
    assert benchmarks["total_active_products"] == 2050
    assert benchmarks["total_active_skus"] == 10576
    assert benchmarks["median_price_inr"] == 1899.0
    assert benchmarks["median_variant_density"] == pytest.approx(5.77, rel=1e-2)
    assert benchmarks["median_discount_ratio"] == pytest.approx(95.86, rel=1e-2)

def test_brand_selector_filtering():
    """Verifies filtering features by specific brands versus all brands."""
    df_feat = load_brand_features(snapshot_date="2026-09-29")
    
    for brand_id in ["baccabucci", "neemans", "elevarsports", "plaeto"]:
        b_df = df_feat[df_feat["brand_id"] == brand_id]
        assert len(b_df) == 1
        assert b_df.iloc[0]["brand_name"] in ["Bacca Bucci", "Neeman's", "Elevar Sports", "Plaeto"]

def test_null_and_formatting_handling():
    """Verifies format_metric_value for valid numbers and NULL representations."""
    assert format_metric_value(None, "currency") == "N/A"
    assert format_metric_value(np.nan, "percent") == "N/A"
    assert format_metric_value(1499.0, "currency") == "₹1,499"
    assert format_metric_value(98.26, "percent") == "98.3%"
    assert format_metric_value(0.79, "index") == "0.79"
    assert format_metric_value(5744, "integer") == "5,744"

def test_low_volume_search_handling():
    """
    Verifies that Google Trends <1 low-volume values are isolated as NULL
    in relative_search_interest without fabricating 0, and cohort share is NULL for those weeks.
    """
    df_search = load_search_demand_series()
    assert len(df_search) == 212  # 53 weeks * 4 brands

    # Check low volume rows (Plaeto 1 week, Elevar Sports 2 weeks)
    low_vol = df_search[df_search["is_low_volume"] == True]
    assert len(low_vol) == 3
    for _, row in low_vol.iterrows():
        assert pd.isna(row["relative_search_interest"]), "Low volume <1 must be NULL in relative_search_interest"
        assert row["relative_search_interest_raw"] == "<1"

    # Exactly 50 weeks have all 4 brands numeric -> 50 * 4 = 200 non-null cohort_relative_search_share rows
    valid_share = df_search.dropna(subset=["cohort_relative_search_share"])
    assert len(valid_share) == 200

def test_search_spikes_extraction():
    """Verifies that search spikes are extracted based on arithmetic thresholds."""
    df_spikes = load_search_spikes(min_abs_delta=5)
    assert not df_spikes.empty
    assert "rsi_change" in df_spikes.columns
    # Bacca Bucci top spike should be +43
    bb_spikes = df_spikes[df_spikes["brand_id"] == "baccabucci"]
    assert (bb_spikes["rsi_change"] == 43).any()

def test_chart_builders_execution():
    """Verifies that all chart builder functions return valid Altair objects."""
    df_feat = load_brand_features(snapshot_date="2026-09-29")
    df_cat = load_category_mix(snapshot_date="2026-09-29")
    df_quant = load_price_quantiles(snapshot_date="2026-09-29")
    df_search = load_search_demand_series()

    c1 = build_catalog_scale_chart(df_feat)
    c2 = build_variant_density_chart(df_feat)
    c3 = build_price_positioning_chart(df_feat)
    c4 = build_discount_dual_chart(df_feat)
    c5 = build_price_distribution_chart(df_quant)
    c6 = build_assortment_scatter_chart(df_feat)
    c7 = build_discount_scatter_chart(df_feat)
    c8 = build_category_mix_chart(df_cat)
    c9 = build_search_trends_chart(df_search)
    c10 = build_cohort_search_share_chart(df_search)

    for c in [c1, c2, c3, c4, c5, c6, c7, c8, c9, c10]:
        assert c is not None
        assert hasattr(c, "to_dict")
