import pandas as pd
from typing import Dict, Any

class SearchFeatureExtractor:
    """Extracts comparative relative search demand features from Google Trends data."""

    @staticmethod
    def compute_weekly_cohort_share(df_search_week: pd.DataFrame) -> pd.DataFrame:
        """
        Calculates cohort_relative_search_share:
        Share_i = (RSI_i / Sum(RSI_cohort)) * 100
        """
        if df_search_week.empty:
            return df_search_week

        df_out = df_search_week.copy()
        total_interest = df_out["relative_search_interest"].sum()
        if total_interest > 0:
            df_out["cohort_relative_search_share"] = (
                df_out["relative_search_interest"] / total_interest * 100.0
            ).round(2)
        else:
            df_out["cohort_relative_search_share"] = 0.0

        return df_out
