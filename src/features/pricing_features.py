import numpy as np
import pandas as pd
from typing import Dict, Any, Optional

class PricingFeatureExtractor:
    """Extracts descriptive pricing and markdown features from normalized catalog snapshots."""

    @staticmethod
    def compute_brand_pricing_summary(df_brand: pd.DataFrame) -> Dict[str, Any]:
        """
        Calculates core pricing and markdown metrics for a single brand snapshot.

        Metrics:
        - price_median_inr: Median listed selling price across active SKUs.
        - price_iqr_inr: 75th percentile selling price - 25th percentile selling price.
        - discounted_catalog_ratio: Percentage of active SKUs where compare_at_price > selling_price.
        - median_discount_depth_pct: For discounted SKUs only: median of ((compare_at - selling) / compare_at) * 100.
        """
        empty_res = {
            "price_min_inr": None,
            "price_p25_inr": None,
            "price_median_inr": None,
            "price_p75_inr": None,
            "price_max_inr": None,
            "price_iqr_inr": None,
            "discounted_sku_count": 0,
            "discounted_catalog_ratio": 0.0,
            "median_discount_depth_pct": None
        }

        if df_brand.empty or "selling_price_inr" not in df_brand.columns:
            return empty_res

        # Validate prices: filter out non-positive or null prices
        valid_price_mask = df_brand["selling_price_inr"].notnull() & (df_brand["selling_price_inr"] > 0)
        prices = df_brand.loc[valid_price_mask, "selling_price_inr"].astype(float)
        if prices.empty:
            return empty_res

        p25 = round(float(np.percentile(prices, 25)), 2)
        p50 = round(float(np.percentile(prices, 50)), 2)
        p75 = round(float(np.percentile(prices, 75)), 2)
        iqr = round(p75 - p25, 2)

        total_skus = len(df_brand)

        # Discounting metrics:
        # active SKUs where compare_at_price > selling_price
        has_discount = False
        discounted_df = pd.DataFrame()
        if "compare_at_price_inr" in df_brand.columns:
            compare_prices = df_brand["compare_at_price_inr"]
            has_discount = (
                compare_prices.notnull() & 
                valid_price_mask & 
                (compare_prices.astype(float) > df_brand["selling_price_inr"].astype(float))
            )
            discounted_df = df_brand[has_discount]

        discounted_sku_count = int(len(discounted_df))

        # discounted_catalog_ratio: Percentage of active SKUs where compare_at_price > selling_price
        discounted_catalog_ratio = round((discounted_sku_count / total_skus) * 100.0, 2) if total_skus > 0 else 0.0

        # median_discount_depth_pct: For discounted SKUs only:
        # ((compare_at_price - selling_price) / compare_at_price) * 100.
        # Do not calculate for non-discounted SKUs.
        median_discount_depth = None
        if discounted_sku_count > 0:
            compare_val = discounted_df["compare_at_price_inr"].astype(float)
            sell_val = discounted_df["selling_price_inr"].astype(float)
            depths = ((compare_val - sell_val) / compare_val) * 100.0

            # Guard against impossible / corrupted values (must be > 0 and <= 100)
            valid_depths = depths[(depths > 0.0) & (depths <= 100.0)]
            if not valid_depths.empty:
                median_discount_depth = round(float(np.median(valid_depths)), 2)

        return {
            "price_min_inr": round(float(prices.min()), 2),
            "price_p25_inr": p25,
            "price_median_inr": p50,
            "price_p75_inr": p75,
            "price_max_inr": round(float(prices.max()), 2),
            "price_iqr_inr": iqr,
            "discounted_sku_count": discounted_sku_count,
            "discounted_catalog_ratio": discounted_catalog_ratio,
            "median_discount_depth_pct": median_discount_depth
        }

    @staticmethod
    def compute_cohort_price_positioning(brand_medians: Dict[str, Optional[float]]) -> Dict[str, Optional[float]]:
        """
        Calculates Price Positioning Index (PPI):
        brand median listed selling price / cohort median listed selling price for the same snapshot.

        Interpretation:
        - 1.00 = equal to cohort median
        - >1.00 = above cohort median (premium)
        - <1.00 = below cohort median (value)
        Listed-price positioning, NOT sales-weighted ASP.
        """
        valid_medians = [m for m in brand_medians.values() if m is not None and m > 0]
        if not valid_medians:
            return {b: None for b in brand_medians}

        cohort_median = float(np.median(valid_medians))
        if cohort_median <= 0:
            return {b: None for b in brand_medians}

        ppi_results = {}
        for b_id, med in brand_medians.items():
            if med is not None and med > 0:
                ppi_results[b_id] = round(med / cohort_median, 2)
            else:
                ppi_results[b_id] = None

        return ppi_results
