import numpy as np
import pandas as pd
from typing import Dict, Any

class PricingFeatureExtractor:
    """Extracts descriptive pricing and markdown features from normalized catalog snapshots."""

    @staticmethod
    def compute_brand_pricing_summary(df_brand: pd.DataFrame) -> Dict[str, Any]:
        """Calculates core pricing metrics for a single brand snapshot."""
        if df_brand.empty:
            return {}

        prices = df_brand["selling_price_inr"].dropna()
        if prices.empty:
            return {}

        p25 = float(np.percentile(prices, 25))
        p50 = float(np.percentile(prices, 50))
        p75 = float(np.percentile(prices, 75))
        iqr = round(p75 - p25, 2)

        # Markdown metrics
        total_skus = len(df_brand)
        discounted_skus = df_brand[df_brand["is_discounted"]]
        discount_ratio = round(len(discounted_skus) / total_skus, 4) if total_skus > 0 else 0.0

        median_discount_depth = None
        if not discounted_skus.empty and discounted_skus["discount_pct"].notnull().any():
            median_discount_depth = round(float(discounted_skus["discount_pct"].median()), 2)

        return {
            "price_min_inr": round(float(prices.min()), 2),
            "price_max_inr": round(float(prices.max()), 2),
            "price_p25_inr": round(p25, 2),
            "price_median_inr": round(p50, 2),
            "price_p75_inr": round(p75, 2),
            "price_iqr_inr": iqr,
            "discounted_sku_ratio": discount_ratio,
            "median_discount_depth_pct": median_discount_depth
        }

    @staticmethod
    def compute_cohort_price_positioning(brand_summaries: Dict[str, Dict[str, Any]]) -> Dict[str, float]:
        """
        Calculates the Price Positioning Index (PPI) for each brand relative to the cohort median price:
        PPI = (Brand_Median / Cohort_Median) * 100
        """
        medians = [s["price_median_inr"] for s in brand_summaries.values() if "price_median_inr" in s]
        if not medians:
            return {}

        cohort_median = float(np.median(medians))
        ppi_results = {}
        for b_id, s in brand_summaries.items():
            if "price_median_inr" in s and cohort_median > 0:
                ppi_results[b_id] = round((s["price_median_inr"] / cohort_median) * 100.0, 2)
            else:
                ppi_results[b_id] = 100.0

        return ppi_results
