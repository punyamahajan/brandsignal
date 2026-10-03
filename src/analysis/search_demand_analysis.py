import duckdb
import pandas as pd
import numpy as np
from typing import Dict, Any, List

class SearchDemandAnalyzer:
    """
    Analyzes Google Trends relative search demand (RSI) and cohort-relative search share
    over the 53-week observation period (2025-09-28 to 2026-09-27).
    
    Database: data/processed/brandsignal.duckdb
    Table: fact_search_demand
    """

    def __init__(self, db_path: str = "data/processed/brandsignal.duckdb"):
        self.db_path = db_path

    def get_connection(self):
        return duckdb.connect(self.db_path, read_only=True)

    def get_search_summary_stats(self) -> pd.DataFrame:
        """
        Calculates descriptive summary statistics for each brand over the 53-week horizon.
        Explicitly distinguishes measurable weeks from <1 unquantified weeks.
        """
        conn = self.get_connection()
        query = """
            SELECT 
                brand_id,
                COUNT(*) AS total_weeks,
                COUNT(relative_search_interest) AS measurable_weeks,
                SUM(CASE WHEN is_low_volume THEN 1 ELSE 0 END) AS low_volume_weeks,
                ROUND(AVG(relative_search_interest), 2) AS mean_rsi,
                ROUND(MEDIAN(relative_search_interest), 2) AS median_rsi,
                ROUND(STDDEV(relative_search_interest), 2) AS std_dev_rsi,
                ROUND(QUANTILE_CONT(relative_search_interest, 0.75) - QUANTILE_CONT(relative_search_interest, 0.25), 2) AS iqr_rsi,
                MIN(relative_search_interest) AS min_rsi,
                MAX(relative_search_interest) AS max_rsi,
                ROUND(AVG(cohort_relative_search_share), 2) AS avg_cohort_search_share,
                ROUND(MAX(cohort_relative_search_share), 2) AS max_cohort_search_share
            FROM fact_search_demand
            GROUP BY brand_id
            ORDER BY brand_id
        """
        df = conn.execute(query).df()

        # Add latest comparable search interest (week 2026-09-06 where all 4 brands have complete data)
        latest_comp_query = """
            SELECT brand_id, relative_search_interest AS latest_comparable_rsi, cohort_relative_search_share AS latest_comparable_share
            FROM fact_search_demand
            WHERE week_start_date = '2026-09-06'
        """
        df_latest = conn.execute(latest_comp_query).df()
        conn.close()

        df = df.merge(df_latest, on="brand_id", how="left")
        return df

    def get_wow_changes(self) -> pd.DataFrame:
        """
        Calculates week-over-week changes where consecutive weekly observations are numeric.
        """
        conn = self.get_connection()
        query = """
            WITH lag_cte AS (
                SELECT 
                    brand_id,
                    week_start_date,
                    relative_search_interest,
                    is_low_volume,
                    LAG(relative_search_interest) OVER (PARTITION BY brand_id ORDER BY week_start_date) AS prev_rsi,
                    LAG(is_low_volume) OVER (PARTITION BY brand_id ORDER BY week_start_date) AS prev_is_low
                FROM fact_search_demand
            )
            SELECT 
                brand_id,
                week_start_date,
                relative_search_interest,
                prev_rsi,
                (relative_search_interest - prev_rsi) AS wow_change_rsi,
                CASE 
                    WHEN prev_rsi > 0 THEN ROUND(((relative_search_interest - prev_rsi)::DECIMAL / prev_rsi) * 100.0, 2)
                    ELSE NULL
                END AS wow_change_pct
            FROM lag_cte
            WHERE prev_rsi IS NOT NULL AND relative_search_interest IS NOT NULL
            ORDER BY brand_id, week_start_date
        """
        df = conn.execute(query).df()
        conn.close()
        return df

    def get_top_spikes_and_drops(self, top_n: int = 5) -> Dict[str, Dict[str, pd.DataFrame]]:
        """
        Identifies the top positive spikes and negative drops in RSI for each brand.
        """
        df_wow = self.get_wow_changes()
        result = {}
        for brand_id, bdf in df_wow.groupby("brand_id"):
            spikes = bdf.sort_values(by="wow_change_rsi", ascending=False).head(top_n)
            drops = bdf.sort_values(by="wow_change_rsi", ascending=True).head(top_n)
            result[brand_id] = {
                "spikes": spikes[["week_start_date", "prev_rsi", "relative_search_interest", "wow_change_rsi", "wow_change_pct"]],
                "drops": drops[["week_start_date", "prev_rsi", "relative_search_interest", "wow_change_rsi", "wow_change_pct"]]
            }
        return result


def main():
    analyzer = SearchDemandAnalyzer()
    print("==================================================")
    print("ANALYSIS 5: 53-WEEK SEARCH SUMMARY STATISTICS")
    print("==================================================")
    df_summary = analyzer.get_search_summary_stats()
    print(df_summary.to_string(index=False))

    print("\n==================================================")
    print("ANALYSIS 6: TOP SPIKES & DROPS BY BRAND")
    print("==================================================")
    spikes_drops = analyzer.get_top_spikes_and_drops(top_n=3)
    for brand_id, data in spikes_drops.items():
        print(f"\n--- {brand_id.upper()} Top Spikes ---")
        print(data["spikes"].to_string(index=False))
        print(f"--- {brand_id.upper()} Top Drops ---")
        print(data["drops"].to_string(index=False))

if __name__ == "__main__":
    main()
