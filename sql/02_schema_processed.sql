-- ==============================================================================
-- BrandSignal: Processed Normalized Dimensional & Fact Models DDL
-- ==============================================================================

-- Brand Dimension Table
CREATE TABLE IF NOT EXISTS dim_brand (
    brand_id VARCHAR PRIMARY KEY,
    brand_name VARCHAR NOT NULL,
    storefront_domain VARCHAR NOT NULL,
    storefront_endpoint VARCHAR NOT NULL,
    category VARCHAR NOT NULL,
    geography VARCHAR NOT NULL,
    currency VARCHAR NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE
);

-- Catalog Snapshot Fact Table (Normalized & Cleaned)
CREATE TABLE IF NOT EXISTS fact_catalog_snapshot (
    snapshot_date DATE NOT NULL,
    variant_id BIGINT NOT NULL,
    brand_id VARCHAR NOT NULL REFERENCES dim_brand(brand_id),
    product_id BIGINT NOT NULL,
    product_title VARCHAR NOT NULL,
    product_type_raw VARCHAR,
    category_std VARCHAR NOT NULL,
    sku VARCHAR,
    variant_title VARCHAR,
    selling_price_inr DECIMAL(10, 2) NOT NULL,
    compare_at_price_inr DECIMAL(10, 2),
    is_discounted BOOLEAN NOT NULL,
    discount_amount_inr DECIMAL(10, 2),
    discount_pct DECIMAL(5, 2),
    is_available BOOLEAN NOT NULL,
    sku_created_at TIMESTAMP,
    collection_timestamp TIMESTAMP NOT NULL,
    raw_payload_ref VARCHAR NOT NULL,
    PRIMARY KEY (snapshot_date, variant_id)
);

-- Search Demand Fact Table (Google Trends)
CREATE TABLE IF NOT EXISTS fact_search_demand (
    week_start_date DATE NOT NULL,
    brand_id VARCHAR NOT NULL REFERENCES dim_brand(brand_id),
    geography VARCHAR NOT NULL,
    search_term VARCHAR NOT NULL,
    relative_search_interest INTEGER NOT NULL,
    cohort_relative_search_share DECIMAL(5, 2) NOT NULL,
    collection_timestamp TIMESTAMP NOT NULL,
    raw_file_ref VARCHAR NOT NULL,
    PRIMARY KEY (week_start_date, brand_id)
);

-- Domain Popularity Fact Table (Tranco Top-1M List)
CREATE TABLE IF NOT EXISTS fact_domain_popularity (
    observation_date DATE NOT NULL,
    brand_id VARCHAR NOT NULL REFERENCES dim_brand(brand_id),
    domain VARCHAR NOT NULL,
    tranco_global_rank BIGINT NOT NULL,
    collection_timestamp TIMESTAMP NOT NULL,
    PRIMARY KEY (observation_date, brand_id)
);
