import os
import yaml
from datetime import datetime, timezone
from typing import Dict, Any, Optional

from src.storage import DatabaseManager
from src.ingestion.logger import IngestionAuditLogger
from src.ingestion.storefront import StorefrontIngestor
from src.ingestion.tranco import TrancoIngestor
from src.ingestion.search import GoogleTrendsIngestor
from src.cleaning.storefront_cleaner import StorefrontCleaner
from src.cleaning.quality_checker import CatalogQualityChecker, SearchDemandQualityChecker

class BrandSignalPipeline:
    """Master orchestrator for BrandSignal V1 data ingestion, validation, and storage."""

    def __init__(self, config_path: str = "config/sources.yaml", base_dir: str = "."):
        self.base_dir = base_dir
        self.config_path = os.path.join(base_dir, config_path)
        with open(self.config_path, "r", encoding="utf-8") as f:
            self.cfg = yaml.safe_load(f)

        self.db = DatabaseManager(
            db_path=self.cfg["paths"]["duckdb_path"],
            base_dir=self.base_dir
        )
        self.audit_logger = IngestionAuditLogger(
            logs_dir=self.cfg["paths"]["logs_dir"],
            base_dir=self.base_dir
        )
        self.storefront_ingestor = StorefrontIngestor(
            user_agent=self.cfg["http_defaults"]["user_agent"],
            timeout=self.cfg["http_defaults"]["timeout_seconds"],
            politeness_delay=self.cfg["http_defaults"]["politeness_delay_seconds"],
            max_retries=self.cfg["http_defaults"]["max_retries"],
            backoff_factor=self.cfg["http_defaults"]["backoff_factor"],
            raw_base_dir=os.path.join(self.cfg["paths"]["raw_dir"], "storefront"),
            base_dir=self.base_dir
        )
        self.tranco_ingestor = TrancoIngestor(
            api_template=self.cfg["external_sources"]["tranco"]["api_url"],
            user_agent=self.cfg["http_defaults"]["user_agent"],
            timeout=self.cfg["http_defaults"]["timeout_seconds"],
            politeness_delay=self.cfg["external_sources"]["tranco"]["politeness_delay_seconds"],
            raw_base_dir=os.path.join(self.cfg["paths"]["raw_dir"], "tranco"),
            base_dir=self.base_dir
        )
        self.search_ingestor = GoogleTrendsIngestor(
            raw_search_dir=os.path.join(self.cfg["paths"]["raw_dir"], "search"),
            base_dir=self.base_dir
        )
        self.cleaner = StorefrontCleaner()
        self.quality_checker = CatalogQualityChecker(
            drift_threshold_pct=self.cfg["quality_thresholds"]["product_count_drift_alert_pct"]
        )
        self.search_quality_checker = SearchDemandQualityChecker()

    def initialize_environment(self) -> None:
        """Sets up directories, DuckDB DDL schemas, and seeds dim_brand."""
        self.db.init_schemas()
        self.db.seed_dim_brand(
            brands_config=self.cfg["brands"],
            category=self.cfg["category"],
            geo=self.cfg["geography"],
            currency=self.cfg["currency"]
        )

    def run_storefront_ingestion(self, snapshot_date: Optional[str] = None) -> Dict[str, Any]:
        """Ingests, cleans, validates, and stores public catalog snapshots for all configured brands."""
        if snapshot_date is None:
            snapshot_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        results = {}
        for brand_key, b_cfg in self.cfg["brands"].items():
            if not b_cfg.get("is_active", True):
                continue

            brand_id = b_cfg["brand_id"]
            endpoint = b_cfg["endpoint"]
            batch_size = b_cfg.get("batch_size", 250)

            t_start = datetime.now(timezone.utc)
            http_status, raw_records, raw_files, err_msg = self.storefront_ingestor.ingest_brand_catalog(
                brand_id=brand_id,
                base_endpoint=endpoint,
                batch_size=batch_size,
                snapshot_date=snapshot_date
            )

            # Clean and validate
            df_cleaned, rejected_records, clean_stats = self.cleaner.clean_records(raw_records)
            quality_report = self.quality_checker.check_catalog_snapshot(df_cleaned)

            # Determine execution status
            if http_status != 200 or err_msg:
                exec_status = "FAILED"
            elif not quality_report.is_valid:
                exec_status = "WARNING"
            else:
                exec_status = "SUCCESS"

            t_end = datetime.now(timezone.utc)

            # Structured logging
            audit_entry = self.audit_logger.log_run(
                job_start_time=t_start,
                job_end_time=t_end,
                source_name=f"storefront_{brand_id}",
                brand_id=brand_id,
                http_status=http_status,
                records_extracted=len(raw_records),
                records_passed=len(df_cleaned),
                records_rejected=len(rejected_records),
                execution_status=exec_status,
                error_message=err_msg or ("; ".join(quality_report.errors) if quality_report.errors else None)
            )
            self.db.insert_audit_log(audit_entry)

            # Store in DuckDB
            if not df_cleaned.empty and quality_report.is_valid:
                self.db.upsert_catalog_snapshot(df_cleaned)

            results[brand_id] = {
                "http_status": http_status,
                "raw_records": len(raw_records),
                "cleaned_records": len(df_cleaned),
                "rejected_records": len(rejected_records),
                "raw_files_saved": raw_files,
                "quality_report": quality_report.to_dict(),
                "status": exec_status
            }

        return results

    def run_tranco_ingestion(self, observation_date: Optional[str] = None) -> Dict[str, Any]:
        """Ingests daily Tranco global popularity ranks for all brand domains."""
        if observation_date is None:
            observation_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        import pandas as pd
        records = []
        results = {}

        for brand_key, b_cfg in self.cfg["brands"].items():
            if not b_cfg.get("is_active", True):
                continue

            brand_id = b_cfg["brand_id"]
            domain = b_cfg["domain"]

            t_start = datetime.now(timezone.utc)
            status, rec, raw_ref, err_msg = self.tranco_ingestor.fetch_domain_rank(
                brand_id=brand_id,
                domain=domain,
                observation_date=observation_date
            )
            t_end = datetime.now(timezone.utc)

            exec_status = "SUCCESS" if (status == 200 and rec) else "FAILED"
            audit_entry = self.audit_logger.log_run(
                job_start_time=t_start,
                job_end_time=t_end,
                source_name=f"tranco_{brand_id}",
                brand_id=brand_id,
                http_status=status,
                records_extracted=1 if rec else 0,
                records_passed=1 if rec else 0,
                records_rejected=0 if rec else 1,
                execution_status=exec_status,
                error_message=err_msg
            )
            self.db.insert_audit_log(audit_entry)

            if rec:
                records.append(rec)

            results[brand_id] = {
                "domain": domain,
                "http_status": status,
                "rank": rec.get("tranco_global_rank") if rec else None,
                "status": exec_status,
                "error": err_msg
            }

        if records:
            df_tranco = pd.DataFrame(records)
            self.db.upsert_domain_popularity(df_tranco)

        return results

    def run_search_ingestion(self) -> Dict[str, Any]:
        """
        Attempts to ingest Google Trends official CSV export.
        If unavailable, records PENDING_MANUAL_REFRESH without generating fake data.
        """
        import pandas as pd
        t_start = datetime.now(timezone.utc)

        cohort_terms = self.cfg["external_sources"]["google_trends"]["cohort_terms"]
        brand_term_mapping = {
            "neemans": "Neeman's",
            "baccabucci": "Bacca Bucci",
            "elevarsports": "Elevar Sports",
            "plaeto": "Plaeto"
        }

        status, records, raw_ref, msg = self.search_ingestor.scan_and_ingest(
            cohort_terms=cohort_terms,
            brand_term_mapping=brand_term_mapping,
            geography=self.cfg["geography"]
        )

        df_search = pd.DataFrame(records) if records else pd.DataFrame()
        records_passed = 0
        records_rejected = 0

        if status == "SUCCESS" and not df_search.empty:
            quality_report = self.search_quality_checker.check_search_demand(df_search)
            if not quality_report.is_valid:
                status = "FAILED"
                msg = f"Search demand data quality checks failed: {'; '.join(quality_report.errors)}"
                records_rejected = len(df_search)
            else:
                records_passed = len(df_search)
                self.db.upsert_search_demand(df_search)

        t_end = datetime.now(timezone.utc)

        audit_entry = self.audit_logger.log_run(
            job_start_time=t_start,
            job_end_time=t_end,
            source_name="google_trends",
            brand_id=None,
            http_status=None,
            records_extracted=len(records),
            records_passed=records_passed,
            records_rejected=records_rejected,
            execution_status=status,
            error_message=msg if status != "SUCCESS" else None
        )
        self.db.insert_audit_log(audit_entry)

        return {
            "status": status,
            "records_loaded": records_passed,
            "raw_file_ref": raw_ref,
            "message": msg
        }

    def build_analytical_features(self, snapshot_date: Optional[str] = None) -> Dict[str, Any]:
        """
        Builds the analytical feature layer (fact_brand_snapshot_features and fact_brand_category_mix)
        from processed catalog snapshots, domain popularity, and search demand observations.
        """
        from src.features.feature_pipeline import AnalyticalFeatureBuilder
        t_start = datetime.now(timezone.utc)

        # 1. Fetch catalog data
        query = "SELECT * FROM fact_catalog_snapshot"
        if snapshot_date:
            query += f" WHERE snapshot_date = '{snapshot_date}'"
        df_catalog = self.db.conn.execute(query).fetchdf()

        # 2. Fetch Tranco and Search data
        df_tranco = self.db.conn.execute("SELECT * FROM fact_domain_popularity").fetchdf()
        df_search = self.db.conn.execute("SELECT * FROM fact_search_demand").fetchdf()

        # Brand names mapping
        brand_names = {cfg["brand_id"]: cfg["name"] for cfg in self.cfg["brands"].values()}

        # 3. Build features
        df_features, df_category_mix = AnalyticalFeatureBuilder.build_snapshot_features(
            df_catalog=df_catalog,
            df_tranco=df_tranco,
            df_search=df_search,
            brand_names=brand_names
        )

        features_loaded = 0
        cat_mix_loaded = 0

        if not df_features.empty:
            features_loaded = self.db.upsert_brand_snapshot_features(df_features)

        if not df_category_mix.empty:
            cat_mix_loaded = self.db.upsert_brand_category_mix(df_category_mix)

        t_end = datetime.now(timezone.utc)

        audit_entry = self.audit_logger.log_run(
            job_start_time=t_start,
            job_end_time=t_end,
            source_name="analytical_feature_layer",
            brand_id=None,
            http_status=None,
            records_extracted=len(df_catalog),
            records_passed=features_loaded,
            records_rejected=0,
            execution_status="SUCCESS" if features_loaded > 0 else "WARNING",
            error_message=None if features_loaded > 0 else "No catalog snapshots available to build features"
        )
        self.db.insert_audit_log(audit_entry)

        return {
            "status": "SUCCESS" if features_loaded > 0 else "WARNING",
            "feature_records_loaded": features_loaded,
            "category_mix_records_loaded": cat_mix_loaded,
            "snapshot_dates": sorted(df_features["snapshot_date"].unique().tolist()) if not df_features.empty else []
        }

    def export_processed_snapshots(self) -> None:
        """Exports processed database tables to Parquet files."""
        parquet_dir = self.cfg["paths"]["parquet_dir"]
        self.db.export_to_parquet("dim_brand", os.path.join(parquet_dir, "dim_brand.parquet"))
        self.db.export_to_parquet("fact_catalog_snapshot", os.path.join(parquet_dir, "fact_catalog_snapshot.parquet"))
        self.db.export_to_parquet("fact_domain_popularity", os.path.join(parquet_dir, "fact_domain_popularity.parquet"))
        self.db.export_to_parquet("fact_search_demand", os.path.join(parquet_dir, "fact_search_demand.parquet"))
        self.db.export_to_parquet("fact_brand_snapshot_features", os.path.join(parquet_dir, "fact_brand_snapshot_features.parquet"))
        self.db.export_to_parquet("fact_brand_category_mix", os.path.join(parquet_dir, "fact_brand_category_mix.parquet"))
        self.db.export_to_parquet("audit_ingestion_log", os.path.join(parquet_dir, "audit_ingestion_log.parquet"))

    def close(self) -> None:
        self.db.close()

