import streamlit as st
import pandas as pd
from typing import Dict, Any, List, Optional

from src.conversation.query_planner import QueryPlanner
from src.conversation.response_generator import ResponseGenerator, ChatResponse
from src.conversation.entity_resolver import CANONICAL_BRANDS

# Suggested prompt chips requested by specification
SUGGESTED_PROMPT_CHIPS = [
    "What's happening in my market?",
    "How does my brand compare with Neeman's?",
    "What is my brand missing?",
    "Who is cheaper?",
    "What changed recently?"
]

TAB_NAV_MAP = {
    1: "📊 Market Snapshot",
    2: "⚖️ Competitive Comparison",
    3: "📈 Search Attention"
}

BRAND_DISPLAY_OPTIONS = {
    "Bacca Bucci (Mass / High Breadth)": "baccabucci",
    "Neeman's (Mid-Tier / Sustainable)": "neemans",
    "Elevar Sports (Premium / Athletic)": "elevarsports",
    "Plaeto (Youth / Value Footwear)": "plaeto"
}

def render_ask_brandsignal(snapshot_date: str = "2026-09-29"):
    """
    Renders the Conversational Competitive Analytics front door.
    Purely deterministic, zero-LLM natural language query interface
    backed by DuckDB feature store and Google Trends series.
    """
    # Initialize session state for chat
    if "chat_messages" not in st.session_state:
        st.session_state["chat_messages"] = []

    if "active_brand_context" not in st.session_state:
        st.session_state["active_brand_context"] = "baccabucci"

    # Top Brand Context & Control Bar
    st.markdown('<div class="section-header">Ask BrandSignal — Conversational Intelligence</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="brand-subtitle">'
        'Ask plain-language questions about catalog scale, pricing architecture, markdown depth, and search interest. '
        'All responses are computed deterministically from verified DuckDB records without generative AI hallucination.'
        '</div>',
        unsafe_allow_html=True
    )

    ctrl_col1, ctrl_col2, ctrl_col3 = st.columns([3, 4, 2])
    with ctrl_col1:
        # Determine current index
        current_id = st.session_state["active_brand_context"]
        option_keys = list(BRAND_DISPLAY_OPTIONS.keys())
        default_idx = 0
        for i, (label, b_id) in enumerate(BRAND_DISPLAY_OPTIONS.items()):
            if b_id == current_id:
                default_idx = i
                break

        selected_label = st.selectbox(
            "Your Brand Perspective",
            options=option_keys,
            index=default_idx,
            key="chat_brand_selector",
            help="Designates which brand 'my brand' or 'we' refers to during comparative queries."
        )
        st.session_state["active_brand_context"] = BRAND_DISPLAY_OPTIONS[selected_label]

    with ctrl_col2:
        st.markdown("<div style='margin-top:24px;'></div>", unsafe_allow_html=True)
        st.markdown(
            f'<span class="meta-tag">Storefront Snapshot: {snapshot_date}</span>'
            f'<span class="meta-tag">Search: 53-Wk Series</span>'
            f'<span class="meta-tag">Engine: Zero-LLM Deterministic</span>',
            unsafe_allow_html=True
        )

    with ctrl_col3:
        st.markdown("<div style='margin-top:24px;'></div>", unsafe_allow_html=True)
        if st.button("🔄 Clear Conversation", key="clear_chat_btn"):
            st.session_state["chat_messages"] = []
            st.rerun()

    st.markdown("<div style='margin-bottom:12px;'></div>", unsafe_allow_html=True)

    # Prompt Chips Row
    st.markdown("<div style='font-size:0.78rem; font-weight:700; color:#64748b; text-transform:uppercase; margin-bottom:6px;'>Suggested Inquiries</div>", unsafe_allow_html=True)
    chip_cols = st.columns(len(SUGGESTED_PROMPT_CHIPS))
    clicked_chip = None
    for i, chip_text in enumerate(SUGGESTED_PROMPT_CHIPS):
        with chip_cols[i]:
            if st.button(chip_text, key=f"chip_{i}", help=f"Ask: '{chip_text}'"):
                clicked_chip = chip_text

    # Conversation History & Empty State
    if not st.session_state["chat_messages"]:
        st.markdown("""
        <div style="background:#ffffff; border:1px solid #e2e8f0; border-radius:6px; padding:20px; margin-top:16px;">
            <div style="font-size:1.05rem; font-weight:700; color:#0f172a; margin-bottom:6px;">
                Welcome to BrandSignal Conversational Analytics
            </div>
            <div style="font-size:0.86rem; color:#475569; line-height:1.5; margin-bottom:14px;">
                Ask questions regarding competitive positioning, pricing landscape, catalog differences, and search momentum.
                BrandSignal maps each question to parameter-safe SQL queries over our verified DuckDB data repository.
            </div>
            <div style="display:grid; grid-template-columns: 1fr 1fr; gap:12px; font-size:0.82rem; color:#334155;">
                <div style="background:#f8fafc; border:1px solid #e2e8f0; padding:10px 14px; border-radius:4px;">
                    <b>📊 Market Landscape & Trends:</b><br/>
                    • <i>"What is happening in my market?"</i><br/>
                    • <i>"What is trending right now?"</i><br/>
                    • <i>"What data is available?"</i>
                </div>
                <div style="background:#f8fafc; border:1px solid #e2e8f0; padding:10px 14px; border-radius:4px;">
                    <b>⚖️ Head-to-Head & Assortment Gaps:</b><br/>
                    • <i>"How does my brand compare with Neeman's?"</i><br/>
                    • <i>"What is my brand missing?"</i><br/>
                    • <i>"Where is my brand different from the other brands?"</i>
                </div>
                <div style="background:#f8fafc; border:1px solid #e2e8f0; padding:10px 14px; border-radius:4px;">
                    <b>🏷️ Pricing & Promotional Intensity:</b><br/>
                    • <i>"Who is cheaper?"</i><br/>
                    • <i>"Who discounts the most?"</i><br/>
                    • <i>"What is my price positioning index?"</i>
                </div>
                <div style="background:#f8fafc; border:1px solid #e2e8f0; padding:10px 14px; border-radius:4px;">
                    <b>📈 Search Momentum & Spikes:</b><br/>
                    • <i>"What changed recently?"</i><br/>
                    • <i>"Who leads in search attention?"</i><br/>
                    • <i>"What happened to search interest?"</i>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        # Render Chat History
        for msg_idx, msg in enumerate(st.session_state["chat_messages"]):
            if msg["role"] == "user":
                with st.chat_message("user"):
                    st.write(msg["content"])
            elif msg["role"] == "assistant":
                resp: ChatResponse = msg["response"]
                with st.chat_message("assistant"):
                    # Render Main Narrative
                    st.markdown(resp.text)

                    # Render Evidence Table (if present)
                    if resp.evidence_table is not None and not resp.evidence_table.empty:
                        st.markdown("<div style='margin-top:8px;'></div>", unsafe_allow_html=True)
                        st.dataframe(resp.evidence_table, width="stretch", hide_index=True)

                    # Deep Link Exploration Button
                    if resp.explore_tab and resp.explore_tab in TAB_NAV_MAP:
                        target_tab = TAB_NAV_MAP[resp.explore_tab]
                        btn_label = resp.explore_label or f"Explore in {target_tab} →"
                        
                        def _navigate_to(view_name):
                            st.session_state["nav_selection"] = view_name

                        st.button(
                            btn_label,
                            key=f"explore_btn_{msg_idx}",
                            on_click=_navigate_to,
                            args=(target_tab,),
                            help=f"Navigate directly to {target_tab} to view full charts and tables."
                        )

                    # Render Suggested Follow-Up Prompt Chips
                    if resp.suggested_followups:
                        st.markdown("<div style='font-size:0.75rem; font-weight:700; color:#64748b; text-transform:uppercase; margin-top:12px; margin-bottom:4px;'>Suggested Follow-Ups</div>", unsafe_allow_html=True)
                        f_cols = st.columns(len(resp.suggested_followups))
                        for f_idx, followup_q in enumerate(resp.suggested_followups):
                            with f_cols[f_idx]:
                                if st.button(followup_q, key=f"followup_{msg_idx}_{f_idx}"):
                                    clicked_chip = followup_q

    # Handle Input from Chat or Prompt Chips
    user_query = st.chat_input("Ask BrandSignal a competitive analytics question...")
    query_to_execute = clicked_chip or user_query

    if query_to_execute:
        # Append User Message
        st.session_state["chat_messages"].append({
            "role": "user",
            "content": query_to_execute
        })

        # Execute Plan
        planner = QueryPlanner()
        exec_res = planner.execute(
            query=query_to_execute,
            active_brand_id=st.session_state["active_brand_context"],
            snapshot_date=snapshot_date
        )

        # Generate Evidence-Based Response
        assistant_resp = ResponseGenerator.generate(exec_res)

        # Append Assistant Message
        st.session_state["chat_messages"].append({
            "role": "assistant",
            "response": assistant_resp
        })

        st.rerun()

    # Guardrail Callout
    st.markdown("<div style='margin-top:20px;'></div>", unsafe_allow_html=True)
    st.markdown("""
    <div style="font-size:0.75rem; color:#475569; background:#f1f5f9; border:1px solid #cbd5e1; border-radius:4px; padding:8px 12px;">
        <b>Conversational Guardrail:</b> BrandSignal uses a deterministic rule-based query parser and analytical templates. 
        It does not query unverified LLMs, make causal assertions, predict revenue, or formulate strategic business advice.
    </div>
    """, unsafe_allow_html=True)
