# BrandSignal V1 Competitive Analytics Dashboard

A professional, analytics-first competitive intelligence dashboard built using **Streamlit**, **Altair**, and **DuckDB**. 

BrandSignal enables empirical benchmarking across four Direct-to-Consumer (D2C) footwear brands in India (*Bacca Bucci, Elevar Sports, Neeman's, and Plaeto*) using strictly validated public storefront snapshots and longitudinal Google Trends search data.

---

## 1. How to Launch the Dashboard

From the project root directory (`D:\BrandSignal`), run:

```bash
streamlit run dashboard/app.py
```

By default, the dashboard will start on `http://localhost:8501`.

---

## 2. Required Python Environment

The dashboard uses the project's existing virtual environment and dependencies. No extra machine learning, LLM, or heavy visualization packages are required.

* **Python:** 3.10+
* **Core Libraries:**
  * `streamlit` (UI application framework)
  * `altair` (declarative statistical visualization)
  * `duckdb` (analytical database engine)
  * `pandas` & `numpy` (data processing)

To verify the test suite and dashboard data integrity before launching:
```bash
python -m pytest tests/test_dashboard.py
```

---

## 3. Data Sources

All dashboard views are queried directly from the local analytical database: [`data/processed/brandsignal.duckdb`](file:///D:/BrandSignal/data/processed/brandsignal.duckdb).

1. **Digital Storefront Snapshot (`fact_catalog_snapshot`, `fact_brand_snapshot_features`):**
   * **Observation Date:** `2026-09-29`
   * **Source:** Verbatim public Shopify storefront API endpoints.
   * **Coverage:** 10,576 purchasable variant listings (SKUs) across 2,050 parent product styles. Zero imputed or synthetic records.
2. **Google Trends Search Attention (`fact_search_demand`):**
   * **Observation Period:** `2025-09-28` to `2026-09-27` (53 continuous weekly observations).
   * **Source:** Official Google Trends CSV export for India (`IN`), Web Search, All Categories.
   * **Coverage:** 212 brand-week rows. Exactly 50 weeks have 100% numeric coverage across all 4 brands; 3 weeks contain unquantified low-volume (`<1`) observations.
3. **Domain Popularity (`fact_domain_popularity`):**
   * **Observation Date:** `2026-09-28`
   * **Source:** Tranco Top 1 Million global web traffic ranking list.

---

## 4. Dashboard Structure & Navigation

The dashboard is organized into three analytical tabs with global sidebar controls:

### Sidebar Controls
* **Target Brand Selector:** Choose between `"All brands"` (cohort overview) or focus on a specific brand (*Bacca Bucci, Elevar Sports, Neeman's, Plaeto*).
* **Catalog Snapshot Selector:** Selects point-in-time catalog date (`2026-09-29`).
* **Temporal Scope Callout:** Explicitly distinguishes the static snapshot date (`29 Sep 2026`) from the longitudinal Google Trends range (`Sep 2025 – Sep 2026`).

### Tab 1 — Market Overview
* **Top KPI Cards:**
  * Active Product Styles (Styles)
  * Active SKUs (Listing Depth)
  * Median Listed Selling Price (INR)
  * Price Positioning Index (PPI vs cohort benchmark 1.00)
  * Discounted Catalog Ratio (%)
  * Latest Comparable Relative Search Interest (Week of 2026-09-06)
* **A. Catalog Scale Comparison:** Horizontal bar chart comparing active SKUs or product styles across brands with interactive metric toggle.
* **B. Variant Density:** Bar chart showing SKU depth per parent style against the cohort median reference line (5.77 variants/style).
* **C. Listed Price Positioning:** Bar chart of Price Positioning Index with reference threshold at 1.00 (cohort median).
* **D. Promotional Intensity:** Grouped bar chart comparing Discounted Catalog Ratio (%) and Median Discount Depth (%).

### Tab 2 — Competitive Comparison
* **1. Cohort Benchmark Summary Table:** Comprehensive, sortable table across all 4 brands with formatted prices, IQRs, PPI, promotional metrics, and Tranco ranks.
* **2. Listed Price Distribution:** Percentile range chart displaying P25, Median, and P75 price dispersion. Subtitled: *"Current storefront snapshot; not sales-weighted transaction prices."*
* **3. Assortment Architecture:** Descriptive scatter plot benchmarking style breadth (X) vs variant depth (Y).
* **4. Promotional Breadth vs Depth:** Scatter plot of Discounted Catalog Ratio (X) vs Median Markdown Depth (Y). Strictly descriptive; zero regression lines or correlation metrics.
* **5. Standardized Category Mix:** Stacked bar chart showing category composition. Features an explicit warning highlighting Elevar Sports' source metadata constraint (90.93% Casual/Other).

### Tab 3 — Search Attention (12M)
* **Search Attention KPI Cards:** Mean RSI, Median RSI, Annual Peak RSI, Latest Comparable RSI, and Mean Cohort Relative Search Share.
* **A. 53-Week Relative Search Interest Trajectory:** Multi-brand longitudinal line chart. Preserves low volume (`<1`) as unquantified breaks rather than fabricating zero.
* **B. Cohort Relative Search Share:** Stacked area chart showing share of search attention across the 50 fully comparable weeks. Clearly labeled: *"Share of relative search attention within this four-brand cohort; not footwear market share."*
* **C. Search Spikes Table:** Formatted table of statistically/arithmetically observable week-over-week fluctuations ($|\Delta| \ge 5$). Strictly non-causal; no speculative marketing attribution.

---

## 5. Metric Definitions

* **Active Product Count (`active_product_count`):** Number of unique active parent styles (`product_id`) listed on the storefront.
* **Active SKU Count (`active_sku_count`):** Number of distinct purchasable variant items (`variant_id`).
* **Variant Density (`variant_density`):** $\frac{\text{active\_sku\_count}}{\text{active\_product\_count}}$. Measures sizing/color depth per style.
* **Price Positioning Index (`price_positioning_index`):** $\frac{\text{brand median listed selling price}}{\text{cohort median listed selling price}}$ ($1.00 = \text{cohort median benchmark}$).
* **Discounted Catalog Ratio (`discounted_catalog_ratio`):** Percentage of active SKUs where $\text{compare\_at\_price} > \text{selling\_price}$.
* **Median Discount Depth (`median_discount_depth_pct`):** Median markdown percentage computed strictly across discounted SKUs ($\frac{\text{compare\_at} - \text{selling}}{\text{compare\_at}} \times 100$).
* **Relative Search Interest (`relative_search_interest`):** Google Trends normalized search index [0–100] relative to peak query attention in India.
* **Cohort Relative Search Share (`cohort_relative_search_share`):** Percentage share of total four-brand relative search attention during weeks where all four brands have numeric data.

---

## 6. Empirical Limitations & Guardrails

1. **Point-in-Time Snapshot:** Catalog metrics reflect a single collection date (`2026-09-29`) and do not indicate inventory turnover or historical pricing trajectory.
2. **Listed Prices $\neq$ Transaction Prices:** Prices reflect catalog asking prices. They do not account for checkout coupon codes, bundle promos, or payment gateway discounts.
3. **Reference Price Anchor:** `compare_at_price` is merchant-defined; it does not prove historical transaction volume at that price.
4. **Indexed Search Attention:** Google Trends reflects normalized relative index values, not absolute search counts, revenue, or market share.
5. **Low Volume Semantics (`<1`):** Represents query activity below Google's 1.0 unit normalization threshold. It is preserved as an unquantified low-volume state, not zero.
6. **Elevar Sports Metadata Quality:** 90.93% of Elevar Sports' catalog is classified under `Casual/Other` due to non-specific storefront tags and inclusion of non-footwear products (e.g. cricket bats, socks).
7. **No AI or Prescriptive Rules:** BrandSignal provides descriptive competitive benchmarking without automated recommendations, strategy prescriptions, or causal modeling.
