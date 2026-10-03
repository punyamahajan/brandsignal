# BrandSignal — Conversational Market Intelligence Platform

BrandSignal is an evidence-grounded **Conversational Market Intelligence Platform** built around the philosophy:

> **"Understand the market. See the gap. Make the call."**

BrandSignal helps business owners and competitive analysts answer four fundamental questions:
1. **WHAT IS HAPPENING** in the market?
2. **WHERE DOES MY BRAND DIFFER** from competitors?
3. **WHAT ARE COMPETITORS DOING DIFFERENTLY?**
4. **WHAT EVIDENCE SUPPORTS THIS?**

BrandSignal strictly avoids answering: *"What should I do?"* — that strategic decision belongs entirely to the human business owner.

---

## 1. Product Philosophy & Non-Prescriptive Discipline

BrandSignal is **NOT**:
* An automated AI business consultant or generic ChatGPT wrapper.
* A recommendation engine giving unsolicited advice (*"You should lower prices by 10%"*).
* A system that invents causal explanations for why a competitor succeeded.
* A tool that hallucinates prices, sales figures, or citation links.

BrandSignal **IS**:
* An objective, evidence-first intelligence analyst.
* A hybrid system where an LLM handles natural language dialogue and tool planning, while deterministic analytical queries and verified public data provide 100% of the numerical facts and citations.
* A transparent research partner where every market finding is backed by an auditable `EvidenceItem` accessible via *"Why are you saying this?"*.

---

## 2. Hybrid System Architecture

```
                                  USER
                                   │  (Natural Language Query)
                                   ▼
             ┌───────────────────────────────────────────┐
             │       Conversational Orchestrator         │
             │   (Multi-Turn Session State & Memory)     │
             └─────────────────────┬─────────────────────┘
                                   │
                                   ▼
             ┌───────────────────────────────────────────┐
             │       LLM Reasoning & Provider Layer      │
             │   (Anthropic / OpenAI / Gemini / Fallback)│
             │                                           │
             │  1. Extract Brand Context (industry, cat) │
             │  2. Decide: Clarify OR Plan Tools         │
             └─────────────────────┬─────────────────────┘
                                   │
                    ┌──────────────┴──────────────┐
                    ▼                             ▼
       ┌─────────────────────────┐   ┌─────────────────────────┐
       │     Analytics Tools     │   │     Research Tools      │
       │  (DuckDB Storefront,    │   │  (Public Web Search,    │
       │   Features, Category    │   │   Brand Site Metadata,  │
       │   Mix, Gap Engine)      │   │   Reddit, YouTube)      │
       └────────────┬────────────┘   └────────────┬────────────┘
                    │                             │
                    └──────────────┬──────────────┘
                                   ▼
             ┌───────────────────────────────────────────┐
             │        Structured Evidence Layer          │
             │   (List of EvidenceItem: Source, Date,    │
             │    Metric, Observation, Value, Provenance)│
             └─────────────────────┬─────────────────────┘
                                   │
                                   ▼
             ┌───────────────────────────────────────────┐
             │      LLM Evidence Synthesis Engine        │
             │  - Synthesizes findings using Evidence    │
             │  - References [EVID-...] citation tags    │
             │  - Verifies citations against store       │
             │  - Attaches "Why are you saying this?"    │
             │  - Suggests Visual Analytics Deep Links   │
             └─────────────────────┬─────────────────────┘
                                   │
                                   ▼
             ┌───────────────────────────────────────────┐
             │             Presentation Layer            │
             │  (Decoupled Streamlit Client / React-ready│
             │   Ask BrandSignal | Market | Competitors  │
             │   Gaps | Trends | Evidence Explorer)      │
             └───────────────────────────────────────────┘
```

---

## 3. Data Flow & Separation of Responsibilities

### 3.1 LLM Responsibilities
* **Natural Language Interpretation:** Understands diverse conversational phrasings, greetings, and complex multi-part questions.
* **Brand Context Onboarding:** Extracts structured brand attributes (`brand_name`, `industry`, `category`, `price_positioning`, `customer_segment`).
* **Clarification Dialogues:** Detects underspecified queries and generates targeted clarification questions rather than guessing.
* **Tool Planning:** Selects appropriate analytical tools (`compare_brands`, `find_brand_gaps`, `compare_prices`, etc.) with parameter-safe arguments.
* **Evidence Synthesis:** Translates raw tool metrics into concise, professional intelligence narratives with citation tags.
* **Conversational Memory:** Preserves multi-turn dialogue context across the session.

