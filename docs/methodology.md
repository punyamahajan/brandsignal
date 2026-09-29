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

### A. Pricing & Dispersion Metrics
* **Median Selling Price (`price_median_inr`):** 50th percentile of active variant list prices. Median is chosen over arithmetic mean to prevent distortion from low-priced accessories (socks, shoe laces, shoe horn, cleaning kits).
* **Interquartile Range (`price_iqr_inr`):**
  $$\text{IQR} = P_{75} - P_{25}$$
  Measures catalog price focus versus broad price dispersion across multiple tiers.
* **Price Positioning Index (PPI):**
  $$\text{PPI}_{\text{brand}} = \frac{\text{price\_median}_{\text{brand}}}{\text{Median}(\text{price\_median}_{\text{cohort}})} \times 100$$
  * $\text{PPI} > 100$: Premium positioning relative to cohort.
  * $\text{PPI} \approx 100$: Core mass-market parity.
  * $\text{PPI} < 100$: Value / entry-tier positioning.

### B. Promotional Intensity & Markdown Depth
* **Discounted Catalog Ratio:**
  $$\text{Discount Ratio} = \frac{N_{\text{discounted\_skus}}}{N_{\text{total\_active\_skus}}}$$
  Calculated strictly where `compare_at_price_inr > selling_price_inr`.
* **Inverted Discount Correction:** If a merchant incorrectly enters `compare_at_price < selling_price`, the system treats the item as non-discounted (`compare_at_price_inr = NULL`), increments `inverted_discount_corrected` in the telemetry log, and excludes it from markdown depth calculations.
* **Median Discount Depth (%):**
  $$\text{Discount Depth} = \text{Median}\left(\frac{\text{compare\_at\_price} - \text{selling\_price}}{\text{compare\_at\_price}} \times 100\right)$$
  Computed strictly across the subset of legitimately discounted SKUs.

### C. Search Attention & Cohort Share
* **Relative Search Interest (`relative_search_interest`):** The observed Google Trends weekly index ($0–100$).
* **Cohort Relative Search Share (`cohort_relative_search_share`):**
  $$\text{Share}_{i, t} = \frac{\text{RSI}_{i, t}}{\sum_{j \in \text{Cohort}} \text{RSI}_{j, t}} \times 100$$
  * *Constraint:* Represents search curiosity share **only within the closed 4-brand cohort**. It must **never** be cited as retail market share or total sales volume.

---

## 4. Data Quality Assertions & Anomaly Thresholds

Before writing records to the processed fact tables, `CatalogQualityChecker` enforces five automated assertion gates:

1. **Uniqueness Gate:** Assert `COUNT(*) == 0` for duplicate `(snapshot_date, variant_id)` pairs.
2. **Price Sanity Gate:** Assert `selling_price_inr > 0` and `NOT NULL`.
3. **Markdown Sanity Gate:** Assert `compare_at_price_inr >= selling_price_inr` for all non-null compare-at values.
4. **Key Completeness Gate:** Assert `product_id IS NOT NULL` and `variant_id IS NOT NULL`.
5. **Catalog Drift Warning Gate:** If total active product styles change by more than $\pm 25\%$ compared to the previous snapshot, log an operational `WARNING` in `audit_ingestion_log` to alert analysts to potential layout changes or catalog restructuring.
