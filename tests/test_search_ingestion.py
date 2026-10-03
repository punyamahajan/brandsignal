import os
import pytest
import pandas as pd
from datetime import datetime
from src.ingestion.search import GoogleTrendsIngestor
from src.features.search_features import SearchFeatureExtractor
from src.cleaning.quality_checker import SearchDemandQualityChecker

COHORT_MAPPING = {
    "neemans": "Neeman's",
    "baccabucci": "Bacca Bucci",
    "elevarsports": "Elevar Sports",
    "plaeto": "Plaeto"
}
EXPECTED_TERMS = list(COHORT_MAPPING.values())
REAL_CSV_PATH = "data/raw/search/google_trends_india_12m.csv"

def test_google_trends_csv_parsing():
    """Validates full end-to-end parsing of the official Google Trends 12m export CSV."""
    ingestor = GoogleTrendsIngestor()
    status, records, ref, msg = ingestor.scan_and_ingest(
        cohort_terms=EXPECTED_TERMS,
        brand_term_mapping=COHORT_MAPPING,
        geography="IN"
    )

    assert status == "SUCCESS"
    assert ref is not None
    assert len(records) == 212  # 53 weeks * 4 brands

    # Check required schema keys on every record
    required_keys = [
        "week_start_date", "brand_id", "geography", "search_term",
        "relative_search_interest_raw", "relative_search_interest",
        "is_low_volume", "cohort_relative_search_share",
        "collection_timestamp", "raw_file_ref"
    ]
    for rec in records:
        for k in required_keys:
            assert k in rec, f"Missing key {k} in record"

def test_expected_brand_validation_success_and_failure(tmp_path):
    """Verifies that all 4 expected brand terms must be present, and missing terms fail validation."""
    ingestor = GoogleTrendsIngestor()

    # 1. Real CSV has all 4 brands
    status, records, _, _ = ingestor.parse_csv_file(
        csv_path=REAL_CSV_PATH,
        cohort_terms=EXPECTED_TERMS,
        brand_term_mapping=COHORT_MAPPING
    )
    assert status == "SUCCESS"
    brands_found = {r["brand_id"] for r in records}
    assert brands_found == {"neemans", "baccabucci", "elevarsports", "plaeto"}

    # 2. Defective CSV with missing brand (only 3 brands)
    bad_csv = tmp_path / "missing_brand.csv"
    bad_csv.write_text(
        "Category: All categories\n\n"
        "Week,Neeman's: (India),Bacca Bucci: (India),Elevar Sports: (India)\n"
        "2026-01-04,30,50,0\n",
        encoding="utf-8"
    )
    status_fail, recs_fail, _, err_msg = ingestor.parse_csv_file(
        csv_path=str(bad_csv),
        cohort_terms=EXPECTED_TERMS,
        brand_term_mapping=COHORT_MAPPING
    )
    assert status_fail == "FAILED"
    assert len(recs_fail) == 0
    assert "Plaeto" in err_msg

def test_date_normalization():
    """Ensures dates are normalized to YYYY-MM-DD and span the expected 53 consecutive weeks."""
    ingestor = GoogleTrendsIngestor()
    status, records, _, _ = ingestor.parse_csv_file(
        csv_path=REAL_CSV_PATH,
        cohort_terms=EXPECTED_TERMS,
        brand_term_mapping=COHORT_MAPPING
    )
    assert status == "SUCCESS"

    df = pd.DataFrame(records)
    unique_dates = sorted(df["week_start_date"].unique())
    assert len(unique_dates) == 53
    assert unique_dates[0] == "2025-09-28"
    assert unique_dates[-1] == "2026-09-27"

    # Validate that every single date parses to valid ISO YYYY-MM-DD
    for d in unique_dates:
        parsed = datetime.strptime(d, "%Y-%m-%d")
        assert parsed.strftime("%Y-%m-%d") == d

def test_missing_and_less_than_one_handling():
    """
    Verifies Google Trends '<1' semantics:
    - Preserves exact raw string '<1'
    - Flags is_low_volume = True
    - Sets numeric relative_search_interest to None (NULL) to prevent invented values (e.g. 0 or 0.5)
    - Sets cohort_relative_search_share to None (NULL) for periods containing '<1'
    """
    ingestor = GoogleTrendsIngestor()
    status, records, _, _ = ingestor.parse_csv_file(
        csv_path=REAL_CSV_PATH,
        cohort_terms=EXPECTED_TERMS,
        brand_term_mapping=COHORT_MAPPING
    )
    assert status == "SUCCESS"
    df = pd.DataFrame(records)

    low_vol_rows = df[df["is_low_volume"] == True]
    assert len(low_vol_rows) == 3

    # Check exact occurrences: Plaeto (2026-09-13), Elevar Sports (2026-09-20, 2026-09-27)
    plaeto_low = low_vol_rows[(low_vol_rows["brand_id"] == "plaeto") & (low_vol_rows["week_start_date"] == "2026-09-13")]
    assert len(plaeto_low) == 1
    assert plaeto_low.iloc[0]["relative_search_interest_raw"] == "<1"
    assert pd.isna(plaeto_low.iloc[0]["relative_search_interest"])
    assert pd.isna(plaeto_low.iloc[0]["cohort_relative_search_share"])

    elevar_low_1 = low_vol_rows[(low_vol_rows["brand_id"] == "elevarsports") & (low_vol_rows["week_start_date"] == "2026-09-20")]
    assert len(elevar_low_1) == 1
    assert pd.isna(elevar_low_1.iloc[0]["relative_search_interest"])

    elevar_low_2 = low_vol_rows[(low_vol_rows["brand_id"] == "elevarsports") & (low_vol_rows["week_start_date"] == "2026-09-27")]
    assert len(elevar_low_2) == 1
    assert pd.isna(elevar_low_2.iloc[0]["relative_search_interest"])