### 3.2 Analytics Responsibilities (DuckDB Source of Truth)
* **Single Source of Truth:** All numerical calculations (catalog counts, price medians, IQR, Price Positioning Index, discount ratios, markdown depths, search shares) are computed deterministically in DuckDB.
* **Zero Generated SQL:** The LLM does not generate arbitrary SQL. All analytical execution goes through parameter-safe Python tool functions.

### 3.3 Research Responsibilities
* **Public Discovery:** Connects to public web search (DuckDuckGo), official brand domains, Google Trends, and public discussion endpoints (Reddit).
* **Respectful Scraping:** Strict user-agent headers, rate limits, and politeness delays (1.0s to 2.0s).
* **Honest Availability:** Unconfigured providers (e.g. YouTube requiring `YOUTUBE_API_KEY`) are clearly marked as `Unavailable` rather than faking data.

---

## 4. Evidence & Provenance System

Every factual claim emitted by BrandSignal is accompanied by an explicit `EvidenceItem`:

```python
@dataclass
class EvidenceItem:
    evidence_id: str             # e.g., "EVID-SNAP-BACCABUCCI"
    source_name: str             # e.g., "Bacca Bucci Digital Storefront Crawl"
    source_type: str             # "storefront_catalog" | "google_trends" | "tranco" | "web_search"
    source_url: Optional[str]    # Canonical source link
    collected_at: str            # ISO-8601 timestamp
    brand_id: str                # e.g., "baccabucci"
    brand_name: str              # e.g., "Bacca Bucci"
    metric: str                  # e.g., "active_catalog_scale"
    observation: str             # Factual observation description
    value: Any                   # e.g., {"styles": 1077, "skus": 5744, "median_price": 1499.0}
    confidence: float            # 1.0 for verified primary sources
    raw_reference: Optional[str] # Pointer to underlying table (e.g. "fact_brand_snapshot_features")
    dataset_name: Optional[str]  # Database or file origin
    limitation_note: Optional[str]
```

### Citation Verification & Anti-Hallucination
When the LLM synthesizes a response citing `[EVID-...]` tags, `EvidenceStore.verify_citations()` validates every cited tag against the store. If the model invents a citation ID that was not generated by an executed tool, it is discarded immediately.

### "Why are you saying this?" Provenance Viewer
Every assistant turn in the UI includes an expandable **"Why are you saying this?"** drawer displaying the exact primary source, collection timestamp, raw observation, dataset reference, and relevant methodological limitations.

---

## 5. Supported Data Sources & Known Limitations

| Data Source | Collection Mechanism | Update Cadence | Key Limitations |
|---|---|---|---|
| **Shopify Storefronts** | Public `/products.json` pagination | Point-in-time snapshot (`2026-09-29`) | Asking prices $\ne$ transaction prices. Does not reflect stock inventory or sales volume. |
| **Google Trends** | Official 53-week India export | Weekly longitudinal (`Sep 2025 – Sep 2026`) | Relative search index [0-100], not absolute search volume. Cohort search share $\ne$ footwear market share. |
| **Tranco Global Rank** | Daily Tranco 1M API | Point-in-time (`2026-09-28`) | Measures website domain popularity, not commercial revenue. |
| **DuckDuckGo API** | Public Knowledge Graph endpoint | Real-time | Search engine summary freshness. |
| **Brand Website** | Public HTML / Meta parser | Real-time | Governed by robots.txt and site accessibility. |
| **Reddit API** | Public subreddit search JSON | Real-time | Unstructured public opinions; not statistically sampled consumer research. |

---

## 6. Gap Explorer & Competitor Lens

### 6.1 Gap Explorer Semantics
A **"gap"** is defined strictly as:
> *An observable characteristic present or more represented among comparison brands but absent or less represented in the target brand.*

Examples:
* **Assortment Gap:** Target brand lists 42 styles; competitor peak is 118 styles (delta: 76 styles).
* **Category Coverage Gap:** Competitor set offers Running, Walking, and Casual; target brand only lists Casual and Slides.
* **Pricing Gap:** Target brand median price is ₹1,899 vs cohort benchmark of ₹1,499.

**Non-Prescriptive Guardrail Alert:**
> *"BrandSignal reports observable catalog differences in public storefront listings. This does NOT constitute a recommendation to expand your catalog, launch new categories, or match competitor breadth. Assortment decisions depend on unit economics, margin targets, and merchant brand identity."*

