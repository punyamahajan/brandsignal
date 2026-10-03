import duckdb
import pandas as pd
import numpy as np
from typing import Dict, Any, Optional

class CompetitiveSnapshotAnalyzer:
    """
    Analyzes current competitive positioning, assortment structure,
    price dispersion, and promotional intensity across the four-brand cohort.
    
    Data grain: snapshot_date = '2026-09-29'
    Database: data/processed/brandsignal.duckdb
    """

    def __init__(self, db_path: str = "data/processed/brandsignal.duckdb"):
        self.db_path = db_path

    def get_connection(self):
        return duckdb.connect(self.db_path, read_only=True)

    def get_competitive_positioning_table(self, snapshot_date: str = "2026-09-29") -> pd.DataFrame:
        """
        Builds the comprehensive competitive positioning comparison table.
        Computes absolute values, cohort medians, absolute differences, and percentage differences.
        """
        conn = self.get_connection()
        query = f"""
            SELECT 
                brand_id,
                brand_name,
                active_product_count,
                active_sku_count,
                variant_density,
                price_median_inr,
                price_iqr_inr,
                price_positioning_index,
                discounted_catalog_ratio,
                median_discount_depth_pct
            FROM fact_brand_snapshot_features
            WHERE snapshot_date = '{snapshot_date}'
            ORDER BY brand_id
        """
        df = conn.execute(query).df()
        conn.close()

        if df.empty:
            return pd.DataFrame()

        metrics = [
            "active_product_count",
            "active_sku_count",
            "variant_density",
            "price_median_inr",
            "price_iqr_inr",
            "price_positioning_index",
            "discounted_catalog_ratio",
            "median_discount_depth_pct"
        ]

        # Calculate cohort median for each metric
        cohort_medians = {m: float(np.nanmedian(df[m])) for m in metrics}

        # Build comparison records
        rows = []
        for _, row in df.iterrows():
            brand_dict = {
                "brand_id": row["brand_id"],
                "brand_name": row["brand_name"],
            }
            for m in metrics:
                val = row[m]
                c_med = cohort_medians[m]
                diff = val - c_med if val is not None and not pd.isna(val) else None
                pct_diff = (diff / c_med * 100.0) if (diff is not None and c_med != 0) else None

                brand_dict[f"{m}_value"] = round(val, 2) if val is not None else None
                brand_dict[f"{m}_cohort_median"] = round(c_med, 2)
                brand_dict[f"{m}_diff"] = round(diff, 2) if diff is not None else None
                brand_dict[f"{m}_pct_diff"] = round(pct_diff, 2) if pct_diff is not None else None

            rows.append(brand_dict)

        return pd.DataFrame(rows)

    def get_assortment_category_mix(self, snapshot_date: str = "2026-09-29") -> pd.DataFrame:
        """
        Returns the standardized category mix across all active brands for a snapshot.
        """
        conn = self.get_connection()
        query = f"""
            SELECT 
                brand_id,
                category_std,
                category_sku_count,
                category_share_pct
            FROM fact_brand_category_mix
            WHERE snapshot_date = '{snapshot_date}'
            ORDER BY brand_id, category_sku_count DESC
        """
        df = conn.execute(query).df()
        conn.close()
        return df

    def get_price_distribution_summary(self, snapshot_date: str = "2026-09-29") -> pd.DataFrame:
        """
        Computes detailed price distribution percentiles and bounds for each brand.
        """
        conn = self.get_connection()
        query = f"""
            SELECT 
                brand_id,
                COUNT(*) AS total_skus,
                ROUND(MIN(selling_price_inr), 2) AS price_min_inr,
                ROUND(QUANTILE_CONT(selling_price_inr, 0.25), 2) AS price_p25_inr,
                ROUND(MEDIAN(selling_price_inr), 2) AS price_median_inr,
                ROUND(QUANTILE_CONT(selling_price_inr, 0.75), 2) AS price_p75_inr,
                ROUND(MAX(selling_price_inr), 2) AS price_max_inr,
                ROUND(QUANTILE_CONT(selling_price_inr, 0.75) - QUANTILE_CONT(selling_price_inr, 0.25), 2) AS price_iqr_inr
            FROM fact_catalog_snapshot
            WHERE snapshot_date = '{snapshot_date}'
            GROUP BY brand_id
            ORDER BY brand_id
        """
        df = conn.execute(query).df()
        conn.close()

        # Add price positioning index
        cohort_med = float(np.nanmedian(df["price_median_inr"]))
        df["cohort_median_inr"] = round(cohort_med, 2)
        df["price_positioning_index"] = round(df["price_median_inr"] / cohort_med, 2)
        return df

    def get_discount_summary(self, snapshot_date: str = "2026-09-29") -> pd.DataFrame:
        """
        Extracts discounting volume, non-discounted volume, ratio, and median depth.
        """
        conn = self.get_connection()
        query = f"""
            SELECT 
                brand_id,
                COUNT(*) AS total_skus,
                COUNT(CASE WHEN is_discounted THEN 1 END) AS discounted_sku_count,
                COUNT(CASE WHEN NOT is_discounted THEN 1 END) AS non_discounted_sku_count,
                ROUND(COUNT(CASE WHEN is_discounted THEN 1 END)::DECIMAL * 100.0 / COUNT(*), 2) AS discounted_catalog_ratio,
                ROUND(MEDIAN(CASE WHEN is_discounted THEN discount_pct END), 2) AS median_discount_depth_pct
            FROM fact_catalog_snapshot
            WHERE snapshot_date = '{snapshot_date}'
            GROUP BY brand_id
            ORDER BY brand_id
        """
        df = conn.execute(query).df()
        conn.close()
        return df


def main():
    analyzer = CompetitiveSnapshotAnalyzer()
    print("==================================================")
    print("ANALYSIS 1: CURRENT COMPETITIVE POSITIONING")
    print("==================================================")
    df_pos = analyzer.get_competitive_positioning_table()
    for _, row in df_pos.iterrows():
        print(f"\n--- {row['brand_name']} ({row['brand_id']}) ---")
        for m in ["active_product_count", "active_sku_count", "variant_density", "price_median_inr", "price_iqr_inr", "price_positioning_index", "discounted_catalog_ratio", "median_discount_depth_pct"]:
            print(f"  {m:26}: Value={row[f'{m}_value']} | CohortMed={row[f'{m}_cohort_median']} | Diff={row[f'{m}_diff']:+g} | %Diff={row[f'{m}_pct_diff']:+g}%")

    print("\n==================================================")
    print("ANALYSIS 2: CATEGORY MIX")
    print("==================================================")
    df_cat = analyzer.get_assortment_category_mix()
    print(df_cat.to_string(index=False))

    print("\n==================================================")
    print("ANALYSIS 3: PRICE STRUCTURE")
    print("==================================================")
    df_price = analyzer.get_price_distribution_summary()
    print(df_price.to_string(index=False))

    print("\n==================================================")
    print("ANALYSIS 4: DISCOUNTING STRUCTURE")
    print("==================================================")
    df_disc = analyzer.get_discount_summary()
    print(df_disc.to_string(index=False))

if __name__ == "__main__":
    main()
