import os
import duckdb
import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional, Tuple

DB_PATH_DEFAULT = "data/processed/brandsignal.duckdb"

def get_db_connection(db_path: str = DB_PATH_DEFAULT) -> duckdb.DuckDBPyConnection:
    """Returns a read-only DuckDB connection."""
    if not os.path.exists(db_path):
        raise FileNotFoundError(f"Database file not found at: {db_path}")
    return duckdb.connect(db_path, read_only=True)

def load_snapshot_dates(db_path: str = DB_PATH_DEFAULT) -> List[str]:
    """Loads distinct catalog snapshot dates in descending order."""
    conn = get_db_connection(db_path)
    try:
        df = conn.execute("""
            SELECT DISTINCT snapshot_date 
            FROM fact_brand_snapshot_features 
            ORDER BY snapshot_date DESC
        """).df()
        return [pd.to_datetime(d).strftime("%Y-%m-%d") for d in df["snapshot_date"].tolist()]
    finally:
        conn.close()

def load_brand_features(db_path: str = DB_PATH_DEFAULT, snapshot_date: str = "2026-09-29") -> pd.DataFrame:
    """Loads analytical brand features for a specific snapshot date."""
    conn = get_db_connection(db_path)
    try:
        query = f"""
            SELECT 
                snapshot_date,
                brand_id,
                brand_name,
                active_product_count,
                active_sku_count,
                variant_density,
                price_min_inr,
                price_p25_inr,
                price_median_inr,
                price_p75_inr,
                price_max_inr,
                price_iqr_inr,
                price_positioning_index,
                discounted_sku_count,
                discounted_catalog_ratio,
                median_discount_depth_pct,
                tranco_global_rank,
                tranco_status,
                latest_relative_search_interest,
                latest_cohort_search_share
            FROM fact_brand_snapshot_features
            WHERE snapshot_date = '{snapshot_date}'
            ORDER BY brand_id
        """
        df = conn.execute(query).df()
        return df
    finally:
        conn.close()

def compute_cohort_benchmarks(df_features: pd.DataFrame) -> Dict[str, Any]:
    """
    Computes cohort totals and cohort medians across the 4 brands.
    """
    if df_features.empty:
        return {}

    return {
        "total_active_products": int(df_features["active_product_count"].sum()),
        "total_active_skus": int(df_features["active_sku_count"].sum()),
        "median_products": float(np.nanmedian(df_features["active_product_count"])),
        "median_skus": float(np.nanmedian(df_features["active_sku_count"])),
        "median_variant_density": float(np.nanmedian(df_features["variant_density"])),
        "median_price_inr": float(np.nanmedian(df_features["price_median_inr"])),
        "median_price_iqr_inr": float(np.nanmedian(df_features["price_iqr_inr"])),
        "median_discount_ratio": float(np.nanmedian(df_features["discounted_catalog_ratio"])),
        "median_discount_depth": float(np.nanmedian(df_features["median_discount_depth_pct"].dropna()))
    }

def load_category_mix(db_path: str = DB_PATH_DEFAULT, snapshot_date: str = "2026-09-29") -> pd.DataFrame:
    """Loads standardized category mix by brand."""
    conn = get_db_connection(db_path)
    try:
        query = f"""
            SELECT 
                snapshot_date,
                brand_id,
                category_std,
                category_sku_count,
                category_share_pct
            FROM fact_brand_category_mix
            WHERE snapshot_date = '{snapshot_date}'
            ORDER BY brand_id, category_sku_count DESC
        """
        return conn.execute(query).df()
    finally:
        conn.close()

def load_price_quantiles(db_path: str = DB_PATH_DEFAULT, snapshot_date: str = "2026-09-29") -> pd.DataFrame:
    """Loads pre-computed price quantiles and ranges for distribution charts."""
    conn = get_db_connection(db_path)
    try:
        query = f"""
            SELECT 
                brand_id,
                COUNT(*) AS total_skus,
                ROUND(MIN(selling_price_inr), 2) AS price_min,
                ROUND(QUANTILE_CONT(selling_price_inr, 0.25), 2) AS price_p25,
                ROUND(MEDIAN(selling_price_inr), 2) AS price_median,
                ROUND(QUANTILE_CONT(selling_price_inr, 0.75), 2) AS price_p75,
                ROUND(MAX(selling_price_inr), 2) AS price_max,
                ROUND(QUANTILE_CONT(selling_price_inr, 0.75) - QUANTILE_CONT(selling_price_inr, 0.25), 2) AS price_iqr
            FROM fact_catalog_snapshot
            WHERE snapshot_date = '{snapshot_date}'
            GROUP BY brand_id
            ORDER BY price_median DESC
        """
        return conn.execute(query).df()
    finally:
        conn.close()

