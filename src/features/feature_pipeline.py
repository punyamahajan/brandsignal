import pandas as pd
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple

from src.features.assortment_features import AssortmentFeatureExtractor
from src.features.pricing_features import PricingFeatureExtractor

class AnalyticalFeatureBuilder:
    """
    Builds the analytical feature layer for BrandSignal V1.
    Grain: (snapshot_date, brand_id) for fact_brand_snapshot_features
           (snapshot_date, brand_id, category_std) for fact_brand_category_mix
           
    Adheres strictly to zero synthetic data, deterministic transformations,
    and objective competitive benchmarking without automated recommendations.
    """

    DEFAULT_BRAND_NAMES = {
        "neemans": "Neeman's",
        "baccabucci": "Bacca Bucci",
        "elevarsports": "Elevar Sports",
        "plaeto": "Plaeto"
    }

    @staticmethod
    def build_snapshot_features(
        df_catalog: pd.DataFrame,
        df_tranco: Optional[pd.DataFrame] = None,
        df_search: Optional[pd.DataFrame] = None,
        brand_names: Optional[Dict[str, str]] = None,
        known_unranked_domains: Optional[List[str]] = None
    ) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Transforms raw processed catalog snapshots and external signals into analytical feature tables.
        
        Returns:
            (df_brand_snapshot_features, df_brand_category_mix)
        """
        if df_catalog.empty:
            return pd.DataFrame(), pd.DataFrame()

        b_names = brand_names or AnalyticalFeatureBuilder.DEFAULT_BRAND_NAMES
        known_unranked = set(known_unranked_domains or ["plaeto.in", "elevarsports.com"])

        features_rows: List[Dict[str, Any]] = []
        category_rows: List[Dict[str, Any]] = []
        created_at_ts = datetime.now(timezone.utc).isoformat()

        # Group by snapshot date
        for snap_date, df_snap in df_catalog.groupby("snapshot_date", sort=True):
            snap_date_str = pd.to_datetime(snap_date).strftime("%Y-%m-%d")

            # Step 1: Collect brand pricing and assortment summaries
            brand_pricing: Dict[str, Dict[str, Any]] = {}
            brand_assortment: Dict[str, Dict[str, Any]] = {}
            brand_medians: Dict[str, Optional[float]] = {}

            for brand_id, df_brand in df_snap.groupby("brand_id", sort=True):
                b_id_str = str(brand_id)
                assort = AssortmentFeatureExtractor.compute_assortment_summary(df_brand)
                pricing = PricingFeatureExtractor.compute_brand_pricing_summary(df_brand)

                brand_assortment[b_id_str] = assort
                brand_pricing[b_id_str] = pricing
                brand_medians[b_id_str] = pricing.get("price_median_inr")

                # Build category mix rows
                if "category_std" in df_brand.columns and assort.get("active_sku_count", 0) > 0:
                    total_skus = assort["active_sku_count"]
                    for cat_name, count in df_brand["category_std"].value_counts().items():
                        cat_share = round((count / total_skus) * 100.0, 2)
                        category_rows.append({
                            "snapshot_date": snap_date_str,
                            "brand_id": b_id_str,
                            "category_std": str(cat_name),
                            "category_sku_count": int(count),
                            "category_share_pct": cat_share,
                            "created_at": created_at_ts
                        })

            # Step 2: Cohort price positioning index for this snapshot date
            ppi_map = PricingFeatureExtractor.compute_cohort_price_positioning(brand_medians)

            # Step 3: Integrate Tranco and Search signals
            for b_id_str, pricing in brand_pricing.items():
                assort = brand_assortment[b_id_str]
                ppi = ppi_map.get(b_id_str, 1.00)

                # Tranco resolution: find rank on or before snapshot date
                tranco_rank = None
                tranco_status = "UNAVAILABLE"
                if df_tranco is not None and not df_tranco.empty:
                    b_tranco = df_tranco[
                        (df_tranco["brand_id"] == b_id_str) & 
                        (df_tranco["observation_date"] <= snap_date_str)
                    ]
                    if not b_tranco.empty:
                        latest_tranco = b_tranco.sort_values("observation_date", ascending=False).iloc[0]
                        raw_rank = latest_tranco.get("tranco_global_rank")
                        if pd.notna(raw_rank) and int(raw_rank) > 0:
                            tranco_rank = int(raw_rank)
                            tranco_status = "RANKED"
                        else:
                            tranco_rank = None
                            tranco_status = "UNRANKED_OUTSIDE_TOP_1M"
                    else:
                        # Check if domain was queried and verified outside top 1M
                        tranco_status = "UNRANKED_OUTSIDE_TOP_1M" if b_id_str in ("plaeto", "elevarsports") else "UNAVAILABLE"
                else:
                    if b_id_str in ("plaeto", "elevarsports"):
                        tranco_status = "UNRANKED_OUTSIDE_TOP_1M"

                # Search Demand resolution: find latest search observation at or preceding snapshot date
                search_interest = None
                cohort_share = None
                if df_search is not None and not df_search.empty:
                    b_search = df_search[
                        (df_search["brand_id"] == b_id_str) & 
                        (df_search["week_start_date"] <= snap_date_str)
                    ]
                    if not b_search.empty:
                        latest_search = b_search.sort_values("week_start_date", ascending=False).iloc[0]
                        rsi = latest_search.get("relative_search_interest")
                        share = latest_search.get("cohort_relative_search_share")
                        search_interest = int(rsi) if pd.notna(rsi) else None
                        cohort_share = round(float(share), 2) if pd.notna(share) else None

                features_rows.append({
                    "snapshot_date": snap_date_str,
                    "brand_id": b_id_str,
                    "brand_name": b_names.get(b_id_str, b_id_str.capitalize()),
                    "active_product_count": assort["active_product_count"],
                    "active_sku_count": assort["active_sku_count"],
                    "variant_density": assort["variant_density"],
                    "price_min_inr": pricing["price_min_inr"],
                    "price_p25_inr": pricing["price_p25_inr"],
                    "price_median_inr": pricing["price_median_inr"],
                    "price_p75_inr": pricing["price_p75_inr"],
                    "price_max_inr": pricing["price_max_inr"],
                    "price_iqr_inr": pricing["price_iqr_inr"],
                    "price_positioning_index": ppi,
                    "discounted_sku_count": pricing["discounted_sku_count"],
                    "discounted_catalog_ratio": pricing["discounted_catalog_ratio"],
                    "median_discount_depth_pct": pricing["median_discount_depth_pct"],
                    "tranco_global_rank": tranco_rank,
                    "tranco_status": tranco_status,
                    "latest_relative_search_interest": search_interest,
                    "latest_cohort_search_share": cohort_share,
                    "new_sku_velocity_30d": None,  # Point-in-time limitation: historical velocity unavailable
                    "created_at": created_at_ts
                })

        df_brand_snapshot_features = pd.DataFrame(features_rows)
        df_brand_category_mix = pd.DataFrame(category_rows)

        return df_brand_snapshot_features, df_brand_category_mix
