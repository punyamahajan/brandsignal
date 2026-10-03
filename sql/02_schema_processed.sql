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
-- Note: relative_search_interest is nullable to preserve Google Trends '<1' (low volume) without inventing values.
-- cohort_relative_search_share is nullable and derived strictly when all 4 cohort brands have valid numeric observations.
CREATE TABLE IF NOT EXISTS fact_search_demand (
    week_start_date DATE NOT NULL,
    brand_id VARCHAR NOT NULL REFERENCES dim_brand(brand_id),
    geography VARCHAR NOT NULL,
    search_term VARCHAR NOT NULL,
    relative_search_interest_raw VARCHAR NOT NULL,
    relative_search_interest INTEGER,
    is_low_volume BOOLEAN NOT NULL DEFAULT FALSE,
    cohort_relative_search_share DECIMAL(5, 2),
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

-- Analytical Brand Snapshot Feature Table
-- Grain: (snapshot_date, brand_id)
-- Consolidates assortment, pricing, discounting, and benchmark signals for each brand snapshot.
CREATE TABLE IF NOT EXISTS fact_brand_snapshot_features (
    snapshot_date DATE NOT NULL,
    brand_id VARCHAR NOT NULL REFERENCES dim_brand(brand_id),
    brand_name VARCHAR NOT NULL,
    active_product_count INTEGER NOT NULL,
    active_sku_count INTEGER NOT NULL,
    variant_density DECIMAL(6, 2) NOT NULL,
    price_min_inr DECIMAL(10, 2),
    price_p25_inr DECIMAL(10, 2),
    price_median_inr DECIMAL(10, 2) NOT NULL,
    price_p75_inr DECIMAL(10, 2),
    price_max_inr DECIMAL(10, 2),
    price_iqr_inr DECIMAL(10, 2) NOT NULL,
    price_positioning_index DECIMAL(5, 2) NOT NULL,
    discounted_sku_count INTEGER NOT NULL,
    discounted_catalog_ratio DECIMAL(5, 2) NOT NULL,
    median_discount_depth_pct DECIMAL(5, 2),
    tranco_global_rank BIGINT,
    tranco_status VARCHAR NOT NULL,
    latest_relative_search_interest INTEGER,
    latest_cohort_search_share DECIMAL(5, 2),
    new_sku_velocity_30d INTEGER,
    created_at TIMESTAMP NOT NULL,
    PRIMARY KEY (snapshot_date, brand_id)
);

-- Assortment Standardized Category Mix Table
-- Grain: (snapshot_date, brand_id, category_std)
CREATE TABLE IF NOT EXISTS fact_brand_category_mix (
    snapshot_date DATE NOT NULL,
    brand_id VARCHAR NOT NULL REFERENCES dim_brand(brand_id),
    category_std VARCHAR NOT NULL,
    category_sku_count INTEGER NOT NULL,
    category_share_pct DECIMAL(5, 2) NOT NULL,
    created_at TIMESTAMP NOT NULL,
    PRIMARY KEY (snapshot_date, brand_id, category_std)
);

