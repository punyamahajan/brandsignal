import duckdb
import pandas as pd
import numpy as np
from typing import Dict, Any, Tuple, Optional, List
from scipy.stats import pearsonr, spearmanr

class CrossSignalAnalyzer:
    """
    Analyzes descriptive associations between storefront catalog/pricing structures
    and 12-month Google Trends search demand.
    
    METHODOLOGICAL WARNING:
    Cross-signal correlations are not used as BrandSignal decision metrics because
    the comparison contains only four brands and combines a single cross-sectional
    storefront snapshot with longitudinal Google Trends data. Correlation coefficients
    at this sample size are unstable and should not be interpreted as evidence of a
    meaningful market relationship.
    
    IMPORTANT METHODOLOGICAL GUARDRAILS:
    - Single point-in-time catalog snapshot (2026-09-29) vs longitudinal search demand (53 weeks).
    - Descriptive associations across N=4 brands only; strictly non-causal.
    - Zero inferential claims regarding causality, revenue impact, or promotional effectiveness.
    """

    def __init__(self, db_path: str = "data/processed/brandsignal.duckdb"):
        self.db_path = db_path

    def get_connection(self):
        return duckdb.connect(self.db_path, read_only=True)

    def get_cross_signal_dataset(self, snapshot_date: str = "2026-09-29") -> pd.DataFrame:
        """
        Merges catalog features, search demand summary statistics, and Tranco domain ranks.
        """
        conn = self.get_connection()
        query = f"""
            WITH search_summary AS (
                SELECT 
                    brand_id,
                    ROUND(AVG(relative_search_interest), 2) AS mean_rsi,
                    ROUND(MEDIAN(relative_search_interest), 2) AS median_rsi,
                    ROUND(AVG(cohort_relative_search_share), 2) AS avg_cohort_share
                FROM fact_search_demand
                GROUP BY brand_id
            )
            SELECT 
                f.brand_id,
                f.brand_name,
                f.active_product_count,
                f.active_sku_count,
                f.variant_density,
                f.price_median_inr,
                f.price_iqr_inr,
                f.price_positioning_index,
                f.discounted_catalog_ratio,
                f.median_discount_depth_pct,
                f.tranco_global_rank,
                f.tranco_status,
                s.mean_rsi,
                s.median_rsi,
                s.avg_cohort_share
            FROM fact_brand_snapshot_features f
            JOIN search_summary s ON f.brand_id = s.brand_id
            WHERE f.snapshot_date = '{snapshot_date}'
            ORDER BY s.mean_rsi DESC
        """
        df = conn.execute(query).df()
        conn.close()
        return df

    def compute_descriptive_associations(self, df: Optional[pd.DataFrame] = None) -> pd.DataFrame:
        """
        Computes Pearson and Spearman rank correlation coefficients between
        storefront catalog/pricing features and mean relative search interest.
        
        Note: These are descriptive correlations across N=4 brands and carry no causal implication.
        """
        if df is None:
            df = self.get_cross_signal_dataset()

        features = [
            ("active_product_count", "Assortment Product Breadth"),
            ("active_sku_count", "Assortment SKU Depth"),
            ("variant_density", "Variant Density"),
            ("price_median_inr", "Median Selling Price (INR)"),
            ("price_iqr_inr", "Price Dispersion (IQR INR)"),
            ("discounted_catalog_ratio", "Discounted Catalog Ratio (%)"),
            ("median_discount_depth_pct", "Median Discount Depth (%)")
        ]

        target = "mean_rsi"
        results = []

        for col, label in features:
            valid_mask = df[col].notna() & df[target].notna()
            x = df.loc[valid_mask, col].astype(float)
            y = df.loc[valid_mask, target].astype(float)

            if len(x) >= 3 and np.std(x) > 0 and np.std(y) > 0:
                p_corr, p_val = pearsonr(x, y)
                s_corr, s_val = spearmanr(x, y)
                results.append({
                    "feature": col,
                    "feature_label": label,
                    "pearson_r": round(float(p_corr), 2),
                    "pearson_p_value": round(float(p_val), 4),
                    "spearman_rho": round(float(s_corr), 2),
                    "spearman_p_value": round(float(s_val), 4),
                    "sample_size": len(x)
                })
            else:
                results.append({
                    "feature": col,
                    "feature_label": label,
                    "pearson_r": None,
                    "pearson_p_value": None,
                    "spearman_rho": None,
                    "spearman_p_value": None,
                    "sample_size": len(x)
                })

        return pd.DataFrame(results)


def main():
    analyzer = CrossSignalAnalyzer()
    print("==================================================")
    print("ANALYSIS 7: CROSS-SIGNAL BENCHMARKING TABLE")
    print("==================================================")
    df_cross = analyzer.get_cross_signal_dataset()
    print(df_cross.to_string(index=False))

    print("\n==================================================")
    print("DESCRIPTIVE ASSOCIATIONS (N=4 BRANDS)")
    print("==================================================")
    df_corr = analyzer.compute_descriptive_associations(df_cross)
    print(df_corr.to_string(index=False))

if __name__ == "__main__":
    main()