def load_search_demand_series(db_path: str = DB_PATH_DEFAULT) -> pd.DataFrame:
    """
    Loads full 53-week Google Trends search demand series.
    Preserves <1 low volume as NULL in relative_search_interest without fabricating 0.
    """
    conn = get_db_connection(db_path)
    try:
        query = """
            SELECT 
                week_start_date,
                brand_id,
                search_term,
                relative_search_interest,
                relative_search_interest_raw,
                is_low_volume,
                cohort_relative_search_share
            FROM fact_search_demand
            ORDER BY week_start_date, brand_id
        """
        df = conn.execute(query).df()
        # Convert week_start_date to string YYYY-MM-DD
        df["week_str"] = pd.to_datetime(df["week_start_date"]).dt.strftime("%Y-%m-%d")
        return df
    finally:
        conn.close()

def load_search_summary_stats(db_path: str = DB_PATH_DEFAULT) -> pd.DataFrame:
    """Loads summary search statistics across all 53 weeks."""
    conn = get_db_connection(db_path)
    try:
        query = """
            SELECT 
                brand_id,
                COUNT(*) AS total_weeks,
                COUNT(relative_search_interest) AS measurable_weeks,
                SUM(CASE WHEN is_low_volume THEN 1 ELSE 0 END) AS low_volume_weeks,
                ROUND(AVG(relative_search_interest), 2) AS mean_rsi,
                ROUND(MEDIAN(relative_search_interest), 2) AS median_rsi,
                MIN(relative_search_interest) AS min_rsi,
                MAX(relative_search_interest) AS max_rsi,
                ROUND(AVG(cohort_relative_search_share), 2) AS avg_cohort_share,
                ROUND(MAX(cohort_relative_search_share), 2) AS max_cohort_share
            FROM fact_search_demand
            GROUP BY brand_id
            ORDER BY brand_id
        """
        df = conn.execute(query).df()

        # Add latest comparable week (2026-09-06 where all 4 brands have numeric values)
        latest_comp = conn.execute("""
            SELECT 
                brand_id,
                relative_search_interest AS latest_comparable_rsi,
                cohort_relative_search_share AS latest_comparable_share
            FROM fact_search_demand
            WHERE week_start_date = '2026-09-06'
        """).df()
        df = df.merge(latest_comp, on="brand_id", how="left")
        return df
    finally:
        conn.close()

def load_search_spikes(db_path: str = DB_PATH_DEFAULT, min_abs_delta: int = 5) -> pd.DataFrame:
    """
    Extracts arithmetically observable week-over-week spikes.
    Strictly non-causal; does not attribute marketing or external causes.
    """
    conn = get_db_connection(db_path)
    try:
        query = f"""
            WITH lag_cte AS (
                SELECT 
                    brand_id,
                    week_start_date,
                    relative_search_interest,
                    LAG(relative_search_interest) OVER (PARTITION BY brand_id ORDER BY week_start_date) AS prev_rsi
                FROM fact_search_demand
            )
            SELECT 
                brand_id,
                week_start_date,
                (relative_search_interest - prev_rsi) AS rsi_change,
                prev_rsi,
                relative_search_interest AS current_rsi
            FROM lag_cte
            WHERE prev_rsi IS NOT NULL 
              AND relative_search_interest IS NOT NULL
              AND ABS(relative_search_interest - prev_rsi) >= {min_abs_delta}
            ORDER BY ABS(relative_search_interest - prev_rsi) DESC
        """
        df = conn.execute(query).df()
        df["week_str"] = pd.to_datetime(df["week_start_date"]).dt.strftime("%Y-%m-%d")
        return df
    finally:
        conn.close()

def format_metric_value(val: Any, metric_type: str = "number", null_label: str = "N/A") -> str:
    """Formats numeric metrics cleanly with designated NULL representations."""
    if val is None or pd.isna(val):
        return null_label
    try:
        if metric_type == "currency":
            return f"₹{float(val):,.2f}".rstrip("0").rstrip(".") if float(val) % 1 == 0 else f"₹{float(val):,.2f}"
        elif metric_type == "currency_int":
            return f"₹{int(round(float(val))):,}"
        elif metric_type == "percent":
            return f"{float(val):.1f}%"
        elif metric_type == "index":
            return f"{float(val):.2f}"
        elif metric_type == "integer":
            return f"{int(round(float(val))):,}"
        elif metric_type == "decimal":
            return f"{float(val):.2f}"
        return str(val)
    except (ValueError, TypeError):
        return null_label
