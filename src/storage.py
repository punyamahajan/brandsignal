import os
import duckdb
import pandas as pd
from typing import Dict, Any, Optional

class DatabaseManager:
    """Manages the local DuckDB analytical database and Parquet exports for BrandSignal."""

    def __init__(self, db_path: str = "data/processed/brandsignal.duckdb", base_dir: str = "."):
        self.base_dir = base_dir
        self.db_path = os.path.join(base_dir, db_path)
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self.conn = duckdb.connect(self.db_path)

    def init_schemas(
        self,
        sql_raw_path: str = "sql/01_schema_raw.sql",
        sql_proc_path: str = "sql/02_schema_processed.sql",
        sql_features_path: str = "sql/04_analytical_features.sql"
    ) -> None:
        """Executes DDL and view statements to ensure all raw, processed, and analytical objects exist."""
        raw_full_path = os.path.join(self.base_dir, sql_raw_path)
        proc_full_path = os.path.join(self.base_dir, sql_proc_path)
        feat_full_path = os.path.join(self.base_dir, sql_features_path)

        with open(raw_full_path, "r", encoding="utf-8") as f:
            self.conn.execute(f.read())

        with open(proc_full_path, "r", encoding="utf-8") as f:
            self.conn.execute(f.read())

        if os.path.exists(feat_full_path):
            with open(feat_full_path, "r", encoding="utf-8") as f:
                self.conn.execute(f.read())

    def seed_dim_brand(self, brands_config: Dict[str, Any], category: str = "D2C Footwear", geo: str = "IN", currency: str = "INR") -> None:
        """Seeds or updates the brand dimension table from configuration."""
        rows = []
        for brand_key, cfg in brands_config.items():
            rows.append({
                "brand_id": cfg["brand_id"],
                "brand_name": cfg["name"],
                "storefront_domain": cfg["domain"],
                "storefront_endpoint": cfg["endpoint"],
                "category": category,
                "geography": geo,
                "currency": currency,
                "is_active": cfg.get("is_active", True)
            })
        df_brands = pd.DataFrame(rows)
        # Register and upsert
        self.conn.register("df_brands_temp", df_brands)
        self.conn.execute("""
            INSERT OR REPLACE INTO dim_brand 
            SELECT * FROM df_brands_temp
        """)
        self.conn.unregister("df_brands_temp")

    def insert_audit_log(self, entry: Dict[str, Any]) -> None:
        """Inserts a structured operational telemetry record into audit_ingestion_log."""
        df_entry = pd.DataFrame([entry])
        self.conn.register("df_entry_temp", df_entry)
        self.conn.execute("""
            INSERT INTO audit_ingestion_log 
            SELECT * FROM df_entry_temp
        """)
        self.conn.unregister("df_entry_temp")

    def upsert_catalog_snapshot(self, df_catalog: pd.DataFrame) -> int:
        """Upserts a cleaned catalog snapshot into fact_catalog_snapshot."""
        if df_catalog.empty:
            return 0
        self.conn.register("df_cat_temp", df_catalog)
        self.conn.execute("""
            INSERT OR REPLACE INTO fact_catalog_snapshot
            SELECT * FROM df_cat_temp
        """)
        self.conn.unregister("df_cat_temp")
        return len(df_catalog)

    def upsert_domain_popularity(self, df_tranco: pd.DataFrame) -> int:
        """Upserts Tranco domain popularity observations."""
        if df_tranco.empty:
            return 0
        self.conn.register("df_tranco_temp", df_tranco)
        self.conn.execute("""
            INSERT OR REPLACE INTO fact_domain_popularity
            SELECT * FROM df_tranco_temp
        """)
        self.conn.unregister("df_tranco_temp")
        return len(df_tranco)

    def upsert_search_demand(self, df_search: pd.DataFrame) -> int:
        """Upserts Google Trends search demand records."""
        if df_search.empty:
            return 0
        self.conn.register("df_search_temp", df_search)
        self.conn.execute("""
            INSERT OR REPLACE INTO fact_search_demand (
                week_start_date,
                brand_id,
                geography,
                search_term,
                relative_search_interest_raw,
                relative_search_interest,
                is_low_volume,
                cohort_relative_search_share,
                collection_timestamp,
                raw_file_ref
            )
            SELECT 
                week_start_date,
                brand_id,
                geography,
                search_term,
                relative_search_interest_raw,
                relative_search_interest,
                is_low_volume,
                cohort_relative_search_share,
                collection_timestamp,
                raw_file_ref
            FROM df_search_temp
        """)
        self.conn.unregister("df_search_temp")
        return len(df_search)

    def upsert_brand_snapshot_features(self, df_features: pd.DataFrame) -> int:
        """Upserts analytical brand snapshot features into fact_brand_snapshot_features."""
        if df_features.empty:
            return 0
        self.conn.register("df_feat_temp", df_features)
        self.conn.execute("""
            INSERT OR REPLACE INTO fact_brand_snapshot_features (
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
                latest_cohort_search_share,
                new_sku_velocity_30d,
                created_at
            )
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
                latest_cohort_search_share,
                new_sku_velocity_30d,
                created_at
            FROM df_feat_temp
        """)
        self.conn.unregister("df_feat_temp")
        return len(df_features)

    def upsert_brand_category_mix(self, df_category_mix: pd.DataFrame) -> int:
        """Upserts category breakdown observations into fact_brand_category_mix."""
        if df_category_mix.empty:
            return 0
        self.conn.register("df_cat_mix_temp", df_category_mix)
        self.conn.execute("""
            INSERT OR REPLACE INTO fact_brand_category_mix (
                snapshot_date,
                brand_id,
                category_std,
                category_sku_count,
                category_share_pct,
                created_at
            )
            SELECT 
                snapshot_date,
                brand_id,
                category_std,
                category_sku_count,
                category_share_pct,
                created_at
            FROM df_cat_mix_temp
        """)
        self.conn.unregister("df_cat_mix_temp")
        return len(df_category_mix)

    def export_to_parquet(self, table_name: str, output_parquet_path: str) -> None:
        """Exports a table from DuckDB to an optimized Parquet file."""
        full_output_path = os.path.join(self.base_dir, output_parquet_path)
        os.makedirs(os.path.dirname(full_output_path), exist_ok=True)
        # Use DuckDB native parquet export
        full_output_path_sql = full_output_path.replace("\\", "/")
        self.conn.execute(f"COPY {table_name} TO '{full_output_path_sql}' (FORMAT PARQUET)")

    def close(self) -> None:
        self.conn.close()