### 6.2 Competitor Lens
Enables symmetric, side-by-side benchmarking of any two brands across active styles, active SKUs, variant density, median price, Price Positioning Index (PPI), promotional penetration, and relative search share.

---

## 7. Decoupled Presentation Layer & Navigation

The frontend is separated into six modular views under `dashboard/views/`:

1. **`💬 Ask BrandSignal` (`ask_view.py`):**
   * Conversational onboarding & active brand context badge.
   * Suggested inquiry chips (*"What's happening in my market?", "What is my brand missing?", "Who is cheaper?"*).
   * Interactive chat history with factual narrative cards.
   * Expandable *"Why are you saying this?"* source provenance drawer.
   * Visual Analytics deep links (*[Explore in Gaps →]*, *[Explore in Competitors →]*).
2. **`📊 Market` (`market_view.py`):** Cohort totals KPI cards, catalog scale chart, variant density chart, Price Positioning Index, and benchmark table.
3. **`⚖️ Competitors` (`competitors_view.py`):** Head-to-head comparison lens, price distribution IQR chart, assortment/discount scatter plots.
4. **`🔍 Gaps` (`gaps_view.py`):** Gap summary KPIs, category coverage matrix, standardized category mix chart, and non-prescriptive guardrail callout.
5. **`📈 Trends` (`trends_view.py`):** 53-week Google Trends trajectory chart, 50-week cohort search share area chart, and observed WoW search spike table.
6. **`📑 Evidence` (`evidence_view.py`):** Audit viewer for all collected `EvidenceItem` records with source filters, primary links, and raw references.

### Headless Architecture (React-Ready)
`dashboard/app.py` contains zero core business logic. All conversational state, context extraction, tool execution, and evidence storage live in `src/orchestrator/service.py`. A FastAPI server and React SPA can replace Streamlit without changing any underlying Python code.

---

## 8. Extension Guides

### How to Add Another Industry
1. Define brand context in `BrandContext` (e.g. `industry="Beverages"`, `category="Carbonated Soft Drinks"`).
2. To add verified offline analytics for that vertical:
   * Insert brand records into `dim_brand` with `category="Carbonated Soft Drinks"`.
   * Ingest catalog JSON into `fact_catalog_snapshot`.
   * Run `AnalyticalFeatureBuilder.build_snapshot_features()`.
3. To research dynamically:
   * `WebSearchProvider` and `BrandSiteProvider` discover competitors on the fly for any consumer category.

### How to Add Another Research Provider
1. Create `src/research/new_provider.py` subclassing `ResearchProvider` from `src/research/base.py`.
2. Implement `name`, `is_available`, `status_description`, and `search(query) -> ResearchResult`.
3. Register the new provider in `SourceRegistry`:
   ```python
   from src.research.new_provider import NewProvider
   registry.register_provider(NewProvider())
   ```

---

## 9. Verification & Test Suite Summary

The entire platform is verified by **99 automated tests** passing 100%:

```powershell
python -m pytest
============================= 99 passed in 3.65s ==============================
```

* `tests/test_analysis.py`: 6 passed (positioning tables, quantiles, discounts)
* `tests/test_analytical_features.py`: 9 passed (feature pipeline, PPI, variant density)
* `tests/test_cleaning_validation.py`: 3 passed (storefront cleaning, deduplication)
* `tests/test_conversational_analytics.py`: 37 passed (intent, entity, legacy routing)
* `tests/test_dashboard.py`: 9 passed (data loader, Altair chart builders)
* `tests/test_evidence_provenance.py`: 4 passed (evidence CRUD, citation verification, audit logs)
* `tests/test_gap_explorer.py`: 3 passed (gap calculation, non-prescriptive guardrail)
* `tests/test_hybrid_orchestrator.py`: 6 passed (greetings, cross-industry context, multi-turn state)
* `tests/test_llm_abstraction.py`: 4 passed (provider factory, schemas, tool planning)
* `tests/test_quality_checks.py`: 3 passed (assertions, drift alerts)
* `tests/test_research_layer.py`: 4 passed (source registry, rate limits, graceful degradation)
* `tests/test_search_ingestion.py`: 9 passed (Google Trends ingestion, metadata validation)
* `tests/test_storefront_parser.py`: 2 passed (Shopify JSON parser)
