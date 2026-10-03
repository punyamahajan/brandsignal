import pandas as pd
from typing import List, Dict, Any, Optional

class DataQualityReport:
    """Represents the results of data quality assertions on a dataset."""

    def __init__(self):
        self.is_valid: bool = True
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.metrics: Dict[str, Any] = {}

    def add_error(self, message: str) -> None:
        self.is_valid = False
        self.errors.append(message)

    def add_warning(self, message: str) -> None:
        self.warnings.append(message)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_valid": self.is_valid,
            "errors": self.errors,
            "warnings": self.warnings,
            "metrics": self.metrics
        }

class CatalogQualityChecker:
    """Runs explicit data-quality assertions against cleaned catalog snapshots."""

    def __init__(self, drift_threshold_pct: float = 25.0):
        self.drift_threshold_pct = drift_threshold_pct

    def check_catalog_snapshot(
        self,
        df: pd.DataFrame,
        previous_count: Optional[int] = None
    ) -> DataQualityReport:
        report = DataQualityReport()
        if df.empty:
            report.add_error("Dataset is empty; zero records present.")
            return report

        report.metrics["total_records"] = len(df)

        # 1. Check required schema columns
        required_cols = [
            "snapshot_date", "variant_id", "brand_id", "product_id",
            "product_title", "category_std", "selling_price_inr",
            "is_discounted", "is_available", "collection_timestamp"
        ]
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            report.add_error(f"Missing required schema columns: {missing_cols}")
            return report

        # 2. Check duplicate variant_id in snapshot
        dup_count = df.duplicated(subset=["snapshot_date", "variant_id"]).sum()
        report.metrics["duplicate_variant_count"] = int(dup_count)
        if dup_count > 0:
            report.add_error(f"Found {dup_count} duplicate variant_id entries in snapshot.")

        # 3. Check for NULL or non-positive selling prices
        null_prices = df["selling_price_inr"].isnull().sum()
        non_positive_prices = (df["selling_price_inr"] <= 0).sum()
        report.metrics["null_or_invalid_price_count"] = int(null_prices + non_positive_prices)
        if null_prices > 0:
            report.add_error(f"Found {null_prices} records with NULL selling price.")
        if non_positive_prices > 0:
            report.add_error(f"Found {non_positive_prices} records with non-positive selling price.")

        # 4. Check for inverted discounts (compare_at < selling_price)
        has_compare = df["compare_at_price_inr"].notnull()
        inverted = (df.loc[has_compare, "compare_at_price_inr"] < df.loc[has_compare, "selling_price_inr"]).sum()
        report.metrics["inverted_discount_count"] = int(inverted)
        if inverted > 0:
            report.add_error(f"Found {inverted} records where compare_at_price < selling_price.")

        # 5. Check for missing product_id or variant_id
        missing_pid = df["product_id"].isnull().sum()
        missing_vid = df["variant_id"].isnull().sum()
        report.metrics["missing_id_count"] = int(missing_pid + missing_vid)
        if missing_pid > 0 or missing_vid > 0:
            report.add_error(f"Found records missing IDs (product_id: {missing_pid}, variant_id: {missing_vid}).")

        # 6. Check for large drift in product count
        unique_products = df["product_id"].nunique()
        report.metrics["unique_products"] = unique_products

        if previous_count is not None and previous_count > 0:
            drift_pct = abs(unique_products - previous_count) / previous_count * 100.0
            report.metrics["count_drift_pct"] = round(drift_pct, 2)
            if drift_pct > self.drift_threshold_pct:
                report.add_warning(
                    f"Product count shifted by {drift_pct:.1f}% (from {previous_count} to {unique_products}), "
                    f"exceeding the {self.drift_threshold_pct}% threshold."
                )

        return report

class SearchDemandQualityChecker:
    """Runs data-quality assertions against Google Trends search demand observations."""

    def __init__(self, expected_brands: Optional[List[str]] = None):
        self.expected_brands = expected_brands or ["neemans", "baccabucci", "elevarsports", "plaeto"]

    def check_search_demand(self, df: pd.DataFrame) -> DataQualityReport:
        report = DataQualityReport()
        if df.empty:
            report.add_error("Search demand dataset is empty; zero records present.")
            return report

        report.metrics["total_records"] = len(df)

        # 1. Required schema columns
        required_cols = [
            "week_start_date", "brand_id", "geography", "search_term",
            "relative_search_interest_raw", "relative_search_interest",
            "is_low_volume", "cohort_relative_search_share",
            "collection_timestamp", "raw_file_ref"
        ]
        missing_cols = [c for c in required_cols if c not in df.columns]
        if missing_cols:
            report.add_error(f"Missing required schema columns: {missing_cols}")
            return report

        # 2. Check duplicate (week_start_date, brand_id)
        dup_count = df.duplicated(subset=["week_start_date", "brand_id"]).sum()
        report.metrics["duplicate_count"] = int(dup_count)
        if dup_count > 0:
            report.add_error(f"Found {dup_count} duplicate (week_start_date, brand_id) entries.")

        # 3. Check expected brands representation
        detected_brands = set(df["brand_id"].unique())
        missing_brands = set(self.expected_brands) - detected_brands
        if missing_brands:
            report.add_error(f"Missing expected brands in search demand: {sorted(list(missing_brands))}")
        report.metrics["unique_brands"] = len(detected_brands)

        # 4. Check date validity (ISO format YYYY-MM-DD)
        invalid_dates = pd.to_datetime(df["week_start_date"], format="%Y-%m-%d", errors="coerce").isna().sum()
        if invalid_dates > 0:
            report.add_error(f"Found {invalid_dates} records with invalid date format (expected YYYY-MM-DD).")

        # 5. Low volume and RSI consistency
        low_vol_mask = df["is_low_volume"] == True
        report.metrics["low_volume_count"] = int(low_vol_mask.sum())

        invalid_low_vol = df[low_vol_mask & (df["relative_search_interest"].notna() | (df["relative_search_interest_raw"] != "<1"))]
        if len(invalid_low_vol) > 0:
            report.add_error(f"Found {len(invalid_low_vol)} low volume records with inconsistent raw/numeric values.")

        numeric_rsi = df["relative_search_interest"].dropna()
        out_of_bounds_rsi = ((numeric_rsi < 0) | (numeric_rsi > 100)).sum()
        if out_of_bounds_rsi > 0:
            report.add_error(f"Found {out_of_bounds_rsi} records with relative_search_interest out of bounds [0, 100].")

        # 6. Cohort share consistency
        shares = df["cohort_relative_search_share"].dropna()
        out_of_bounds_share = ((shares < 0.0) | (shares > 100.0)).sum()
        if out_of_bounds_share > 0:
            report.add_error(f"Found {out_of_bounds_share} records with cohort_relative_search_share out of bounds [0, 100].")

        # For weeks with low volume, cohort_relative_search_share must be null
        weeks_with_low_vol = df.loc[low_vol_mask, "week_start_date"].unique()
        shares_in_low_vol_weeks = df[df["week_start_date"].isin(weeks_with_low_vol) & df["cohort_relative_search_share"].notna()]
        if len(shares_in_low_vol_weeks) > 0:
            report.add_error(f"Found {len(shares_in_low_vol_weeks)} calculated cohort shares in weeks containing low-volume (<1) values.")

        return report
