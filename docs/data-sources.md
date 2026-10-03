# BrandSignal: Data Sources & Metric Dictionary
**Analytical Focus:** Indian D2C Footwear Competitive Intelligence  
**Standard Version:** 1.0 (Analytics-First, Zero Synthetic Data)  

---

## 1. Data Governance & Operational Tiers

BrandSignal strictly enforces a 4-tier data accessibility and governance framework:

| Access Tier | Definition | Examples | Pipeline Action |
| :--- | :--- | :--- | :--- |
| **Tier 1: Explicitly Authorized API Access** | Authenticated developer access with formal credentials / SLAs | First-party Shopify Admin API, Google Cloud APIs | Preferred for focal brand's 1st-party data |
| **Tier 2: Publicly Observable Open Research APIs** | Free, open research endpoints publishing public data without authentication | Tranco Top-1M List API, Stock exchange portals | Fully endorsed for automated competitor benchmarking |
| **Tier 3: Publicly Observable Storefront Feeds** | Data published intentionally to the public web by merchants | Shopify `/products.json`, XML sitemaps, JSON-LD microdata | Automated polite retrieval (throttled 2.0s delay, snapshot-only) |
| **Tier 4: Inappropriate / Prohibited Collection** | Platforms prohibiting automated extraction or using anti-bot firewalls | Amazon India reviews, Instagram web profiles, Trustpilot | **Strictly excluded & marked POSTPONED** |

---

## 2. Standard Metric Documentation Standard (The 6-Tuple)

Every metric in BrandSignal is documented and validated against the standard 6-tuple:
1. **Metric Name & Definition:** Exact conceptual definition and mathematical derivation.
2. **Source:** Origin platform or dataset.
3. **Collection Method:** Endpoint, protocol, rate limits, and extraction rules.
4. **Unit:** Measurement unit (`₹ INR`, `0–100 index`, `integer count`, `percentage %`).
5. **Time Period & Granularity:** Observation frequency (`Daily`, `Weekly rolling`, `Point-in-time snapshot`).
6. **Geography:** Geographical scope (`IN` / India, `Global`).

---

## 3. Approved V1 Data Sources Catalog

### Source 1: Public E-Commerce Storefront Feeds (Shopify REST JSON)
* **Endpoints:**
  * Neeman's: `https://neemans.com/products.json?limit=250&page={n}`
  * Bacca Bucci: `https://baccabucci.com/products.json?limit=250&page={n}`
  * Elevar Sports: `https://elevarsports.com/products.json?limit=250&page={n}`
  * Plaeto: `https://plaeto.in/products.json?limit=250&page={n}`
* **Access Tier:** Tier 3 (Publicly Observable Web Feed).
* **Collection Mechanism:** Automated `HTTP GET` with polite throttling (minimum 2.0s sleep between paginated requests), exponential backoff on `HTTP 429`/`5xx`.
* **Raw Response Auditability:** Unmutated JSON payloads are preserved directly in `data/raw/storefront/{brand}/{YYYY-MM-DD}/page_{n}.json`.
* **Metrics Provided:**
  * `selling_price_inr` (Selling price in INR, observed)
  * `compare_at_price_inr` (Listed MRP, observed)
  * `is_discounted` (Boolean flag: `compare_at > price`, derived)
  * `discount_pct` (Markdown percentage off compare-at price, derived)
  * `is_available` (Live stock availability flag, observed)
  * `active_product_count` (Unique parent styles, derived)
  * `active_sku_count` (Total variants, derived)
  * `variant_density` (Variants per product, derived)
  * `category_std` (Standardized footwear category, derived)

### Source 2: Tranco Top-1M List Research API
* **Endpoint:** `https://tranco-list.eu/api/ranks/domain/{domain}`
* **Access Tier:** Tier 2 (Open Research API).
* **Collection Mechanism:** Automated REST API request with 1.0s politeness delay.
* **Raw Response Auditability:** Stored in `data/raw/tranco/{YYYY-MM-DD}/{brand}_{domain}.json`.
* **Metrics Provided:**
  * `tranco_global_rank` (Daily global domain popularity rank in top 1M, observed).
* **Distinction Note:** Measures global domain popularity momentum based on recursive DNS resolution logs. It does **not** measure India-specific traffic or internal pageviews.

### Source 3: Google Trends (India Footwear Cohort)
* **Explore URL:** `https://trends.google.com/trends/explore?date=today%2012-m&geo=IN&q=Neeman%27s,Bacca%20Bucci,Elevar%20Sports,Plaeto`
* **Access Tier:** Tier 3 (Public Web Comparison Export).
* **Collection Mechanism:** **Official Batch CSV Export Ingestion.** Programmatic scrapers encounter `HTTP 429` rate limit blocks. The pipeline ingests verified official CSV exports placed in `data/raw/search/google_trends_india_12m.csv` accompanied by a metadata manifest `data/raw/search/search_metadata.json`.
* **Export Metadata Specifications:**
  * **Source:** Google Trends
  * **Geography:** India (`IN`)
  * **Search Type:** Web Search
  * **Category:** All categories
  * **Time Range:** Past 12 months (53 weekly observation periods: 2025-09-28 to 2026-09-27)
  * **Exact Cohort Search Terms:**
    * `Neeman's` (brand_id: `neemans`)
    * `Bacca Bucci` (brand_id: `baccabucci`)
    * `Elevar Sports` (brand_id: `elevarsports`)
    * `Plaeto` (brand_id: `plaeto`)
  * **Original File:** `data/raw/search/google_trends_india_12m.csv` (Preserved completely unmodified)
