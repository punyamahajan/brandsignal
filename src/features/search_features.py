import pandas as pd
from typing import Dict, Any, Optional, List, Set

class SearchFeatureExtractor:
    """Extracts comparative relative search demand features from Google Trends data."""

    DEFAULT_COHORT_BRANDS = ["neemans", "baccabucci", "elevarsports", "plaeto"]

    @staticmethod
    def compute_weekly_cohort_share(
        df_search: pd.DataFrame,
        expected_brands: Optional[List[str]] = None
    ) -> pd.DataFrame:
        """
        Calculates cohort_relative_search_share:
        cohort_relative_search_share = brand relative_search_interest / sum(relative_search_interest across cohort) * 100

        Strict Analytical Constraints:
        1. Cohort validation: Only derived after validating that all expected cohort brands are represented
           for each comparable period.
        2. Zero synthetic/invented data: If any brand in the period has a missing or low-volume ('<1') value,
           the true cohort sum is indeterminate (sub-unit inequality 0 < interest < 1). We do NOT substitute
           invented numbers (like 0 or 0.5); instead, cohort_relative_search_share is set to None/NaN.
        3. Scope documentation: This metric represents ONLY relative search attention within the selected
           closed four-brand cohort. It is NOT Indian footwear market share, absolute search volume, or unit sales.
        """
        if df_search.empty:
            return df_search

        target_brands = set(expected_brands or SearchFeatureExtractor.DEFAULT_COHORT_BRANDS)
        df_out = df_search.copy()

        if "week_start_date" in df_out.columns:
            pieces = []
            for _, group in df_out.groupby("week_start_date", sort=False, as_index=False):
                pieces.append(SearchFeatureExtractor._calculate_period_share(group, target_brands))
            df_out = pd.concat(pieces, axis=0, ignore_index=True)
        else:
            df_out = SearchFeatureExtractor._calculate_period_share(df_out, target_brands)

        return df_out

    @staticmethod
    def _calculate_period_share(grp: pd.DataFrame, target_brands: Set[str]) -> pd.DataFrame:
        df_grp = grp.copy()
        present_brands = set(df_grp["brand_id"].unique()) if "brand_id" in df_grp.columns else set()

        # Validate that all expected cohort brands are present
        if not target_brands.issubset(present_brands):
            df_grp["cohort_relative_search_share"] = None
            return df_grp

        # Filter strictly to the target cohort
        cohort_mask = df_grp["brand_id"].isin(target_brands) if "brand_id" in df_grp.columns else pd.Series(True, index=df_grp.index)
        cohort_rows = df_grp[cohort_mask]

        # Check for low-volume (<1) or missing values within cohort
        has_low_vol = False
        if "is_low_volume" in cohort_rows.columns:
            has_low_vol = bool(cohort_rows["is_low_volume"].any())

        has_missing = bool(cohort_rows["relative_search_interest"].isna().any())

        if has_low_vol or has_missing:
            # Cannot calculate exact sum without inventing values
            df_grp["cohort_relative_search_share"] = None
            return df_grp

        total_interest = cohort_rows["relative_search_interest"].sum()
        if total_interest > 0:
            df_grp["cohort_relative_search_share"] = (
                df_grp["relative_search_interest"] / total_interest * 100.0
            ).round(2)
        else:
            df_grp["cohort_relative_search_share"] = 0.0

        return df_grp
