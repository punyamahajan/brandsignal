import streamlit as st
import pandas as pd
from typing import Dict, Any

from dashboard.data_loader import (
    load_brand_features,
    compute_cohort_benchmarks,
    load_price_quantiles
)
from dashboard.charts import (
    build_catalog_scale_chart,
    build_variant_density_chart,
    build_price_positioning_chart,
    build_price_median_bar_chart,
    build_discount_dual_chart
)

def render_market_view(snapshot_date: str = "2026-09-29"):
    """Renders the Market Snapshot view."""
    st.markdown('<div class="brand-title">Market Snapshot</div>', unsafe_allow_html=True)
    st.markdown('<div class="brand-subtitle">Cohort scale, assortment breadth, and macro pricing landscape for Indian D2C Footwear.</div>', unsafe_allow_html=True)

    df_features = load_brand_features(snapshot_date=snapshot_date)
    benchmarks = compute_cohort_benchmarks(df_features)

    # 4-Card KPI Row
    kpi_cols = st.columns(4)
    with kpi_cols[0]:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-label">Active Styles</div>
            <div class="kpi-value">{benchmarks.get('total_active_products', 0):,}</div>
            <div class="kpi-context">Cohort Total across 4 brands</div>
        </div>
        """, unsafe_allow_html=True)
    with kpi_cols[1]:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-label">Active SKUs</div>
            <div class="kpi-value">{benchmarks.get('total_active_skus', 0):,}</div>
            <div class="kpi-context">Cohort Total Purchasable Listings</div>
        </div>
        """, unsafe_allow_html=True)
    with kpi_cols[2]:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-label">Median Listed Price</div>
            <div class="kpi-value">₹{benchmarks.get('median_price_inr', 0):,.0f}</div>
            <div class="kpi-context">Cohort Median Benchmark</div>
        </div>
        """, unsafe_allow_html=True)
    with kpi_cols[3]:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-label">Discounted Catalog %</div>
            <div class="kpi-value">{benchmarks.get('median_discount_ratio', 0):.1f}%</div>
            <div class="kpi-context">Cohort Median Penetration</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<div style='margin-top:14px;'></div>", unsafe_allow_html=True)

    # Visualizations
    col1, col2 = st.columns(2)
    with col1:
        st.markdown('<div class="section-header">1. Catalog Scale: Styles vs Active SKUs</div>', unsafe_allow_html=True)
        chart_scale = build_catalog_scale_chart(df_features)
        st.altair_chart(chart_scale, width="stretch")
        st.markdown('<div class="source-caption">Source: Storefront crawl (2026-09-29). Bacca Bucci represents 54.3% of total cohort listings.</div>', unsafe_allow_html=True)

    with col2:
        st.markdown('<div class="section-header">2. Variant Density (SKUs per Style)</div>', unsafe_allow_html=True)
        chart_density = build_variant_density_chart(df_features)
        st.altair_chart(chart_density, width="stretch")
        st.markdown('<div class="source-caption">Source: Storefront crawl (2026-09-29). Variant density indicates sizing/colorway option depth per parent style.</div>', unsafe_allow_html=True)

    col3, col4 = st.columns(2)
    with col3:
        st.markdown('<div class="section-header">3. Price Positioning Index (PPI vs Cohort Median)</div>', unsafe_allow_html=True)
        chart_ppi = build_price_positioning_chart(df_features)
        st.altair_chart(chart_ppi, width="stretch")
        st.markdown('<div class="source-caption">Formula: Brand Median Price / Cohort Median Price (₹1,899). 1.0 = Cohort Parity.</div>', unsafe_allow_html=True)

    with col4:
        st.markdown('<div class="section-header">4. Promotional Penetration & Markdown Depth</div>', unsafe_allow_html=True)
        chart_disc = build_discount_dual_chart(df_features)
        st.altair_chart(chart_disc, width="stretch")
        st.markdown('<div class="source-caption">Elevar Sports exhibits markdown discipline (47.8% discounted catalog ratio).</div>', unsafe_allow_html=True)

    # Benchmark Summary Table
    st.markdown('<div class="section-header">Cohort Benchmark Summary Table</div>', unsafe_allow_html=True)
    bench_table = df_features[[
        "brand_name",
        "active_product_count",
        "active_sku_count",
        "variant_density",
        "price_median_inr",
        "price_positioning_index",
        "discounted_catalog_ratio",
        "median_discount_depth_pct",
        "tranco_global_rank"
    ]].copy()

    bench_table.columns = [
        "Brand",
        "Styles",
        "SKUs",
        "Variants / Style",
        "Median Price",
        "Price Positioning (PPI)",
        "Discounted Catalog (%)",
        "Median Discount Depth (%)",
        "Tranco Global Rank"
    ]

    st.dataframe(
        bench_table.style.format({
            "Styles": "{:,}",
            "SKUs": "{:,}",
            "Variants / Style": "{:.2f}",
            "Median Price": "₹{:,.0f}",
            "Price Positioning (PPI)": "{:.2f}x",
            "Discounted Catalog (%)": "{:.1f}%",
            "Median Discount Depth (%)": lambda v: f"{v:.1f}%" if pd.notna(v) else "—",
            "Tranco Global Rank": lambda v: f"{int(v):,}" if pd.notna(v) and v > 0 else "Unranked"
        }),
        width="stretch",
        hide_index=True
    )
