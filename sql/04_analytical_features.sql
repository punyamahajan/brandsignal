-- ==============================================================================
-- BrandSignal: Analytical Feature Views & Reproducible SQL Transformations
-- ==============================================================================

-- 1. Assortment & Catalog Depth View
CREATE OR REPLACE VIEW view_brand_snapshot_assortment AS
SELECT 
    snapshot_date,
    brand_id,
    COUNT(DISTINCT product_id) AS active_product_count,
    COUNT(DISTINCT variant_id) AS active_sku_count,
    ROUND(COUNT(DISTINCT variant_id)::DECIMAL / NULLIF(COUNT(DISTINCT product_id), 0), 2) AS variant_density
FROM fact_catalog_snapshot
GROUP BY snapshot_date, brand_id;

-- 2. Pricing Dispersion View
CREATE OR REPLACE VIEW view_brand_snapshot_pricing AS
SELECT 
    snapshot_date,
    brand_id,
    ROUND(MIN(selling_price_inr), 2) AS price_min_inr,
    ROUND(QUANTILE_CONT(selling_price_inr, 0.25), 2) AS price_p25_inr,
    ROUND(MEDIAN(selling_price_inr), 2) AS price_median_inr,
    ROUND(QUANTILE_CONT(selling_price_inr, 0.75), 2) AS price_p75_inr,
    ROUND(MAX(selling_price_inr), 2) AS price_max_inr,
    ROUND(QUANTILE_CONT(selling_price_inr, 0.75) - QUANTILE_CONT(selling_price_inr, 0.25), 2) AS price_iqr_inr
FROM fact_catalog_snapshot
WHERE selling_price_inr > 0
GROUP BY snapshot_date, brand_id;

-- 3. Promotional Intensity & Markdown Depth View
CREATE OR REPLACE VIEW view_brand_snapshot_discounts AS
SELECT 
    snapshot_date,
    brand_id,
    COUNT(CASE WHEN is_discounted THEN 1 END) AS discounted_sku_count,
    ROUND(COUNT(CASE WHEN is_discounted THEN 1 END)::DECIMAL * 100.0 / NULLIF(COUNT(*), 0), 2) AS discounted_catalog_ratio,
    ROUND(MEDIAN(CASE WHEN is_discounted THEN discount_pct ELSE NULL END), 2) AS median_discount_depth_pct
FROM fact_catalog_snapshot
GROUP BY snapshot_date, brand_id;

-- 4. Standardized Assortment Category Mix View
CREATE OR REPLACE VIEW view_brand_category_mix AS
WITH brand_totals AS (
    SELECT snapshot_date, brand_id, COUNT(*) AS total_skus
    FROM fact_catalog_snapshot
    GROUP BY snapshot_date, brand_id
)
SELECT 
    c.snapshot_date,
    c.brand_id,
    c.category_std,
    COUNT(*) AS category_sku_count,
    ROUND(COUNT(*)::DECIMAL * 100.0 / t.total_skus, 2) AS category_share_pct
FROM fact_catalog_snapshot c
JOIN brand_totals t ON c.snapshot_date = t.snapshot_date AND c.brand_id = t.brand_id
GROUP BY c.snapshot_date, c.brand_id, c.category_std, t.total_skus;