* **Strict Real-World & Semantics Rules:**
  * No synthetic data generation or historical observation fabrication.
  * Google Trends relative search interest values are preserved exactly as exported.
  * Google Trends `<1` semantics: Indicates detectable non-zero search curiosity falling below 1% of cohort peak volume ($0 < \text{interest} < 1$). To eliminate invented/synthetic data, `<1` is recorded with `is_low_volume = TRUE` and numeric `relative_search_interest = NULL`. Neither 0 nor 0.5 nor any other arbitrary number is imputed.
  * Missing observations are recorded with numeric `relative_search_interest = NULL` without imputing invented values.
* **Metrics Provided in `fact_search_demand`:**
  * `relative_search_interest_raw` (VARCHAR): Exact string as exported by Google Trends (`'31'`, `'0'`, `'<1'`).
  * `relative_search_interest` (INTEGER, Nullable): Google Trends weekly index ($0–100$) on the shared cohort scale. `NULL` for `<1` and missing periods.
  * `is_low_volume` (BOOLEAN): Boolean flag indicating sub-threshold interest (`<1`).
  * `cohort_relative_search_share` (DECIMAL(5, 2), Nullable): Mathematical proportion (%) of total relative search interest across the four brands in the identical weekly period. Derived **only** when all four cohort brands are present with definite numeric observations; preserved as `NULL` if any brand is missing or flagged as low-volume (`<1`).
* **Essential Analytical Boundaries:**
  * Represents relative search attention/curiosity **strictly within the closed four-brand cohort**.
  * **Must NEVER be described, cited, or modeled as Indian footwear market share, absolute search query counts, transactions, or revenue.**

### Processed Analytical Feature Layer (`fact_brand_snapshot_features`)
* **Grain:** `(snapshot_date, brand_id)`
* **Primary Key:** `PRIMARY KEY (snapshot_date, brand_id)`
* **Metrics Provided:**
  * `active_product_count` (Integer): Number of unique active parent styles (`product_id`) for a brand in a snapshot.
  * `active_sku_count` (Integer): Number of distinct purchasable variants (`variant_id`) for a brand in a snapshot.
  * `variant_density` (Decimal, 2 decimal places): `active_sku_count / active_product_count` (0.0 if active_product_count == 0).
  * `price_min_inr`, `price_p25_inr`, `price_median_inr`, `price_p75_inr`, `price_max_inr`: Listed selling price percentiles in INR across active SKUs.
  * `price_iqr_inr` (Decimal, 2 decimal places): $P_{75} - P_{25}$ measuring catalog price dispersion.
  * `price_positioning_index` (Decimal, 2 decimal places): `brand_median_price / cohort_median_price`. 1.00 = parity with cohort median; >1.00 = premium positioning; <1.00 = value positioning.
  * `discounted_sku_count` (Integer): Count of active SKUs where `compare_at_price > selling_price`.
  * `discounted_catalog_ratio` (Decimal, percentage %): Percentage of active SKUs with a listed markdown: `(discounted_sku_count / active_sku_count) * 100.0`.
  * `median_discount_depth_pct` (Decimal, percentage %): For discounted SKUs only: median of `((compare_at_price - selling_price) / compare_at_price) * 100.0`. `NULL` if 0 discounted SKUs.
  * `tranco_global_rank` (BigInt, Nullable): Tranco global domain popularity rank in top 1M; `NULL` if unranked.
  * `tranco_status` (VarChar): Operational indicator (`'RANKED'`, `'UNRANKED_OUTSIDE_TOP_1M'`, `'UNAVAILABLE'`).
  * `latest_relative_search_interest` (Integer, Nullable): Latest Google Trends RSI index at or preceding snapshot date; `NULL` if `<1` or unavailable.
  * `latest_cohort_search_share` (Decimal, Nullable): Latest cohort search attention share; `NULL` if `<1` was present in the cohort for that week.
  * `new_sku_velocity_30d` (Integer, Nullable): Preserved as `NULL` (Unavailable in V1 due to point-in-time storefront architecture; historical SKU additions cannot be defended from a single crawl).

### Supporting Assortment Category Mix (`fact_brand_category_mix`)
* **Grain:** `(snapshot_date, brand_id, category_std)`
* **Primary Key:** `PRIMARY KEY (snapshot_date, brand_id, category_std)`
* **Metrics Provided:**
  * `category_sku_count` (Integer): Number of active SKUs in the standardized category.
  * `category_share_pct` (Decimal, percentage %): Percentage share of the brand's active catalog in this category.
* **Data Quality Limitation Note:** Elevar Sports storefront feed lacks granular category classification tags, causing 90.9% of its catalog to map to `Casual/Other`. Granular category mix comparisons across the cohort are therefore constrained.

---

## 4. Postponed & Infeasible Sources Registry

| Data Source | Intended Signal | Exclusion / Postponement Reason |
| :--- | :--- | :--- |
| **Amazon India & Flipkart** | Customer Reviews & Ratings | Prohibited automated collection; explicit `robots.txt` disallows; aggressive CAPTCHA/bot challenges. Postponed until 1st-party SP-API credentials are provided. |
| **Instagram / Meta Graph API** | Social Content & Followers | Web scraping violates Meta ToS and hits login walls; official API requires 1st-party brand page authentication and Meta App Review. |
| **Google Analytics 4 (GA4)** | Sessions & Conversion Rates | Private first-party data; inaccessible for competitor benchmarking. |
| **SimilarWeb / SEMrush** | Modeled Traffic Volume | Opaque third-party modeled panel estimates; requires enterprise commercial API subscriptions. |
| **Private Financial Statements** | Revenue, COGS, EBITDA | Not publicly observable for unlisted D2C private limited companies. |