def test_missing_values_synthetic_fixture(tmp_path):
    """Verifies that empty/unrecorded cells are preserved as None without inventing zeros."""
    ingestor = GoogleTrendsIngestor()
    csv_file = tmp_path / "test_missing.csv"
    csv_file.write_text(
        "Category: All categories\n\n"
        "Week,Neeman's: (India),Bacca Bucci: (India),Elevar Sports: (India),Plaeto: (India)\n"
        "2026-01-04,30,50,,10\n",  # Elevar Sports is blank / missing
        encoding="utf-8"
    )

    status, recs, _, _ = ingestor.parse_csv_file(
        csv_path=str(csv_file),
        cohort_terms=EXPECTED_TERMS,
        brand_term_mapping=COHORT_MAPPING
    )
    assert status == "SUCCESS"
    elevar_rec = next(r for r in recs if r["brand_id"] == "elevarsports")
    assert elevar_rec["relative_search_interest"] is None
    assert elevar_rec["relative_search_interest_raw"] == ""
    assert elevar_rec["is_low_volume"] is False
    # All records in that week have None for cohort_relative_search_share
    for r in recs:
        assert r["cohort_relative_search_share"] is None

def test_cohort_relative_search_share_calculation():
    """
    Verifies cohort_relative_search_share calculation:
    Share = RSI / sum(cohort RSI) * 100
    - Exactly 200 rows (50 complete weeks * 4 brands) have calculated shares.
    - Shares sum to ~100.0% for every complete week.
    - Exactly 12 rows (3 weeks with '<1' * 4 brands) have NULL shares.
    """
    ingestor = GoogleTrendsIngestor()
    status, records, _, _ = ingestor.parse_csv_file(
        csv_path=REAL_CSV_PATH,
        cohort_terms=EXPECTED_TERMS,
        brand_term_mapping=COHORT_MAPPING
    )
    assert status == "SUCCESS"
    df = pd.DataFrame(records)

    calc_df = df[df["cohort_relative_search_share"].notna()]
    assert len(calc_df) == 200

    null_df = df[df["cohort_relative_search_share"].isna()]
    assert len(null_df) == 12

    # Verify mathematical sum for each complete week
    for week_date, group in calc_df.groupby("week_start_date"):
        total_share = group["cohort_relative_search_share"].sum()
        assert 99.8 <= total_share <= 100.2, f"Week {week_date} total share sum {total_share} not ~100%"

def test_cohort_share_all_zeros_period():
    """Verifies that if all brands have 0 RSI in a week, cohort_relative_search_share is 0.0 without div-by-zero."""
    df_zero = pd.DataFrame([
        {"week_start_date": "2026-01-04", "brand_id": "neemans", "relative_search_interest": 0, "is_low_volume": False},
        {"week_start_date": "2026-01-04", "brand_id": "baccabucci", "relative_search_interest": 0, "is_low_volume": False},
        {"week_start_date": "2026-01-04", "brand_id": "elevarsports", "relative_search_interest": 0, "is_low_volume": False},
        {"week_start_date": "2026-01-04", "brand_id": "plaeto", "relative_search_interest": 0, "is_low_volume": False},
    ])
    result = SearchFeatureExtractor.compute_weekly_cohort_share(df_zero)
    assert (result["cohort_relative_search_share"] == 0.0).all()

def test_duplicate_observation_handling(tmp_path):
    """Verifies that duplicate observations for the same (week_start_date, brand_id) are deduplicated."""
    ingestor = GoogleTrendsIngestor()
    dup_csv = tmp_path / "dup.csv"
    dup_csv.write_text(
        "Category: All categories\n\n"
        "Week,Neeman's: (India),Bacca Bucci: (India),Elevar Sports: (India),Plaeto: (India)\n"
        "2026-01-04,30,50,0,5\n"
        "2026-01-04,30,50,0,5\n",  # Duplicate row
        encoding="utf-8"
    )

    status, recs, _, msg = ingestor.parse_csv_file(
        csv_path=str(dup_csv),
        cohort_terms=EXPECTED_TERMS,
        brand_term_mapping=COHORT_MAPPING
    )
    assert status == "SUCCESS"
    assert len(recs) == 4  # Deduplicated from 8 to 4
    assert "Removed 4 duplicate observations" in msg

def test_search_demand_quality_checker():
    """Verifies SearchDemandQualityChecker assertion rules."""
    checker = SearchDemandQualityChecker()
    ingestor = GoogleTrendsIngestor()
    status, records, _, _ = ingestor.parse_csv_file(
        csv_path=REAL_CSV_PATH,
        cohort_terms=EXPECTED_TERMS,
        brand_term_mapping=COHORT_MAPPING
    )
    df = pd.DataFrame(records)
    report = checker.check_search_demand(df)
    assert report.is_valid is True
    assert len(report.errors) == 0
    assert report.metrics["total_records"] == 212
    assert report.metrics["unique_brands"] == 4
    assert report.metrics["low_volume_count"] == 3
