import duckdb
import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional, Tuple

from dashboard.data_loader import (
    get_db_connection,
    load_brand_features,
    compute_cohort_benchmarks,
    load_category_mix,
    load_price_quantiles,
    load_search_summary_stats,
    load_search_spikes,
    load_search_demand_series
)
from src.conversation.entity_resolver import CANONICAL_BRANDS, EntityResolver

METRIC_DEFINITIONS = {
    "active_product_count": {
        "name": "Active Product Styles",
        "definition": "Number of unique parent product styles offered by a merchant in the storefront snapshot.",
        "grain": "Snapshot date + Brand",
        "limitation": "Measures catalog breadth, not sales volume or inventory depth."
    },
    "active_sku_count": {
        "name": "Active SKU Count",
        "definition": "Total number of distinct purchasable SKU variant options (size, color, material) in the catalog.",
        "grain": "Snapshot date + Brand",
        "limitation": "Listing options only; out-of-stock items still listed are counted unless delisted by merchant."
    },
    "variant_density": {
        "name": "Variant Density",
        "definition": "Average number of purchasable variant SKUs per parent product style (active_sku_count / active_product_count).",
        "grain": "Snapshot date + Brand",
        "limitation": "High variant density can reflect deep sizing/color options or duplicate listings."
    },
    "price_median_inr": {
        "name": "Median Listed Price (INR)",
        "definition": "50th percentile of active listed variant selling prices on digital storefronts.",
        "grain": "Snapshot date + Brand",
        "limitation": "Reflects merchant asking prices; not sales-weighted Average Selling Price (ASP)."
    },
    "price_positioning_index": {
        "name": "Price Positioning Index (PPI)",
        "definition": "Ratio of brand median selling price to cohort median selling price (1.00 = cohort median).",
        "grain": "Snapshot date + Brand",
        "limitation": "Relative index within this 4-brand cohort only; not an industry-wide price index."
    },
    "discounted_catalog_ratio": {
        "name": "Discounted Catalog Ratio (%)",
        "definition": "Percentage of active SKUs where compare_at_price > selling_price.",
        "grain": "Snapshot date + Brand",
        "limitation": "compare_at_price is merchant-defined; does not prove customer realized discount or past transaction price."
    },
    "median_discount_depth_pct": {
        "name": "Median Discount Depth (%)",
        "definition": "Median percentage markdown calculated strictly across discounted SKUs ((compare_at - selling) / compare_at * 100).",
        "grain": "Snapshot date + Brand (discounted items only)",
        "limitation": "Excludes full-price SKUs; does not capture cart-level promo codes or bundle deals."
    },
    "relative_search_interest": {
        "name": "Relative Search Interest (RSI)",
        "definition": "Google Trends normalized search index [0–100] relative to peak query attention in India.",
        "grain": "Weekly + Brand",
        "limitation": "Indexed query attention, not absolute search volume, impression counts, or revenue."
    },
    "cohort_relative_search_share": {
        "name": "Cohort Relative Search Share (%)",
        "definition": "Share of relative search attention within the 4-brand cohort during comparable weeks.",
        "grain": "Weekly + Brand (comparable weeks only)",
        "limitation": "Measures attention strictly within this 4-brand cohort; NOT Indian footwear market share."
    },
    "low_volume": {
        "name": "Google Trends <1 Low Volume",
        "definition": "Indicates search activity existed above zero but fell below the 1.0 unit normalization threshold.",
        "grain": "Weekly + Brand",
        "limitation": "Cannot be converted to 0 (which falsely implies zero queries) or 1 (which overstates volume)."
    },
    "tranco_global_rank": {
        "name": "Tranco Global Domain Rank",
        "definition": "Global web traffic popularity rank across top 1 million domains based on DNS queries.",
        "grain": "Observation date + Domain",
        "limitation": "Global traffic measure, not domestic India web traffic. Unranked brands sit outside the Top 1M."
    }
}

