import streamlit as st
import pandas as pd
from typing import Dict, Any

from dashboard.data_loader import (
    load_brand_features,
    load_price_quantiles,
    compute_cohort_benchmarks
)
from dashboard.charts import (
    build_price_distribution_chart,
    build_assortment_scatter_chart,
    build_discount_scatter_chart,
    BRAND_DISPLAY_NAMES
)

def render_competitors_view(snapshot_date: str = "2026-09-29"):
    """Renders the Competitor Lens view."""
    st.markdown('<div class="brand-title">Competitor Lens</div>', unsafe_allow_html=True)
    st.markdown('<div class="brand-subtitle">Head-to-head empirical contrast across assortment breadth, pricing architecture, and promotional depth.</div>', unsafe_allow_html=True)

    df_features = load_brand_features(snapshot_date=snapshot_date)
    df_quantiles = load_price_quantiles(snapshot_date=snapshot_date)

    # Brand selectors
    brand_keys = list(BRAND_DISPLAY_NAMES.keys())
    c1, c2 = st.columns(2)
    with c1:
        target_b = st.selectbox("Target Brand (My Brand)", brand_keys, index=1, format_func=lambda x: BRAND_DISPLAY_NAMES[x])
    with c2:
        comp_b = st.selectbox("Comparison Competitor", brand_keys, index=0, format_func=lambda x: BRAND_DISPLAY_NAMES[x])

    row_a = df_features[df_features["brand_id"] == target_b]
    row_b = df_features[df_features["brand_id"] == comp_b]

    if not row_a.empty and not row_b.empty:
        da = row_a.iloc[0]
        db = row_b.iloc[0]

        # Metric comparison table
        metrics = [
            ("Active Styles", f"{int(da['active_product_count']):,}", f"{int(db['active_product_count']):,}", f"{int(da['active_product_count']) - int(db['active_product_count']):+,}"),
            ("Active SKUs", f"{int(da['active_sku_count']):,}", f"{int(db['active_sku_count']):,}", f"{int(da['active_sku_count']) - int(db['active_sku_count']):+,}"),
            ("Variant Density (SKUs/Style)", f"{da['variant_density']:.2f}", f"{db['variant_density']:.2f}", f"{da['variant_density'] - db['variant_density']:+.2f}"),
            ("Median Listed Price", f"₹{da['price_median_inr']:,.0f}", f"₹{db['price_median_inr']:,.0f}", f"₹{da['price_median_inr'] - db['price_median_inr']:+,.0f}"),
            ("Price Positioning (PPI)", f"{da['price_positioning_index']:.2f}x", f"{db['price_positioning_index']:.2f}x", f"{da['price_positioning_index'] - db['price_positioning_index']:+.2f}x"),
            ("Discounted Catalog %", f"{da['discounted_catalog_ratio']:.1f}%", f"{db['discounted_catalog_ratio']:.1f}%", f"{da['discounted_catalog_ratio'] - db['discounted_catalog_ratio']:+.1f}%"),
            ("Median Markdown Depth %", f"{da['median_discount_depth_pct']:.1f}%" if pd.notna(da['median_discount_depth_pct']) else "—", f"{db['median_discount_depth_pct']:.1f}%" if pd.notna(db['median_discount_depth_pct']) else "—", "—")
        ]

        df_comp = pd.DataFrame(metrics, columns=["Metric", BRAND_DISPLAY_NAMES[target_b], BRAND_DISPLAY_NAMES[comp_b], "Observed Difference"])
        st.dataframe(df_comp, width="stretch", hide_index=True)

    st.markdown("<div style='margin-top:14px;'></div>", unsafe_allow_html=True)

    # Detailed Charts
    st.markdown('<div class="section-header">Price Distribution & Middle-50% Spread (IQR)</div>', unsafe_allow_html=True)
    chart_dist = build_price_distribution_chart(df_quantiles)
    st.altair_chart(chart_dist, width="stretch")
    st.markdown('<div class="source-caption">Bar spans Middle 50% (P25 to P75). Thick diamond indicates Median Price. Whiskers span Min to Max listed prices.</div>', unsafe_allow_html=True)

    c_s1, c_s2 = st.columns(2)
    with c_s1:
        st.markdown('<div class="section-header">Assortment Scale vs Price Positioning</div>', unsafe_allow_html=True)
        chart_scatter_assort = build_assortment_scatter_chart(df_features)
        st.altair_chart(chart_scatter_assort, width="stretch")
    with c_s2:
        st.markdown('<div class="section-header">Discount Ratio vs Median Markdown Depth</div>', unsafe_allow_html=True)
        chart_scatter_disc = build_discount_scatter_chart(df_features)
        st.altair_chart(chart_scatter_disc, width="stretch")
