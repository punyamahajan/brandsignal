# BrandSignal: Analytical Methodology & Quality Assurance
**Analytical Focus:** Indian D2C Footwear Competitive Intelligence  
**Standard Version:** 1.0 (Analytics-First, Zero Synthetic Data)  

---

## 1. Analytics-First Core Principles

BrandSignal is an evidence-based market and competitive intelligence platform designed to answer four foundational questions:
1. **What is changing in the market?**
2. **How does the target brand compare with peers?**
3. **Where are the meaningful gaps or differences?**
4. **How has the brand's position evolved over time?**

### Non-Goals & Strict Boundaries
* **No Prescriptive Strategy:** BrandSignal provides objective comparative metrics (e.g. price percentiles, discount depth, search share). It does **not** generate automated business strategies or claim causal attribution (e.g., it will not claim "reducing price by 10% will increase search share by 15%").
* **Zero Generative AI / LLM Dependency:** No LLMs, RAG layers, vector databases, or chatbot interfaces are introduced into the core analytical pipeline.
* **Zero Synthetic Fallbacks:** If a source fails, is blocked, or is missing, the record is flagged in the audit log as `FAILED` or `PENDING_MANUAL_REFRESH`. Synthetic or fabricated numbers are strictly prohibited.

---

## 2. Longitudinal Snapshot Architecture

* **Snapshot Reality:** Public storefront endpoints (`/products.json`) only provide current point-in-time catalog state. Past price changes, flash sales, and delisted styles leave no historical trace in live feeds.
* **Prospective Accumulation:**
  * Rather than fabricating past catalog data, the ingestion pipeline stores timestamped snapshots (`fact_catalog_snapshot`) on each collection run.
  * Longitudinal historical curves are accumulated **forward in time** through scheduled weekly and monthly collection runs.
  * Product introduction age is tracked via `sku_created_at` among surviving catalog items, with full recognition of survivorship bias.

---

## 3. Mathematical & Analytical Formulations

### A. Assortment & Catalog Depth Metrics
* **Active Product Count (`active_product_count`):**
  $$N_{\text{products}} = \text{COUNT(DISTINCT } \text{product\_id)}$$
  Measures the number of distinct active parent styles offered by a merchant in the snapshot.
* **Active SKU Count (`active_sku_count`):**
  $$N_{\text{skus}} = \text{COUNT(DISTINCT } \text{variant\_id)}$$
  Measures total purchasable SKU options (size/color variations) across the catalog.
* **Variant Density (`variant_density`):**
  $$\text{Variant Density} = \frac{N_{\text{skus}}}{N_{\text{products}}}$$
  Measures depth per style (average number of variants per style). Guarded against division by zero ($0.0$ if $N_{\text{products}} = 0$).

### B. Pricing & Dispersion Metrics
* **Median Selling Price (`price_median_inr`):** 50th percentile of active variant list prices. Median is chosen over arithmetic mean to prevent distortion from low-priced accessories (socks, shoe laces, shoe horn, cleaning kits).
* **Interquartile Range (`price_iqr_inr`):**
  $$\text{IQR} = P_{75} - P_{25}$$
  Measures catalog price focus versus broad price dispersion across multiple tiers.
* **Price Positioning Index (PPI):**
  $$\text{PPI}_{\text{brand}} = \frac{\text{price\_median}_{\text{brand}}}{\text{Median}(\text{price\_median}_{\text{cohort}})}$$
  * $\text{PPI} = 1.00$: Equal to cohort median listed price.
  * $\text{PPI} > 1.00$: Listed pricing above cohort median (premium tier).
  * $\text{PPI} < 1.00$: Listed pricing below cohort median (value tier).
  * *Constraint:* Measures listed-price positioning, **NOT** sales-weighted Average Selling Price (ASP) or revenue.

### C. Promotional Intensity & Markdown Depth
* **Discounted Catalog Ratio (`discounted_catalog_ratio`):**
  $$\text{Discount Ratio} = \frac{N_{\text{discounted\_skus}}}{N_{\text{total\_active\_skus}}} \times 100$$
  Percentage of active SKUs where `compare_at_price_inr > selling_price_inr`.
* **Inverted Discount Correction:** If a merchant incorrectly enters `compare_at_price < selling_price`, the system treats the item as non-discounted (`compare_at_price_inr = NULL`), increments `inverted_discount_corrected` in the telemetry log, and excludes it from markdown depth calculations.
* **Median Discount Depth (`median_discount_depth_pct`):**
  $$\text{Discount Depth} = \text{Median}\left(\frac{\text{compare\_at\_price} - \text{selling\_price}}{\text{compare\_at\_price}} \times 100\right)$$
  Computed strictly across the subset of legitimately discounted SKUs. Preserved as `NULL` if a brand has zero discounted SKUs.