class AnalyticsService:
    """
    Read-only deterministic analytical query service.
    Directly accesses DuckDB fact tables and analytical summaries.
    Returns structured, auditable evidence payloads with zero hallucinations.
    """

    def __init__(self, db_path: str = "data/processed/brandsignal.duckdb"):
        self.db_path = db_path

    def get_market_overview(self, snapshot_date: str = "2026-09-29") -> Dict[str, Any]:
        """Returns macro-level cohort statistics across catalog, pricing, and search."""
        df_feat = load_brand_features(self.db_path, snapshot_date)
        benchmarks = compute_cohort_benchmarks(df_feat)
        df_search = load_search_summary_stats(self.db_path)

        brand_summaries = []
        for _, row in df_feat.iterrows():
            b_id = row["brand_id"]
            s_row = df_search[df_search["brand_id"] == b_id]
            s_data = s_row.iloc[0] if not s_row.empty else {}
            brand_summaries.append({
                "brand_id": b_id,
                "brand_name": row["brand_name"],
                "active_styles": int(row["active_product_count"]),
                "active_skus": int(row["active_sku_count"]),
                "variant_density": float(row["variant_density"]),
                "median_price": float(row["price_median_inr"]),
                "ppi": float(row["price_positioning_index"]),
                "discount_ratio": float(row["discounted_catalog_ratio"]),
                "median_discount_depth": float(row["median_discount_depth_pct"]) if pd.notna(row["median_discount_depth_pct"]) else None,
                "tranco_rank": int(row["tranco_global_rank"]) if pd.notna(row["tranco_global_rank"]) else None,
                "mean_rsi": float(s_data.get("mean_rsi", 0.0)) if pd.notna(s_data.get("mean_rsi")) else None,
                "avg_cohort_share": float(s_data.get("avg_cohort_share", 0.0)) if pd.notna(s_data.get("avg_cohort_share")) else None
            })

        return {
            "snapshot_date": snapshot_date,
            "cohort_size": len(df_feat),
            "benchmarks": benchmarks,
            "brands": brand_summaries
        }

    def compare_brands(self, brand_a: str, brand_b: str, snapshot_date: str = "2026-09-29") -> Dict[str, Any]:
        """Provides side-by-side empirical comparison between two specific brands."""
        df_feat = load_brand_features(self.db_path, snapshot_date)
        df_search = load_search_summary_stats(self.db_path)
        benchmarks = compute_cohort_benchmarks(df_feat)

        row_a = df_feat[df_feat["brand_id"] == brand_a]
        row_b = df_feat[df_feat["brand_id"] == brand_b]

        if row_a.empty or row_b.empty:
            return {"error": f"One or both brands ({brand_a}, {brand_b}) not found in dataset."}

        data_a = row_a.iloc[0]
        data_b = row_b.iloc[0]

        s_a = df_search[df_search["brand_id"] == brand_a].iloc[0] if not df_search[df_search["brand_id"] == brand_a].empty else {}
        s_b = df_search[df_search["brand_id"] == brand_b].iloc[0] if not df_search[df_search["brand_id"] == brand_b].empty else {}

        return {
            "brand_a": {
                "id": brand_a,
                "name": data_a["brand_name"],
                "styles": int(data_a["active_product_count"]),
                "skus": int(data_a["active_sku_count"]),
                "variant_density": float(data_a["variant_density"]),
                "median_price": float(data_a["price_median_inr"]),
                "ppi": float(data_a["price_positioning_index"]),
                "discount_ratio": float(data_a["discounted_catalog_ratio"]),
                "median_discount_depth": float(data_a["median_discount_depth_pct"]) if pd.notna(data_a["median_discount_depth_pct"]) else None,
                "tranco_rank": int(data_a["tranco_global_rank"]) if pd.notna(data_a["tranco_global_rank"]) else None,
                "mean_rsi": float(s_a.get("mean_rsi", 0.0)) if pd.notna(s_a.get("mean_rsi")) else None,
                "avg_cohort_share": float(s_a.get("avg_cohort_share", 0.0)) if pd.notna(s_a.get("avg_cohort_share")) else None
            },
            "brand_b": {
                "id": brand_b,
                "name": data_b["brand_name"],
                "styles": int(data_b["active_product_count"]),
                "skus": int(data_b["active_sku_count"]),
                "variant_density": float(data_b["variant_density"]),
                "median_price": float(data_b["price_median_inr"]),
                "ppi": float(data_b["price_positioning_index"]),
                "discount_ratio": float(data_b["discounted_catalog_ratio"]),
                "median_discount_depth": float(data_b["median_discount_depth_pct"]) if pd.notna(data_b["median_discount_depth_pct"]) else None,
                "tranco_rank": int(data_b["tranco_global_rank"]) if pd.notna(data_b["tranco_global_rank"]) else None,
                "mean_rsi": float(s_b.get("mean_rsi", 0.0)) if pd.notna(s_b.get("mean_rsi")) else None,
                "avg_cohort_share": float(s_b.get("avg_cohort_share", 0.0)) if pd.notna(s_b.get("avg_cohort_share")) else None
            },
            "cohort_benchmarks": benchmarks
        }

    def compare_assortment(self, target_brand: str, comparison_brands: List[str], snapshot_date: str = "2026-09-29") -> Dict[str, Any]:
        """Compares style breadth, SKU depth, and variant density across brands."""
        df_feat = load_brand_features(self.db_path, snapshot_date)
        benchmarks = compute_cohort_benchmarks(df_feat)

        target_row = df_feat[df_feat["brand_id"] == target_brand]
        if target_row.empty:
            return {"error": f"Target brand '{target_brand}' not found."}

        target_data = target_row.iloc[0]
        comparisons = []
        for c_id in comparison_brands:
            c_row = df_feat[df_feat["brand_id"] == c_id]
            if not c_row.empty:
                c_data = c_row.iloc[0]
                comparisons.append({
                    "brand_id": c_id,
                    "brand_name": c_data["brand_name"],
                    "styles": int(c_data["active_product_count"]),
                    "skus": int(c_data["active_sku_count"]),
                    "variant_density": float(c_data["variant_density"]),
                    "style_diff": int(target_data["active_product_count"] - c_data["active_product_count"]),
                    "sku_diff": int(target_data["active_sku_count"] - c_data["active_sku_count"])
                })

        return {
            "target": {
                "id": target_brand,
                "name": target_data["brand_name"],
                "styles": int(target_data["active_product_count"]),
                "skus": int(target_data["active_sku_count"]),
                "variant_density": float(target_data["variant_density"]),
                "cohort_styles_median": benchmarks.get("median_products", 457.5),
                "cohort_skus_median": benchmarks.get("median_skus", 2220.5)
            },
            "comparisons": comparisons
        }

    def compare_pricing(self, target_brand: str, comparison_brands: List[str], snapshot_date: str = "2026-09-29") -> Dict[str, Any]:
        """Compares listed median prices, price IQR, and Price Positioning Index."""
        df_feat = load_brand_features(self.db_path, snapshot_date)
        benchmarks = compute_cohort_benchmarks(df_feat)

        target_row = df_feat[df_feat["brand_id"] == target_brand]
        if target_row.empty:
            return {"error": f"Target brand '{target_brand}' not found."}

        target_data = target_row.iloc[0]
        comparisons = []
        for c_id in comparison_brands:
            c_row = df_feat[df_feat["brand_id"] == c_id]
            if not c_row.empty:
                c_data = c_row.iloc[0]
                comparisons.append({
                    "brand_id": c_id,
                    "brand_name": c_data["brand_name"],
                    "median_price": float(c_data["price_median_inr"]),
                    "price_iqr": float(c_data["price_iqr_inr"]),
                    "ppi": float(c_data["price_positioning_index"]),
                    "price_diff": float(target_data["price_median_inr"] - c_data["price_median_inr"])
                })

        return {
            "target": {
                "id": target_brand,
                "name": target_data["brand_name"],
                "median_price": float(target_data["price_median_inr"]),
                "price_iqr": float(target_data["price_iqr_inr"]),
                "ppi": float(target_data["price_positioning_index"]),
                "cohort_median_price": benchmarks.get("median_price_inr", 1899.0)
            },
            "comparisons": comparisons
        }

    def compare_discounting(self, target_brand: str, comparison_brands: List[str], snapshot_date: str = "2026-09-29") -> Dict[str, Any]:
        """Compares promotional penetration and median markdown depth."""
        df_feat = load_brand_features(self.db_path, snapshot_date)
        benchmarks = compute_cohort_benchmarks(df_feat)

        target_row = df_feat[df_feat["brand_id"] == target_brand]
        if target_row.empty:
            return {"error": f"Target brand '{target_brand}' not found."}

        target_data = target_row.iloc[0]
        comparisons = []
        for c_id in comparison_brands:
            c_row = df_feat[df_feat["brand_id"] == c_id]
            if not c_row.empty:
                c_data = c_row.iloc[0]
                comparisons.append({
                    "brand_id": c_id,
                    "brand_name": c_data["brand_name"],
                    "discount_ratio": float(c_data["discounted_catalog_ratio"]),
                    "median_discount_depth": float(c_data["median_discount_depth_pct"]) if pd.notna(c_data["median_discount_depth_pct"]) else None
                })

        return {
            "target": {
                "id": target_brand,
                "name": target_data["brand_name"],
                "discount_ratio": float(target_data["discounted_catalog_ratio"]),
                "median_discount_depth": float(target_data["median_discount_depth_pct"]) if pd.notna(target_data["median_discount_depth_pct"]) else None,
                "cohort_median_ratio": benchmarks.get("median_discount_ratio", 95.86),
                "cohort_median_depth": benchmarks.get("median_discount_depth", 30.95)
            },
            "comparisons": comparisons
        }

    def get_search_trend(self, brand_id: str) -> Dict[str, Any]:
        """Returns 53-week search trend statistics and trajectories for a specific brand."""
        df_search = load_search_summary_stats(self.db_path)
        row = df_search[df_search["brand_id"] == brand_id]
        if row.empty:
            return {"error": f"Brand '{brand_id}' not found in search data."}

        data = row.iloc[0]
        return {
            "brand_id": brand_id,
            "brand_name": EntityResolver.get_canonical_name(brand_id),
            "total_weeks": int(data["total_weeks"]),
            "measurable_weeks": int(data["measurable_weeks"]),
            "low_volume_weeks": int(data["low_volume_weeks"]),
            "mean_rsi": float(data["mean_rsi"]) if pd.notna(data["mean_rsi"]) else None,
            "median_rsi": float(data["median_rsi"]) if pd.notna(data["median_rsi"]) else None,
            "min_rsi": int(data["min_rsi"]) if pd.notna(data["min_rsi"]) else None,
            "max_rsi": int(data["max_rsi"]) if pd.notna(data["max_rsi"]) else None,
            "avg_cohort_share": float(data["avg_cohort_share"]) if pd.notna(data["avg_cohort_share"]) else None,
            "latest_comparable_rsi": int(data["latest_comparable_rsi"]) if pd.notna(data.get("latest_comparable_rsi")) else None
        }

    def compare_search_attention(self, target_brand: str, comparison_brands: List[str]) -> Dict[str, Any]:
        """Compares search attention metrics across cohort brands."""
        df_search = load_search_summary_stats(self.db_path)
        target_info = self.get_search_trend(target_brand)
        
        comparisons = []
        for c_id in comparison_brands:
            c_info = self.get_search_trend(c_id)
            if "error" not in c_info:
                comparisons.append(c_info)

        return {
            "target": target_info,
            "comparisons": comparisons
        }

    def get_recent_changes(self, min_abs_delta: int = 5) -> List[Dict[str, Any]]:
        """Returns observed search spikes (|Δ| ≥ 5) from the 53-week dataset."""
        df_spikes = load_search_spikes(self.db_path, min_abs_delta=min_abs_delta)
        results = []
        for _, row in df_spikes.iterrows():
            results.append({
                "brand_id": row["brand_id"],
                "brand_name": EntityResolver.get_canonical_name(row["brand_id"]),
                "week_start": row["week_str"],
                "rsi_change": int(row["rsi_change"]),
                "prev_rsi": float(row["prev_rsi"]),
                "current_rsi": float(row["current_rsi"])
            })
        return results

    def get_brand_differences(self, target_brand: str, comparison_brands: List[str], snapshot_date: str = "2026-09-29") -> Dict[str, Any]:
        """
        Identifies key observable dimensions where target brand differs from comparison brands.
        Descriptive differences only; zero causal claims.
        """
        df_feat = load_brand_features(self.db_path, snapshot_date)
        df_search = load_search_summary_stats(self.db_path)
        benchmarks = compute_cohort_benchmarks(df_feat)

        target_row = df_feat[df_feat["brand_id"] == target_brand]
        if target_row.empty:
            return {"error": f"Target brand '{target_brand}' not found."}

        t_data = target_row.iloc[0]
        t_search = df_search[df_search["brand_id"] == target_brand].iloc[0] if not df_search[df_search["brand_id"] == target_brand].empty else {}

        diffs = []
        # 1. Breadth
        c_med_prod = benchmarks.get("median_products", 457.5)
        prod_val = t_data["active_product_count"]
        prod_diff_pct = ((prod_val - c_med_prod) / c_med_prod * 100.0) if c_med_prod else 0
        diffs.append({
            "dimension": "Catalog Breadth",
            "metric": "Active Product Styles",
            "brand_value": int(prod_val),
            "cohort_median": c_med_prod,
            "status": "above" if prod_val > c_med_prod else "below",
            "diff_pct": round(prod_diff_pct, 1)
        })

        # 2. Variant Density
        c_med_dens = benchmarks.get("median_variant_density", 5.77)
        dens_val = t_data["variant_density"]
        dens_diff_pct = ((dens_val - c_med_dens) / c_med_dens * 100.0) if c_med_dens else 0
        diffs.append({
            "dimension": "Variant Density",
            "metric": "SKUs per Style",
            "brand_value": float(dens_val),
            "cohort_median": c_med_dens,
            "status": "above" if dens_val > c_med_dens else "below",
            "diff_pct": round(dens_diff_pct, 1)
        })

        # 3. Pricing
        c_med_price = benchmarks.get("median_price_inr", 1899.0)
        price_val = t_data["price_median_inr"]
        price_diff = price_val - c_med_price
        diffs.append({
            "dimension": "Pricing Architecture",
            "metric": "Median Listed Price (INR)",
            "brand_value": float(price_val),
            "cohort_median": c_med_price,
            "status": "above" if price_val > c_med_price else "below",
            "diff_abs": round(price_diff, 0),
            "ppi": float(t_data["price_positioning_index"])
        })

        # 4. Discounting
        c_med_disc = benchmarks.get("median_discount_ratio", 95.86)
        disc_val = t_data["discounted_catalog_ratio"]
        diffs.append({
            "dimension": "Promotional Penetration",
            "metric": "Discounted Catalog %",
            "brand_value": float(disc_val),
            "cohort_median": c_med_disc,
            "status": "above" if disc_val > c_med_disc else "below",
            "markdown_depth": float(t_data["median_discount_depth_pct"]) if pd.notna(t_data["median_discount_depth_pct"]) else None
        })

        # 5. Search Attention
        avg_share = float(t_search.get("avg_cohort_share", 0.0))
        diffs.append({
            "dimension": "Search Attention",
            "metric": "Avg Cohort Search Share (%)",
            "brand_value": avg_share,
            "cohort_benchmark": 25.0, # Equal 4-way share
            "status": "above" if avg_share > 25.0 else "below"
        })

        return {
            "target_brand": {
                "id": target_brand,
                "name": t_data["brand_name"]
            },
            "differences": diffs
        }

    def get_brand_gaps(self, target_brand: str, comparison_brands: List[str], snapshot_date: str = "2026-09-29") -> Dict[str, Any]:
        """
        Answers 'What is my brand missing?' strictly by identifying observable characteristics
        present in comparison brands but less represented in target brand.
        NO prescriptive advice or recommendations.
        """
        df_feat = load_brand_features(self.db_path, snapshot_date)
        df_cat = load_category_mix(self.db_path, snapshot_date)

        target_row = df_feat[df_feat["brand_id"] == target_brand]
        if target_row.empty:
            return {"error": f"Target brand '{target_brand}' not found."}

        t_data = target_row.iloc[0]
        t_categories = set(df_cat[df_cat["brand_id"] == target_brand]["category_std"].unique())

        # Find categories present in peers but missing or low in target
        peer_cat_df = df_cat[df_cat["brand_id"].isin(comparison_brands)]
        peer_categories = set(peer_cat_df["category_std"].unique())
        missing_categories = list(peer_categories - t_categories)

        # Assortment breadth comparison
        max_peer_styles = int(df_feat[df_feat["brand_id"].isin(comparison_brands)]["active_product_count"].max())
        style_gap = max(0, max_peer_styles - int(t_data["active_product_count"]))

        # Sizing / Variant density comparison
        max_peer_density = float(df_feat[df_feat["brand_id"].isin(comparison_brands)]["variant_density"].max())
        density_diff = round(max_peer_density - float(t_data["variant_density"]), 2)

        return {
            "target_brand": {
                "id": target_brand,
                "name": t_data["brand_name"],
                "styles": int(t_data["active_product_count"]),
                "variant_density": float(t_data["variant_density"])
            },
            "missing_categories": missing_categories,
            "style_breadth_difference": style_gap,
            "max_peer_styles": max_peer_styles,
            "variant_density_difference": density_diff if density_diff > 0 else 0.0
        }

    def get_category_mix(self, brand_id: str, snapshot_date: str = "2026-09-29") -> Dict[str, Any]:
        """Returns standardized category distribution for a brand."""
        df_cat = load_category_mix(self.db_path, snapshot_date)
        b_df = df_cat[df_cat["brand_id"] == brand_id]
        if b_df.empty:
            return {"error": f"No category data found for brand '{brand_id}'."}

        cats = []
        for _, row in b_df.iterrows():
            cats.append({
                "category": row["category_std"],
                "sku_count": int(row["category_sku_count"]),
                "share_pct": float(row["category_share_pct"])
            })

        has_limitation = (brand_id == "elevarsports")
        return {
            "brand_id": brand_id,
            "brand_name": EntityResolver.get_canonical_name(brand_id),
            "categories": cats,
            "has_limitation": has_limitation,
            "limitation_note": "90.93% of SKUs map to Casual/Other due to non-specific storefront product_type tags." if has_limitation else None
        }

    def get_metric_definition(self, metric_key: str) -> Optional[Dict[str, str]]:
        """Returns official methodology documentation for a given metric."""
        for key, meta in METRIC_DEFINITIONS.items():
            if key in metric_key.lower() or metric_key.lower() in key:
                return meta
        return None

    def get_data_availability(self) -> Dict[str, Any]:
        """Reports verified data sources, coverage, and snapshot dates."""
        conn = get_db_connection(self.db_path)
        try:
            brand_count = conn.execute("SELECT COUNT(*) FROM dim_brand WHERE is_active = TRUE").fetchone()[0]
            catalog_skus = conn.execute("SELECT COUNT(*) FROM fact_catalog_snapshot").fetchone()[0]
            search_weeks = conn.execute("SELECT COUNT(DISTINCT week_start_date) FROM fact_search_demand").fetchone()[0]
            return {
                "active_brands": list(CANONICAL_BRANDS.values()),
                "total_brands": brand_count,
                "catalog_snapshot_date": "2026-09-29",
                "total_skus": catalog_skus,
                "search_weeks": search_weeks,
                "search_date_range": "2025-09-28 to 2026-09-27",
                "search_geography": "India (Web Search)",
                "domain_rank_source": "Tranco Top 1M (2026-09-28)"
            }
        finally:
            conn.close()
