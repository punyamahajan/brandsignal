import streamlit as st
import pandas as pd
import numpy as np
import os
import sys

# Ensure project root is in python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

try:
    import dotenv
    dotenv.load_dotenv()
except ImportError:
    pass

from dashboard.data_loader import load_snapshot_dates
from dashboard.views.ask_view import render_ask_view
from dashboard.views.market_view import render_market_view
from dashboard.views.competitors_view import render_competitors_view
from dashboard.views.gaps_view import render_gaps_view
from dashboard.views.trends_view import render_trends_view
from dashboard.views.evidence_view import render_evidence_view

# -----------------------------------------------------------------------------
# Streamlit Page Configuration
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="BrandSignal | Market & Competitive Intelligence",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# -----------------------------------------------------------------------------
# Institutional / Financial Research Terminal Styling
# -----------------------------------------------------------------------------
st.markdown("""
<style>
    /* Global Base */
    html, body, [class*="css"] {
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
        color: #0f172a;
    }
    .stApp {
        background-color: #f8fafc;
    }
    /* Headers */
    .brand-title {
        font-size: 1.6rem;
        font-weight: 800;
        letter-spacing: -0.02em;
        color: #0f172a;
        margin: 0;
        padding: 0;
    }
    .brand-subhead {
        font-size: 1.0rem;
        font-weight: 600;
        color: #334155;
        margin-top: 2px;
        margin-bottom: 4px;
    }
    .brand-subtitle {
        font-size: 0.85rem;
        color: #64748b;
        margin-bottom: 12px;
    }
    .meta-tag {
        display: inline-block;
        background: #f1f5f9;
        border: 1px solid #cbd5e1;
        border-radius: 3px;
        padding: 3px 8px;
        font-size: 0.78rem;
        font-weight: 600;
        color: #334155;
        margin-right: 8px;
    }
    /* Compact KPI Card */
    .kpi-card {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 4px;
        padding: 10px 14px;
        box-shadow: none;
    }
    .kpi-label {
        font-size: 0.70rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: #64748b;
        margin-bottom: 2px;
    }
    .kpi-value {
        font-size: 1.55rem;
        font-weight: 700;
        color: #0f172a;
        line-height: 1.15;
    }
    .kpi-context {
        font-size: 0.76rem;
        color: #475569;
        margin-top: 3px;
    }
    /* Section Headers */
    .section-header {
        font-size: 0.88rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: #0f172a;
        border-bottom: 1px solid #e2e8f0;
        padding-bottom: 4px;
        margin-top: 16px;
        margin-bottom: 10px;
    }
    .source-caption {
        font-size: 0.72rem;
        color: #94a3b8;
        margin-top: 3px;
        margin-bottom: 12px;
    }
</style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# Sidebar: Streamlined Intelligence Controls
# -----------------------------------------------------------------------------
with st.sidebar:
    st.markdown("<div style='font-size:1.20rem; font-weight:800; color:#0f172a;'>BrandSignal</div>", unsafe_allow_html=True)
    st.markdown("<div style='font-size:0.80rem; color:#64748b; margin-bottom:12px;'>Conversational Market Intelligence</div>", unsafe_allow_html=True)

    # Snapshot Date
    available_dates = load_snapshot_dates()
    default_date = "2026-09-29" if "2026-09-29" in available_dates else (available_dates[0] if available_dates else "2026-09-29")
    selected_snapshot_date = st.selectbox(
        "Catalog Snapshot",
        available_dates if available_dates else ["2026-09-29"],
        index=available_dates.index(default_date) if default_date in available_dates else 0
    )

    st.markdown("<div style='margin-top:16px;'></div>", unsafe_allow_html=True)

    # Methodology & Data Notes in Sidebar
    with st.expander("Data Sources & Integrity"):
        st.markdown("""
        * **Catalog Snapshot:** Public storefront crawl on `2026-09-29` (10,576 SKUs, 2,050 styles).
        * **Google Trends:** `Sep 2025 – Sep 2026` (53 weeks), India geography, Web Search.
        * **Domain Rank:** Tranco Top 1M list (`2026-09-28`).
        * **Core Philosophy:** "Understand the market. See the gap. Make the call."
        * **Limitations:**
          - Storefront data is a cross-sectional snapshot.
          - Asking prices $\\neq$ realized transaction prices.
          - Google Trends is relative indexed attention [0-100], not sales volume.
          - Cohort search share is relative attention, not footwear market share.
          - No private commercial metrics (revenue, GMV, sales) are observed.
        """)

# -----------------------------------------------------------------------------
# Main Navigation View (Segmented Control Routing)
# -----------------------------------------------------------------------------
NAV_TABS = [
    "💬 Ask BrandSignal",
    "📊 Market",
    "⚖️ Competitors",
    "🔍 Gaps",
    "📈 Trends",
    "📑 Evidence"
]

if "nav_selection" not in st.session_state:
    st.session_state["nav_selection"] = "💬 Ask BrandSignal"

nav_view = st.segmented_control(
    "Navigation",
    options=NAV_TABS,
    key="nav_selection",
    label_visibility="collapsed"
)

if not nav_view:
    nav_view = st.session_state.get("nav_selection", "💬 Ask BrandSignal")

# -----------------------------------------------------------------------------
# Modular View Routing
# -----------------------------------------------------------------------------
if nav_view == "💬 Ask BrandSignal":
    render_ask_view(snapshot_date=selected_snapshot_date)
elif nav_view == "📊 Market":
    render_market_view(snapshot_date=selected_snapshot_date)
elif nav_view == "⚖️ Competitors":
    render_competitors_view(snapshot_date=selected_snapshot_date)
elif nav_view == "🔍 Gaps":
    render_gaps_view(snapshot_date=selected_snapshot_date)
elif nav_view == "📈 Trends":
    render_trends_view()
elif nav_view == "📑 Evidence":
    render_evidence_view()

# =============================================================================
# METHODOLOGY & DATA NOTES FOOTER
# =============================================================================
st.markdown("<div style='margin-top:28px;'></div>", unsafe_allow_html=True)
with st.expander("Methodology, Primary Data Context & Methodological Guardrails"):
    st.markdown("""
    ### Primary Data Sources
    * **Catalog Snapshot (`2026-09-29`):** Direct public Shopify storefront API collection across Neeman's, Bacca Bucci, Elevar Sports, and Plaeto. 10,576 total purchasable SKU listings across 2,050 parent styles. Zero synthetic or imputed rows.
    * **Google Trends (`2025-09-28` to `2026-09-27`):** Official 53-week Google Trends export for India, Web Search, All Categories. Exactly 50 weeks have complete numeric coverage across all 4 brands; 3 weeks contain `<1` unquantified low-volume observations.
    * **Domain Traffic Popularity (`2026-09-28`):** Tranco Top 1 Million global web traffic ranking list.

    ### Core Methodological Guardrails
    1. **Single Storefront Snapshot:** Catalog and pricing metrics reflect a single point-in-time snapshot (`2026-09-29`) and do not indicate historical catalog additions, retirements, or price trajectory.
    2. **Listed Prices $\\neq$ Transaction Prices:** Prices reflect digital storefront asking prices. Realized transaction prices may be lower due to unobserved checkout coupon codes, bundle discounts, or payment gateway cashbacks.
    3. **Reference Pricing Anchor:** `compare_at_price` represents merchant-declared reference anchors; it does not prove historical transaction volume or consumer savings at that price.
    4. **Google Trends Relative Nature:** Google Trends reports normalized index values [0-100], not absolute search volume, query counts, or revenue.
    5. **Google Trends `<1` Semantics:** Indicates search volume existed above zero but below the 1.0 unit normalization threshold. Preserved as an unquantified low-volume state, never converted to zero.
    6. **Cohort Relative Search Share $\\neq$ Market Share:** Measures relative search attention strictly within this selected four-brand cohort; it is not Indian footwear market share, industry revenue share, or brand equity.
    7. **Cross-Signal Correlations Reference-Only:** Cross-signal correlations are not used as decision metrics because the comparison contains only four brands ($N=4$) and combines a single cross-sectional storefront snapshot with longitudinal Google Trends data.
    8. **Category Classification Quality:** Elevar Sports' source catalog classifies 90.93% of items under non-specific tags mapped to `Casual/Other`.
    9. **Unavailable Private Metrics:** BrandSignal operates exclusively on public and secondary signals. Internal metrics—such as revenue, GMV, return rates, CAC, and conversion rates—are unobserved.
    """)
