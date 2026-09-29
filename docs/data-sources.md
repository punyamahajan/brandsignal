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
* **Explore URL:** `https://trends.google.com/trends/explore?date=today%2012-m&geo=IN&q=Neemans,Bacca%20Bucci,Elevar%20Sports,Plaeto`
* **Access Tier:** Tier 3 (Public Web Comparison Export).
* **Collection Mechanism:** **Official Batch CSV Export Required.** Unauthenticated programmatic scrapers encounter `HTTP 429` rate limit blocks. The pipeline ingests verified official CSV exports placed in `data/raw/search/{YYYY-MM-DD}/` alongside a `search_metadata.json` manifest.
* **Strict Real-World Rule:** If no official CSV export is deposited, the pipeline logs the source as `PENDING_MANUAL_REFRESH` and preserves the empty table schema. **No synthetic search data is ever generated.**
* **Metrics Provided:**
  * `relative_search_interest` (Weekly index 0–100 on shared cohort scale, observed).
  * `cohort_relative_search_share` (Proportion of total cohort search attention, derived).
* **Limitations:** Represents top-of-funnel relative search curiosity in India; **must never be described as retail market share, unit sales, or absolute search volume.**

---

## 4. Postponed & Infeasible Sources Registry

| Data Source | Intended Signal | Exclusion / Postponement Reason |
| :--- | :--- | :--- |
| **Amazon India & Flipkart** | Customer Reviews & Ratings | Prohibited automated collection; explicit `robots.txt` disallows; aggressive CAPTCHA/bot challenges. Postponed until 1st-party SP-API credentials are provided. |
| **Instagram / Meta Graph API** | Social Content & Followers | Web scraping violates Meta ToS and hits login walls; official API requires 1st-party brand page authentication and Meta App Review. |
| **Google Analytics 4 (GA4)** | Sessions & Conversion Rates | Private first-party data; inaccessible for competitor benchmarking. |
| **SimilarWeb / SEMrush** | Modeled Traffic Volume | Opaque third-party modeled panel estimates; requires enterprise commercial API subscriptions. |
| **Private Financial Statements** | Revenue, COGS, EBITDA | Not publicly observable for unlisted D2C private limited companies. |
