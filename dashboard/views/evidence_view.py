import streamlit as st
import pandas as pd
from typing import Dict, Any, List

from src.evidence.models import EvidenceStore, EvidenceItem

def render_evidence_view():
    """
    Renders the Evidence Explorer view.
    Provides complete transparency, provenance audits, and primary citations for every market observation.
    """
    st.markdown('<div class="brand-title">Evidence Explorer</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="brand-subtitle">'
        'Audit trail of verified primary data sources and empirical observations recorded during analytical execution. '
        '"Why are you saying this?" provenance repository.'
        '</div>',
        unsafe_allow_html=True
    )

    # Retrieve evidence items from session orchestrator
    evidence_items: List[EvidenceItem] = []
    if "orchestrator" in st.session_state:
        evidence_items = st.session_state["orchestrator"].evidence_store.get_all()

    # Pre-seed with default verified cohort evidence if empty
    if not evidence_items:
        from src.tools.analytics_tools import AnalyticsToolsEngine
        engine = AnalyticsToolsEngine()
        _, snap_ev = engine.get_market_snapshot()
        evidence_items = snap_ev

    # Filters
    f_c1, f_c2 = st.columns(2)
    with f_c1:
        sources = ["All Sources"] + sorted(list(set(e.source_name for e in evidence_items)))
        sel_source = st.selectbox("Filter by Source", sources)
    with f_c2:
        brands = ["All Brands"] + sorted(list(set(e.brand_name for e in evidence_items)))
        sel_brand = st.selectbox("Filter by Brand", brands)

    filtered = evidence_items
    if sel_source != "All Sources":
        filtered = [e for e in filtered if e.source_name == sel_source]
    if sel_brand != "All Brands":
        filtered = [e for e in filtered if e.brand_name == sel_brand]

    st.markdown(f"**Showing {len(filtered)} verified evidence item(s):**")
    st.markdown("<div style='margin-bottom:10px;'></div>", unsafe_allow_html=True)

    # Render Evidence Cards
    for item in filtered:
        url_snippet = f" | [Direct Link]({item.source_url})" if item.source_url else ""
        raw_snippet = f" | Raw: `{item.raw_reference}`" if item.raw_reference else ""
        lim_box = (
            f'<div style="font-size:0.75rem; color:#b45309; background:#fffbeb; border:1px solid #fef3c7; padding:6px 10px; border-radius:3px; margin-top:6px;">'
            f'<b>Data Limitation:</b> {item.limitation_note}'
            f'</div>'
            if item.limitation_note else ""
        )

        st.markdown(f"""
        <div style="background:#ffffff; border:1px solid #e2e8f0; border-radius:4px; padding:12px 16px; margin-bottom:12px;">
            <div style="display:flex; justify-content:space-between; margin-bottom:4px;">
                <span style="font-weight:700; color:#0f172a; font-size:0.88rem;">{item.brand_name} — {item.metric}</span>
                <span style="font-family:monospace; font-size:0.75rem; color:#64748b; background:#f1f5f9; padding:2px 6px; border-radius:3px;">{item.evidence_id}</span>
            </div>
            <div style="font-size:0.82rem; color:#334155; margin-bottom:6px;">
                <b>Observation:</b> {item.observation}
            </div>
            <div style="font-size:0.75rem; color:#64748b;">
                Source: <b>{item.source_name}</b> ({item.source_type}) | Collected: <code>{item.collected_at[:10]}</code>{url_snippet}{raw_snippet}
            </div>
            {lim_box}
        </div>
        """, unsafe_allow_html=True)

    # Table view option
    with st.expander("View Evidence Audit Table (Structured Data)"):
        table_rows = [e.to_dict() for e in filtered]
        if table_rows:
            df_table = pd.DataFrame(table_rows)[[
                "evidence_id", "brand_name", "metric", "source_name", "source_type", "collected_at", "confidence"
            ]]
            st.dataframe(df_table, width="stretch", hide_index=True)
