import streamlit as st
import pandas as pd
from typing import Dict, Any

from dashboard.data_loader import (
    load_search_demand_series,
    load_search_summary_stats,
    load_search_spikes
)
from dashboard.charts import (
    build_search_trends_chart,
    build_cohort_search_share_chart,
    BRAND_DISPLAY_NAMES
)

def render_trends_view():
    """Renders the Trend Explorer view."""
    st.markdown('<div class="brand-title">Trend Explorer</div>', unsafe_allow_html=True)
    st.markdown('<div class="brand-subtitle">53-week Google Trends search interest trajectories and observed week-over-week fluctuations for Indian D2C footwear.</div>', unsafe_allow_html=True)

    df_search_series = load_search_demand_series()
    df_search_summary = load_search_summary_stats()
    df_search_spikes = load_search_spikes(min_abs_delta=5)

    # Search KPIs
    s_cols = st.columns(4)
    with s_cols[0]:
        st.metric("Observed Weeks", "53 Weeks", "Sep 2025 – Sep 2026")
    with s_cols[1]:
        st.metric("Geography Scope", "India (IN)", "Web Search, All Categories")
    with s_cols[2]:
        st.metric("Index Normalization", "[0 – 100]", "Relative to cohort peak week")
    with s_cols[3]:
        st.metric("Coverage Integrity", "50 Weeks Complete", "3 weeks low-volume (<1)")

    st.markdown("<div style='margin-top:10px;'></div>", unsafe_allow_html=True)

    # 53-Week Trajectory
    st.markdown('<div class="section-header">1. 53-Week Relative Search Interest Trajectory</div>', unsafe_allow_html=True)
    chart_search_trend = build_search_trends_chart(df_search_series)
    st.altair_chart(chart_search_trend, width="stretch")
    st.markdown('<div class="source-caption">Source: Google Trends official export (India, Web Search). Values indexed [0-100]. Low volume (<1) preserved as unquantified breaks rather than zero.</div>', unsafe_allow_html=True)

    # Cohort Relative Search Share
    st.markdown('<div class="section-header">2. Cohort Relative Search Share</div>', unsafe_allow_html=True)
    chart_share = build_cohort_search_share_chart(df_search_series)
    st.altair_chart(chart_share, width="stretch")
    st.markdown(
        '<div style="font-size:0.75rem; color:#1e3a8a; background:#eff6ff; border:1px solid #bfdbfe; padding:6px 10px; border-radius:3px; margin-top:4px;">'
        '<b>Metric Scope:</b> Share of relative search attention within this four-brand cohort; NOT footwear market share. '
        'Calculated across the 50 comparable weeks where all four brands have quantified numeric values.'
        '</div>',
        unsafe_allow_html=True
    )

    # Observed Fluctuations Table
    st.markdown('<div class="section-header">3. Observed Search Movements (|Δ| ≥ 5)</div>', unsafe_allow_html=True)
    st.markdown('<div class="brand-subtitle">Measurable week-over-week fluctuations. Strictly descriptive; BrandSignal does not attribute movements to marketing campaigns or events without primary proof.</div>', unsafe_allow_html=True)

    if not df_search_spikes.empty:
        spike_disp = df_search_spikes.copy()
        spike_disp["brand_name"] = spike_disp["brand_id"].map(BRAND_DISPLAY_NAMES).fillna(spike_disp["brand_id"])

        st.dataframe(
            spike_disp[["brand_name", "week_str", "rsi_change", "prev_rsi", "current_rsi"]].rename(columns={
                "brand_name": "Brand",
                "week_str": "Week Starting",
                "rsi_change": "RSI Change (WoW Δ)",
                "prev_rsi": "Previous Week RSI",
                "current_rsi": "Current Week RSI"
            }).style.format({
                "RSI Change (WoW Δ)": "{:+d}",
                "Previous Week RSI": "{:.0f}",
                "Current Week RSI": "{:.0f}"
            }),
            width="stretch",
            hide_index=True
        )
    else:
        st.caption("No search fluctuations exceeding threshold (|Δ| ≥ 5) observed.")
