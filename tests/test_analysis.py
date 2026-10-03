import pytest
import pandas as pd
import numpy as np

from src.analysis.competitive_snapshot import CompetitiveSnapshotAnalyzer
from src.analysis.search_demand_analysis import SearchDemandAnalyzer
from src.analysis.cross_signal_analysis import CrossSignalAnalyzer

@pytest.fixture
def comp_analyzer():
    return CompetitiveSnapshotAnalyzer()

@pytest.fixture
def search_analyzer():
    return SearchDemandAnalyzer()

@pytest.fixture
def cross_analyzer():
    return CrossSignalAnalyzer()

def test_competitive_positioning_table(comp_analyzer):
    """Verifies that the competitive positioning table returns all 4 brands and valid metrics."""
    df = comp_analyzer.get_competitive_positioning_table("2026-09-29")
    assert len(df) == 4
    expected_brands = {"neemans", "baccabucci", "elevarsports", "plaeto"}
    assert set(df["brand_id"]) == expected_brands

    # Check that cohort medians and differences are calculated
    for m in ["active_product_count", "active_sku_count", "variant_density", "price_median_inr"]:
        assert f"{m}_value" in df.columns
        assert f"{m}_cohort_median" in df.columns
        assert f"{m}_diff" in df.columns
        assert f"{m}_pct_diff" in df.columns

    # Verify specific known values
    bb_row = df[df["brand_id"] == "baccabucci"].iloc[0]
    assert bb_row["active_product_count_value"] == 1077
    assert bb_row["active_sku_count_value"] == 5744
    assert bb_row["price_median_inr_value"] == 1499.0
    assert bb_row["price_positioning_index_value"] == 0.79

def test_price_distribution_summary(comp_analyzer):
    """Verifies price quantiles: min <= p25 <= median <= p75 <= max."""
    df = comp_analyzer.get_price_distribution_summary("2026-09-29")
    assert len(df) == 4
    for _, row in df.iterrows():
        assert row["price_min_inr"] <= row["price_p25_inr"]
        assert row["price_p25_inr"] <= row["price_median_inr"]
        assert row["price_median_inr"] <= row["price_p75_inr"]
        assert row["price_p75_inr"] <= row["price_max_inr"]
        assert round(row["price_p75_inr"] - row["price_p25_inr"], 2) == row["price_iqr_inr"]

def test_discount_summary(comp_analyzer):
    """Verifies discounting counts and percentages."""
    df = comp_analyzer.get_discount_summary("2026-09-29")
    assert len(df) == 4
    for _, row in df.iterrows():
        assert row["discounted_sku_count"] + row["non_discounted_sku_count"] == row["total_skus"]
        expected_ratio = round((row["discounted_sku_count"] / row["total_skus"]) * 100.0, 2)
        assert row["discounted_catalog_ratio"] == expected_ratio

def test_search_summary_stats(search_analyzer):
    """Verifies 53-week search demand statistics and low-volume week counts."""
    df = search_analyzer.get_search_summary_stats()
    assert len(df) == 4
    for _, row in df.iterrows():
        assert row["total_weeks"] == 53
        assert row["measurable_weeks"] + row["low_volume_weeks"] == 53
        assert row["min_rsi"] <= row["max_rsi"]
        if row["measurable_weeks"] > 0:
            assert row["mean_rsi"] >= 0

    # Elevar Sports has 2 low volume weeks, Plaeto has 1
    es_row = df[df["brand_id"] == "elevarsports"].iloc[0]
    assert es_row["low_volume_weeks"] == 2
    assert es_row["measurable_weeks"] == 51

    pl_row = df[df["brand_id"] == "plaeto"].iloc[0]
    assert pl_row["low_volume_weeks"] == 1
    assert pl_row["measurable_weeks"] == 52

def test_wow_changes_and_spikes(search_analyzer):
    """Verifies week-over-week changes calculation and spike extraction."""
    df_wow = search_analyzer.get_wow_changes()
    assert not df_wow.empty
    assert "wow_change_rsi" in df_wow.columns

    spikes_drops = search_analyzer.get_top_spikes_and_drops(top_n=3)
    assert "baccabucci" in spikes_drops
    assert "spikes" in spikes_drops["baccabucci"]
    # Bacca Bucci top spike should be +43 in Dec 2025
    top_spike = spikes_drops["baccabucci"]["spikes"].iloc[0]
    assert top_spike["wow_change_rsi"] == 43

def test_cross_signal_dataset_and_correlations(cross_analyzer):
    """Verifies that cross-signal dataset joins correctly and computes descriptive associations."""
    df_cross = cross_analyzer.get_cross_signal_dataset("2026-09-29")
    assert len(df_cross) == 4
    assert "mean_rsi" in df_cross.columns
    assert "active_sku_count" in df_cross.columns
    assert "price_median_inr" in df_cross.columns

    df_assoc = cross_analyzer.compute_descriptive_associations(df_cross)
    assert len(df_assoc) > 0
    assert "pearson_r" in df_assoc.columns
    assert "spearman_rho" in df_assoc.columns
    for _, row in df_assoc.iterrows():
        assert row["sample_size"] == 4
