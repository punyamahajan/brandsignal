import streamlit as st
import pandas as pd
from typing import Dict, Any

from dashboard.data_loader import (
    load_brand_features,
    load_category_mix,
    compute_cohort_benchmarks
)
from dashboard.charts import (
    build_category_mix_chart,
    BRAND_DISPLAY_NAMES
)

def render_gaps_view(snapshot_date: str = "2026-09-29"):
    """
    Renders the Gap Explorer view.
    Identifies observable characteristics present or more represented in competitors
    but absent or less represented in the target brand.
    """
    st.markdown('<div class="brand-title">Gap Explorer</div>', unsafe_allow_html=True)
    st.markdown('<div class="brand-subtitle">Observable assortment, category coverage, and sizing breadth differences across the competitor set.</div>', unsafe_allow_html=True)

    df_features = load_brand_features(snapshot_date=snapshot_date)
    df_cat = load_category_mix(snapshot_date=snapshot_date)

    brand_keys = list(BRAND_DISPLAY_NAMES.keys())
    target_b = st.selectbox("Select Your Brand Context", brand_keys, index=1, format_func=lambda x: BRAND_DISPLAY_NAMES[x])

    target_row = df_features[df_features["brand_id"] == target_b]
    if not target_row.empty:
        t_data = target_row.iloc[0]
        t_name = BRAND_DISPLAY_NAMES[target_b]

        # Peer comparison
        peers = [b for b in brand_keys if b != target_b]
        peer_df = df_features[df_features["brand_id"].isin(peers)]

        max_peer_styles = int(peer_df["active_product_count"].max())
        max_peer_brand = peer_df.loc[peer_df["active_product_count"].idxmax()]["brand_name"]
        style_delta = max_peer_styles - int(t_data["active_product_count"])

        max_peer_density = float(peer_df["variant_density"].max())
        density_delta = round(max_peer_density - float(t_data["variant_density"]), 2)

        # Categories
        t_cats = set(df_cat[df_cat["brand_id"] == target_b]["category_std"].unique())
        peer_cats = set(df_cat[df_cat["brand_id"].isin(peers)]["category_std"].unique())
        missing_cats = sorted(list(peer_cats - t_cats))

        # KPI Summary
        g_cols = st.columns(3)
        with g_cols[0]:
            st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-label">Assortment Breadth Gap</div>
                <div class="kpi-value">{style_delta:,}</div>
                <div class="kpi-context">Styles below peer peak ({max_peer_brand}: {max_peer_styles:,})</div>
            </div>
            """, unsafe_allow_html=True)

        with g_cols[1]:
            st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-label">Sizing / Option Depth Gap</div>
                <div class="kpi-value">{density_delta:.2f}</div>
                <div class="kpi-context">Fewer SKU variants per parent style vs peer peak</div>
            </div>
            """, unsafe_allow_html=True)

        with g_cols[2]:
            st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-label">Unrepresented Categories</div>
                <div class="kpi-value">{len(missing_cats)}</div>
                <div class="kpi-context">Active in peers but absent in {t_name}</div>
            </div>
            """, unsafe_allow_html=True)

        # Methodological Guardrail
        st.markdown(
            '<div style="font-size:0.75rem; color:#1e3a8a; background:#eff6ff; border:1px solid #bfdbfe; padding:8px 12px; border-radius:4px; margin-top:14px; margin-bottom:14px;">'
            '<b>Non-Prescriptive Guardrail:</b> BrandSignal reports observable catalog differences in public storefront listings. '
            'This does <b>NOT</b> constitute a recommendation to expand your catalog, launch new categories, or match competitor breadth. '
            'Strategic assortment decisions depend on unit economics, margin targets, and merchant brand identity.'
            '</div>',
            unsafe_allow_html=True
        )

        # Category Matrix Table
        st.markdown('<div class="section-header">Category Coverage Matrix across Cohort</div>', unsafe_allow_html=True)
        cat_pivot = df_cat.pivot_table(
            index="category_std",
            columns="brand_id",
            values="category_sku_count",
            fill_value=0
        ).reset_index()

        cat_pivot.columns = ["Category"] + [BRAND_DISPLAY_NAMES.get(c, c) for c in cat_pivot.columns[1:]]
        st.dataframe(cat_pivot, width="stretch", hide_index=True)

        # Visual Category Mix
        st.markdown('<div class="section-header">Standardized Category Mix (% of Active SKUs)</div>', unsafe_allow_html=True)
        chart_cat = build_category_mix_chart(df_cat)
        st.altair_chart(chart_cat, width="stretch")
        st.markdown('<div class="source-caption">Source: Shopify product listings standardized into 8 uniform footwear categories. Elevar Sports maps 90.9% to Casual/Other due to non-specific source tags.</div>', unsafe_allow_html=True)
