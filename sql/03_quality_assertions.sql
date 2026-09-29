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

-- 3. Inverted Discount Check (Selling price strictly exceeding compare-at price; Must return 0 rows)
SELECT 
    snapshot_date, 
    brand_id, 
    variant_id, 
    selling_price_inr, 
    compare_at_price_inr
FROM fact_catalog_snapshot
WHERE compare_at_price_inr IS NOT NULL 
  AND selling_price_inr > compare_at_price_inr;

-- 4. Orphan Foreign Key Check (Must return 0 rows)
SELECT 
    f.brand_id, 
    COUNT(*) AS orphaned_records
FROM fact_catalog_snapshot f
LEFT JOIN dim_brand b ON f.brand_id = b.brand_id
WHERE b.brand_id IS NULL
GROUP BY f.brand_id;
