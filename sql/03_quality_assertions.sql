-- ==============================================================================
-- BrandSignal: Data Quality & Integrity Assertion Queries
-- ==============================================================================

-- 1. Duplicate Variant ID Check in a single snapshot (Must return 0 rows)
SELECT 
    snapshot_date, 
    variant_id, 
    COUNT(*) AS occurrence_count
FROM fact_catalog_snapshot
GROUP BY snapshot_date, variant_id
HAVING COUNT(*) > 1;

-- 2. Non-positive Selling Price Check (Must return 0 rows)
SELECT 
    snapshot_date, 
    brand_id, 
    variant_id, 
    selling_price_inr
FROM fact_catalog_snapshot
WHERE selling_price_inr <= 0 OR selling_price_inr IS NULL;

-- 3. Inverted Discount Check (Selling price strictly exceeding compare-at price - Must return 0 rows)
SELECT 
    snapshot_date, 
    brand_id, 
    variant_id, 
    selling_price_inr, 
    compare_at_price_inr
FROM fact_catalog_snapshot
WHERE compare_at_price_inr IS NOT NULL 
  AND selling_price_inr > compare_at_price_inr;

-- 4. Orphan Foreign Key Check for Catalog (Must return 0 rows)
SELECT 
    f.brand_id, 
    COUNT(*) AS orphaned_records
FROM fact_catalog_snapshot f
LEFT JOIN dim_brand b ON f.brand_id = b.brand_id
WHERE b.brand_id IS NULL
GROUP BY f.brand_id;

-- 5. Duplicate Search Demand Check (Must return 0 rows)
SELECT 
    week_start_date, 
    brand_id, 
    COUNT(*) AS occurrence_count
FROM fact_search_demand
GROUP BY week_start_date, brand_id
HAVING COUNT(*) > 1;

-- 6. Orphan Foreign Key Check for Search Demand (Must return 0 rows)
SELECT 
    f.brand_id, 
    COUNT(*) AS orphaned_records
FROM fact_search_demand f
LEFT JOIN dim_brand b ON f.brand_id = b.brand_id
WHERE b.brand_id IS NULL
GROUP BY f.brand_id;

-- 7. Search Interest Range Check (Must return 0 rows)
SELECT 
    week_start_date, 
    brand_id, 
    relative_search_interest
FROM fact_search_demand
WHERE relative_search_interest IS NOT NULL 
  AND (relative_search_interest < 0 OR relative_search_interest > 100);

-- 8. Cohort Relative Search Share Range Check (Must return 0 rows)
SELECT 
    week_start_date, 
    brand_id, 
    cohort_relative_search_share
FROM fact_search_demand
WHERE cohort_relative_search_share IS NOT NULL 
  AND (cohort_relative_search_share < 0.0 OR cohort_relative_search_share > 100.0);

-- 9. Duplicate Brand Snapshot Features Check (Must return 0 rows)
SELECT 
    snapshot_date, 
    brand_id, 
    COUNT(*) AS occurrence_count
FROM fact_brand_snapshot_features
GROUP BY snapshot_date, brand_id
HAVING COUNT(*) > 1;

-- 10. Orphan Foreign Key Check for Brand Snapshot Features (Must return 0 rows)
SELECT 
    f.brand_id, 
    COUNT(*) AS orphaned_records
FROM fact_brand_snapshot_features f
LEFT JOIN dim_brand b ON f.brand_id = b.brand_id
WHERE b.brand_id IS NULL
GROUP BY f.brand_id;

-- 11. Positive Product and SKU Count Check (Must return 0 rows)
SELECT 
    snapshot_date, 
    brand_id, 
    active_product_count, 
    active_sku_count
FROM fact_brand_snapshot_features
WHERE active_product_count <= 0 OR active_sku_count <= 0;

-- 12. Price Positioning Index Range Check (Must return 0 rows)
SELECT 
    snapshot_date, 
    brand_id, 
    price_positioning_index
FROM fact_brand_snapshot_features
WHERE price_positioning_index <= 0.0 OR price_positioning_index IS NULL;

-- 13. Discounted Catalog Ratio Range Check (Must return 0 rows)
SELECT 
    snapshot_date, 
    brand_id, 
    discounted_catalog_ratio
FROM fact_brand_snapshot_features
WHERE discounted_catalog_ratio < 0.0 OR discounted_catalog_ratio > 100.0;


