-- ==============================================================================
-- BrandSignal: Raw Ingestion & Audit Telemetry DDL (DuckDB / Standard SQL)
-- ==============================================================================

-- Operational Telemetry Log: Tracks every collection run across all sources
CREATE TABLE IF NOT EXISTS audit_ingestion_log (
    log_id VARCHAR PRIMARY KEY,
    job_start_time TIMESTAMP NOT NULL,
    job_end_time TIMESTAMP NOT NULL,
    source_name VARCHAR NOT NULL,
    brand_id VARCHAR,
    http_status INTEGER,
    records_extracted INTEGER NOT NULL,
    records_passed INTEGER NOT NULL,
    records_rejected INTEGER NOT NULL,
    error_message VARCHAR,
    execution_status VARCHAR NOT NULL  -- 'SUCCESS', 'WARNING', 'FAILED', 'PENDING_MANUAL_REFRESH'
);

-- Raw Storefront Snapshot Staging: Mirrors fields extracted directly from raw payloads
CREATE TABLE IF NOT EXISTS staging_storefront_raw (
    collection_timestamp TIMESTAMP NOT NULL,
    snapshot_date DATE NOT NULL,
    brand_id VARCHAR NOT NULL,
    product_id BIGINT NOT NULL,
    product_title VARCHAR NOT NULL,
    product_type VARCHAR,
    handle VARCHAR NOT NULL,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    sku VARCHAR,
    variant_id BIGINT NOT NULL,
    variant_title VARCHAR,
    price_raw VARCHAR NOT NULL,
    compare_at_price_raw VARCHAR,
    available BOOLEAN NOT NULL,
    source_url VARCHAR NOT NULL,
    raw_payload_ref VARCHAR NOT NULL,
    PRIMARY KEY (snapshot_date, variant_id)
);
