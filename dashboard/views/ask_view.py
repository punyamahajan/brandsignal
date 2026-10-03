import streamlit as st
import pandas as pd
from typing import Dict, Any, List, Optional

from src.orchestrator.service import ConversationalOrchestrator, OrchestratorResponse
from src.orchestrator.context import BrandContext

SUGGESTED_CHIPS = [
    "What is happening in my market?",
    "How does my brand compare with Neeman's?",
    "What is my brand missing?",
    "Who is cheaper?",
    "What changed recently?"
]

def render_ask_view(snapshot_date: str = "2026-09-29"):
    """
    Renders the Ask BrandSignal conversational market intelligence view.
    Grounded strictly in verified DuckDB records and primary research evidence.
    """
    # Initialize orchestrator in session state
    if "orchestrator" not in st.session_state:
        st.session_state["orchestrator"] = ConversationalOrchestrator()

    if "chat_turns" not in st.session_state:
        st.session_state["chat_turns"] = []

    orch: ConversationalOrchestrator = st.session_state["orchestrator"]

    # Header
    st.markdown('<div class="brand-title">Ask BrandSignal</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="brand-subtitle">'
        'Conversational market and competitive intelligence. '
        'Understand your market, discover competitors, identify observable gaps, and inspect verified primary evidence.'
        '</div>',
        unsafe_allow_html=True
    )

    # Active Brand Context Badge
    ctx: BrandContext = orch.context
    ctx_summary = ctx.summary() if ctx.is_established() else "No brand context established. Tell BrandSignal about your brand below."
    st.markdown(
        f'<div style="background:#ffffff; border:1px solid #cbd5e1; border-radius:4px; padding:8px 12px; margin-bottom:12px; font-size:0.80rem; color:#334155;">'
        f'<b>Active Brand Context:</b> {ctx_summary}'
        f'</div>',
        unsafe_allow_html=True
    )

    # Prompt Chips
    st.markdown("<div style='font-size:0.75rem; font-weight:700; color:#64748b; text-transform:uppercase; margin-bottom:4px;'>Suggested Inquiries</div>", unsafe_allow_html=True)
    chip_cols = st.columns(len(SUGGESTED_CHIPS))
    clicked_chip = None
    for i, chip_text in enumerate(SUGGESTED_CHIPS):
        with chip_cols[i]:
            if st.button(chip_text, key=f"chip_{i}", help=f"Ask: '{chip_text}'"):
                clicked_chip = chip_text

    # Conversation History & Empty State
    if not st.session_state["chat_turns"]:
        st.markdown("""
        <div style="background:#ffffff; border:1px solid #e2e8f0; border-radius:4px; padding:16px; margin-top:10px; margin-bottom:14px;">
            <div style="font-weight:700; color:#0f172a; margin-bottom:4px; font-size:0.95rem;">
                Evidence-Grounded Market Intelligence
            </div>
            <div style="font-size:0.82rem; color:#475569; margin-bottom:10px;">
                Ask questions regarding competitive positioning, pricing landscape, catalog differences, and search momentum.
                Every finding is backed by auditable evidence items.
            </div>
            <div style="font-size:0.78rem; color:#64748b;">
                • <b>Market:</b> <i>"What is happening in my market?"</i><br/>
                • <b>Competitors:</b> <i>"How does my brand compare with Neeman's?"</i><br/>
                • <b>Gaps:</b> <i>"What is my brand missing?"</i><br/>
                • <b>Pricing:</b> <i>"Who is cheaper?"</i><br/>
                • <b>Trends:</b> <i>"What changed recently in search?"</i>
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        for idx, turn in enumerate(st.session_state["chat_turns"]):
            user_msg = turn["query"]
            resp: OrchestratorResponse = turn["response"]

            with st.chat_message("user"):
                st.write(user_msg)

            with st.chat_message("assistant"):
                st.markdown(resp.narrative)

                # "Why are you saying this?" Provenance Drawer
                if resp.why_are_you_saying_this_md:
                    with st.expander("📑 Why are you saying this? (Source Provenance & Citations)"):
                        st.markdown(resp.why_are_you_saying_this_md)

                # Visual Analytics Deep Link Action
                if resp.visual_navigation_target:
                    tab_map = {
                        "Market": "📊 Market",
                        "Competitors": "⚖️ Competitors",
                        "Gaps": "🔍 Gaps",
                        "Trends": "📈 Trends",
                        "Evidence": "📑 Evidence"
                    }
                    target_tab = tab_map.get(resp.visual_navigation_target, resp.visual_navigation_target)
                    label = resp.visual_navigation_label or f"Explore in {target_tab} →"

                    def _nav_to(tab_name):
                        st.session_state["nav_selection"] = tab_name

                    st.button(
                        label,
                        key=f"deep_link_{idx}",
                        on_click=_nav_to,
                        args=(target_tab,),
                        help=f"Navigate directly to {target_tab} tab with current brand context preserved."
                    )

                # Follow-up chips
                if resp.suggested_followups:
                    st.markdown("<div style='font-size:0.72rem; font-weight:700; color:#64748b; text-transform:uppercase; margin-top:8px;'>Follow-Up Inquiries</div>", unsafe_allow_html=True)
                    f_cols = st.columns(len(resp.suggested_followups))
                    for f_i, f_q in enumerate(resp.suggested_followups):
                        with f_cols[f_i]:
                            if st.button(f_q, key=f"fup_{idx}_{f_i}"):
                                clicked_chip = f_q

    # Input handling
    user_input = st.chat_input("Ask a market, competitor, pricing, or gap question...")
    query_to_run = clicked_chip or user_input

    if query_to_run:
        resp = orch.process_turn(query_to_run)
        st.session_state["chat_turns"].append({
            "query": query_to_run,
            "response": resp
        })
        st.rerun()

    # Footer Guardrail
    st.markdown("<div style='margin-top:16px;'></div>", unsafe_allow_html=True)
    st.markdown(
        '<div style="font-size:0.72rem; color:#64748b; background:#f8fafc; border:1px solid #e2e8f0; border-radius:3px; padding:6px 10px;">'
        '<b>Methodological Standard:</b> BrandSignal describes observable facts and measurable comparisons in public market data. '
        'It does not generate speculative business advice or causal claims. "Understand the market. See the gap. Make the call."'
        '</div>',
        unsafe_allow_html=True
    )
