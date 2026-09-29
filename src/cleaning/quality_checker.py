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
