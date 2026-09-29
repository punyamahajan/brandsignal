import sys
import os
sys.path.insert(0, os.path.abspath("."))
import json
from src.pipeline import BrandSignalPipeline

def main():
    print("=" * 60)
    print("Starting BrandSignal V1 Live Ingestion Dry-Run")
    print("=" * 60)

    pipeline = BrandSignalPipeline(config_path="config/sources.yaml", base_dir=".")
    
    # 1. Initialize environment, DuckDB DDL, and dim_brand
    print("\n[Step 1] Initializing DuckDB and Dimension Tables...")
    pipeline.initialize_environment()
    print("DuckDB schema initialized and dim_brand seeded.")

    # 2. Ingest Storefronts
    print("\n[Step 2] Executing Storefront Ingestion for 4 Brands...")
    storefront_results = pipeline.run_storefront_ingestion()
    for b_id, res in storefront_results.items():
        print(f"  -> {b_id}: HTTP {res['http_status']} | Raw: {res['raw_records']} | Cleaned: {res['cleaned_records']} | Rejected: {res['rejected_records']} | Status: {res['status']}")
        if res["quality_report"]["warnings"]:
            print(f"     Warnings: {res['quality_report']['warnings']}")
        if res["quality_report"]["errors"]:
            print(f"     Errors: {res['quality_report']['errors']}")

    # 3. Ingest Tranco Ranks
    print("\n[Step 3] Executing Tranco Domain Popularity Ingestion...")
    tranco_results = pipeline.run_tranco_ingestion()
    for b_id, res in tranco_results.items():
        print(f"  -> {b_id} ({res['domain']}): HTTP {res['http_status']} | Global Rank: {res['rank']} | Status: {res['status']}")

    # 4. Ingest Google Trends Search Demand
    print("\n[Step 4] Checking Google Trends Search Ingestion...")
    search_results = pipeline.run_search_ingestion()
    print(f"  -> Google Trends Status: {search_results['status']}")
    print(f"     Records Loaded: {search_results['records_loaded']}")
    print(f"     Message: {search_results['message']}")

    # 5. Export Processed Parquet Snapshots
    print("\n[Step 5] Exporting Processed Tables to Parquet...")
    pipeline.export_processed_snapshots()
    print("Parquet exports completed.")

    # 6. Verify Database Tables
    print("\n[Step 6] Inspecting DuckDB Tables...")
    tables = pipeline.db.conn.execute("SHOW TABLES").fetchall()
    table_names = [t[0] for t in tables]
    print(f"Tables in DuckDB: {table_names}")

    for t in table_names:
        count = pipeline.db.conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        print(f"  - {t}: {count} rows")

    pipeline.close()
    print("\n" + "=" * 60)
    print("Dry-Run Completed Successfully.")
    print("=" * 60)

if __name__ == "__main__":
    main()