* *Important Limitation:* List/compare-at prices reflect merchant marketing conventions. A listed discount does **not** prove that a customer purchased at that price or received that markdown in transaction history.

### D. Optional & Secondary Signals
* **Assortment Category Share (`category_share_pct`):** Percentage breakdown of active SKUs across standardized categories. Evaluated with recognized limitation: Elevar Sports lacks granular category tagging (90.9% mapped to `Casual/Other`), constraining cohort category benchmarking.
* **30-Day New SKU Velocity (`new_sku_velocity_30d`):** Preserved as `NULL` / marked unavailable in V1. Storefront REST feeds represent point-in-time snapshots without delisted items; claiming historical additions from a single crawl would introduce survivorship distortion.
* **Tranco Global Rank (`tranco_global_rank`):** Global recursive DNS domain popularity rank. Unranked domains outside the top 1M are preserved as `NULL` with `tranco_status = 'UNRANKED_OUTSIDE_TOP_1M'`, strictly avoiding fabricated rankings.

### E. Search Attention & Cohort Share
* **Relative Search Interest (`relative_search_interest`):** The observed Google Trends weekly index ($0–100$).
  * *Raw Preservation:* Stored verbatim in `relative_search_interest_raw` (e.g. `'31'`, `'0'`, `'<1'`).
  * *Handling of `<1` (Low Volume):* Google Trends semantics indicate that search interest was non-zero and detectable, but fell below 1% of the peak value ($0 < \text{interest} < 1$). Under BrandSignal's strict zero-synthetic-data principle, `<1` is **never** replaced with an invented number (e.g. neither 0 nor 0.5 is substituted). Instead, `is_low_volume` is set to `TRUE`, and the numeric `relative_search_interest` is preserved as `NULL`.
  * *Missing Periods:* Recorded with numeric `relative_search_interest = NULL` without invented imputation.
* **Cohort Relative Search Share (`cohort_relative_search_share`):**
  $$\text{cohort\_relative\_search\_share}_{i, t} = \frac{\text{RSI}_{i, t}}{\sum_{j \in \text{Cohort}} \text{RSI}_{j, t}} \times 100$$
  * *Cohort Completeness Gate:* Derived **only** after validating that all four cohort brands (`Neeman's`, `Bacca Bucci`, `Elevar Sports`, `Plaeto`) are represented for the given weekly period.
  * *Handling Sub-Threshold Periods:* If any brand in a week has an unquantified sub-unit observation (`<1`) or missing value, the cohort sum cannot be computed with certainty without inventing data. In accordance with zero-synthetic-data rules, `cohort_relative_search_share` is set to `NULL` for all four brands in that week.
  * *All-Zero Sum:* If all four brands have $0$ RSI in a given week, the share is assigned $0.0\%$.
  * *Strict Boundary:* Represents relative search attention/curiosity **strictly within the closed 4-brand cohort**. It must **never** be cited or interpreted as Indian footwear retail market share, absolute search query counts, or sales volume.

---

## 4. Data Quality Assertions & Anomaly Thresholds

Before writing records to processed analytical tables, `CatalogQualityChecker` and `SearchDemandQualityChecker` enforce automated assertion gates:

### Catalog Snapshot Assertions (`CatalogQualityChecker`)
1. **Uniqueness Gate:** Assert `COUNT(*) == 0` for duplicate `(snapshot_date, variant_id)` pairs.
2. **Price Sanity Gate:** Assert `selling_price_inr > 0` and `NOT NULL`.
3. **Markdown Sanity Gate:** Assert `compare_at_price_inr >= selling_price_inr` for all non-null compare-at values.
4. **Key Completeness Gate:** Assert `product_id IS NOT NULL` and `variant_id IS NOT NULL`.
5. **Catalog Drift Warning Gate:** If total active product styles change by more than $\pm 25\%$ compared to the previous snapshot, log an operational `WARNING` in `audit_ingestion_log`.

### Search Demand Assertions (`SearchDemandQualityChecker` & SQL Gates)
6. **Search Uniqueness Gate:** Assert `COUNT(*) == 0` for duplicate `(week_start_date, brand_id)` pairs.
7. **Cohort Representation Gate:** Assert all 4 cohort brands (`neemans`, `baccabucci`, `elevarsports`, `plaeto`) are present in each dataset.
8. **Date Format & Continuity Gate:** Assert all weekly dates strictly adhere to ISO format `YYYY-MM-DD`.
9. **Low-Volume & Value Integrity Gate:** Assert that for every record with `is_low_volume = TRUE`, `relative_search_interest` is `NULL` and `relative_search_interest_raw == '<1'`. Assert all non-null `relative_search_interest` values fall strictly within $[0, 100]$.
10. **Cohort Share Boundary Gate:** Assert that all non-null `cohort_relative_search_share` values fall strictly within $[0.0, 100.0]$, and weeks containing `<1` strictly preserve share as `NULL`.

