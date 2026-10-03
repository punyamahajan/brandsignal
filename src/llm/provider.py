import os
import re
import json
from typing import Dict, Any, List, Optional

from src.orchestrator.context import BrandContext, BrandContextManager
from src.llm.base import LLMProvider, LLMConfigurationError
from src.llm.schemas import LLMPlan, ToolCall, ToolResult, SynthesizedResponse
from src.llm.prompts import SYSTEM_PROMPT, TOOL_PLANNING_PROMPT, EVIDENCE_SYNTHESIS_PROMPT
from src.tools.registry import ToolRegistry

try:
    import dotenv
    dotenv.load_dotenv()
except ImportError:
    pass


class DeterministicHybridProvider(LLMProvider):
    """
    Zero-dependency, deterministic hybrid reasoning and synthesis provider.
    Guarantees 100% operational resilience, zero hallucination, and instant
    sub-millisecond execution when cloud LLM APIs are unavailable.
    Strictly follows non-prescriptive, evidence-grounded rules.
    """

    def plan_tools(
        self,
        query: str,
        context: BrandContext,
        history: Optional[List[Dict[str, str]]] = None
    ) -> LLMPlan:
        cleaned = query.strip()
        cleaned_lower = cleaned.lower()

        # 1. Greetings: hi, hello, hey, help, what can you do
        if re.match(r"^(hi|hello|hey|greetings|good\s+(morning|afternoon|evening))\b", cleaned_lower) and len(cleaned.split()) <= 4:
            return LLMPlan(
                intent="GREETING",
                clarification_needed=True,
                clarification_question="Hi! I'm BrandSignal. Tell me about your brand and what you sell, and I'll help you understand your market."
            )

        if re.search(r"\b(what can you do|how does this work|help|capabilities)\b", cleaned_lower):
            return LLMPlan(
                intent="CAPABILITIES",
                clarification_needed=True,
                clarification_question=(
                    "Hi! I'm BrandSignal. Tell me about your brand and what you sell, and I'll help you understand your market.\n\n"
                    "I analyze public market evidence: catalog scale, pricing architecture, assortment breadth, "
                    "Google Trends search interest, and public creator reviews — without telling you what strategy to follow."
                )
            )

        # 2. Industry / brand statement without specific analytical question
        # e.g. "I run a stationery brand." or "I run a D2C footwear brand."
        if re.search(r"\b(i run|my brand is|we sell|our brand)\b", cleaned_lower) and not re.search(r"\b(what|where|who|compare|vs|how|gap|lacking|trend|search)\b", cleaned_lower):
            if context.industry and "stationery" in context.industry.lower():
                return LLMPlan(
                    intent="INDUSTRY_ONBOARDING",
                    clarification_needed=True,
                    clarification_question="I recognize you operate in the stationery industry. What is your brand name, and what specific products (e.g., notebooks, pens, office supplies) or geography do you focus on?"
                )
            elif context.industry and "footwear" in context.industry.lower():
                if not context.geography:
                    return LLMPlan(
                        intent="INDUSTRY_ONBOARDING",
                        clarification_needed=True,
                        clarification_question="Which market or geography (e.g., India, US, global) does your footwear brand operate in?"
                    )
                else:
                    return LLMPlan(
                        intent="INDUSTRY_ONBOARDING",
                        clarification_needed=True,
                        clarification_question=f"I have established your brand context for {context.industry}. Ask me what is happening in your market, how competitors compare, or where your brand has observable gaps."
                    )
            elif context.industry:
                return LLMPlan(
                    intent="INDUSTRY_ONBOARDING",
                    clarification_needed=True,
                    clarification_question=f"I recognize you operate in {context.industry}. What is your brand name, and which geography do you focus on?"
                )

        tool_calls: List[ToolCall] = []
        target_b = context.demo_brand_id or "baccabucci"

        # 3. Dedicated YouTube research queries
        if re.search(r"\b(youtube|videos?|reviews?|creator content)\b", cleaned_lower):
            yt_query = cleaned
            if context.brand_name:
                yt_query = f"{context.brand_name} {context.industry or ''} reviews"
            elif context.industry:
                yt_query = f"{context.industry} brand reviews"
            tool_calls.append(ToolCall(tool_name="search_youtube", arguments={"query": yt_query, "max_results": 5}))
            return LLMPlan(intent="YOUTUBE_RESEARCH", tool_calls=tool_calls, visual_action="Evidence")

        # 4. Dedicated Web search queries
        if re.search(r"\b(web search|google search|articles|news|online presence)\b", cleaned_lower):
            tool_calls.append(ToolCall(tool_name="search_public_web", arguments={"query": cleaned}))
            return LLMPlan(intent="WEB_RESEARCH", tool_calls=tool_calls, visual_action="Evidence")

        # 5. Market overview queries: "What is happening in my market?"
        if re.search(r"\b(market|overview|happening|trending|category|landscape)\b", cleaned_lower):
            # Check if brand/market context is completely unestablished
            if not context.industry and not context.brand_name and not context.is_demo_vertical:
                return LLMPlan(
                    intent="CLARIFICATION",
                    clarification_needed=True,
                    clarification_question="To tell you what is happening in your market, please tell me about your brand, industry, or category."
                )

            # If demo vertical or footwear
            if context.is_demo_vertical or (context.industry and "footwear" in context.industry.lower()):
                tool_calls.append(ToolCall(tool_name="get_market_snapshot", arguments={"category": "D2C Footwear"}))
                return LLMPlan(intent="MARKET_OVERVIEW", tool_calls=tool_calls, visual_action="Market")
            else:
                # Unsupported industry in warehouse (e.g. stationery) -> run data availability + web research
                tool_calls.append(ToolCall(
                    tool_name="get_data_availability",
                    arguments={"category": context.category or context.industry, "industry": context.industry}
                ))
                tool_calls.append(ToolCall(
                    tool_name="search_public_web",
                    arguments={"query": f"{context.industry} brands market overview"}
                ))
                tool_calls.append(ToolCall(
                    tool_name="search_youtube",
                    arguments={"query": f"{context.industry} brands overview", "max_results": 3}
                ))
                return LLMPlan(intent="MARKET_OVERVIEW", tool_calls=tool_calls, visual_action="Evidence")

        # 6. Gap analysis: "Where is my brand lacking?", "What is my brand missing?"
        elif re.search(r"\b(missing|gaps?|lacking|coverage|absent)\b", cleaned_lower):
            if context.is_demo_vertical or context.demo_brand_id:
                tool_calls.append(ToolCall(tool_name="find_brand_gaps", arguments={"target_brand": target_b}))
                return LLMPlan(intent="GAP_ANALYSIS", tool_calls=tool_calls, visual_action="Gaps")
            elif context.industry and "footwear" not in context.industry.lower():
                tool_calls.append(ToolCall(
                    tool_name="get_data_availability",
                    arguments={"brand_name": context.brand_name, "industry": context.industry}
                ))
                tool_calls.append(ToolCall(
                    tool_name="search_public_web",
                    arguments={"query": f"{context.brand_name or context.industry} market gaps differences"}
                ))
                return LLMPlan(intent="GAP_ANALYSIS", tool_calls=tool_calls, visual_action="Evidence")
            else:
                if not context.brand_name:
                    return LLMPlan(
                        intent="CLARIFICATION",
                        clarification_needed=True,
                        clarification_question="Which brand should I analyze for catalog and assortment gaps?"
                    )
                tool_calls.append(ToolCall(tool_name="find_brand_gaps", arguments={"target_brand": target_b}))
                return LLMPlan(intent="GAP_ANALYSIS", tool_calls=tool_calls, visual_action="Gaps")

        # 7. Competitor comparison
        elif re.search(r"\b(compare|vs|versus|against|differ|different|benchmark)\b", cleaned_lower):
            comp_arg = "neemans"
            if "elevar" in cleaned_lower:
                comp_arg = "elevarsports"
            elif "plaeto" in cleaned_lower:
                comp_arg = "plaeto"
            elif "bacca" in cleaned_lower:
                comp_arg = "baccabucci"

            if target_b == comp_arg:
                target_b = "baccabucci" if comp_arg != "baccabucci" else "neemans"

            if context.is_demo_vertical or (context.industry and "footwear" in context.industry.lower()):
                tool_calls.append(ToolCall(tool_name="compare_brands", arguments={"target_brand": target_b, "comparison_brand": comp_arg}))
                return LLMPlan(intent="COMPETITOR_COMPARISON", tool_calls=tool_calls, visual_action="Competitors")
            else:
                tool_calls.append(ToolCall(tool_name="get_data_availability", arguments={"industry": context.industry}))
                tool_calls.append(ToolCall(tool_name="search_public_web", arguments={"query": query}))
                return LLMPlan(intent="COMPETITOR_COMPARISON", tool_calls=tool_calls, visual_action="Evidence")

        # 8. Pricing comparison
        elif re.search(r"\b(price|prices|pricing|cheaper|expensive|cost|ppi)\b", cleaned_lower):
            tool_calls.append(ToolCall(tool_name="compare_prices", arguments={"target_brand": target_b}))
            return LLMPlan(intent="PRICE_COMPARISON", tool_calls=tool_calls, visual_action="Competitors")

        # 9. Discounting comparison
        elif re.search(r"\b(discount|discounts|markdown|markdowns|promotions?|sale)\b", cleaned_lower):
            tool_calls.append(ToolCall(tool_name="compare_discounting", arguments={"target_brand": target_b}))
            return LLMPlan(intent="DISCOUNT_COMPARISON", tool_calls=tool_calls, visual_action="Competitors")

        # 10. Assortment breadth
        elif re.search(r"\b(styles|skus|assortment|catalog|breadth|variant|variants)\b", cleaned_lower):
            tool_calls.append(ToolCall(tool_name="compare_assortment", arguments={"target_brand": target_b}))
            return LLMPlan(intent="ASSORTMENT_COMPARISON", tool_calls=tool_calls, visual_action="Gaps")

        # 11. Search trends
        elif re.search(r"\b(search|trends?|interest|attention|google)\b", cleaned_lower):
            tool_calls.append(ToolCall(tool_name="get_search_trends", arguments={"brand_id": target_b}))
            return LLMPlan(intent="SEARCH_ANALYSIS", tool_calls=tool_calls, visual_action="Trends")

        # 12. Recent movements
        elif re.search(r"\b(recent|changes?|spikes?|drops?|shifted|moved)\b", cleaned_lower):
            tool_calls.append(ToolCall(tool_name="get_recent_changes", arguments={"min_abs_delta": 5}))
            return LLMPlan(intent="MARKET_CHANGES", tool_calls=tool_calls, visual_action="Trends")

        # 13. Category mix
        elif re.search(r"\b(categories|types|mix)\b", cleaned_lower):
            tool_calls.append(ToolCall(tool_name="get_category_mix", arguments={"brand_id": target_b}))
            return LLMPlan(intent="CATEGORY_MIX", tool_calls=tool_calls, visual_action="Competitors")

        else:
            # Fallback when query is unclassified
            if not context.is_established() and not context.is_demo_vertical:
                clarification = BrandContextManager.get_clarification_question(context)
                if clarification:
                    return LLMPlan(
                        intent="CLARIFICATION",
                        clarification_needed=True,
                        clarification_question=clarification
                    )

            if context.is_demo_vertical:
                tool_calls.append(ToolCall(tool_name="get_market_snapshot", arguments={"category": "D2C Footwear"}))
                return LLMPlan(intent="MARKET_OVERVIEW", tool_calls=tool_calls, visual_action="Market")
            else:
                tool_calls.append(ToolCall(tool_name="search_public_web", arguments={"query": query}))
                return LLMPlan(intent="WEB_RESEARCH", tool_calls=tool_calls, visual_action="Evidence")

    def synthesize_response(
        self,
        query: str,
        context: BrandContext,
        tool_results: List[ToolResult],
        history: Optional[List[Dict[str, str]]] = None
    ) -> SynthesizedResponse:
        cited_ids: List[str] = []
        for tr in tool_results:
            cited_ids.extend(tr.evidence_ids)

        if not tool_results or not any(tr.success for tr in tool_results):
            err_msg = tool_results[0].error if tool_results and tool_results[0].error else "Unable to retrieve empirical data."
            return SynthesizedResponse(
                narrative=f"I was unable to retrieve empirical data for this query: {err_msg}",
                cited_evidence_ids=[],
                suggested_followups=["What data is available?", "Tell me about D2C Footwear demo", "Who is cheaper?"]
            )

        res = tool_results[0]
        data = res.data
        tool_name = res.tool_name

        # 1. get_market_snapshot
        if tool_name == "get_market_snapshot":
            bench = data.get("benchmarks", {})
            brands = data.get("brands", [])
            b_list_str = ", ".join([b["brand_name"] for b in brands])

            narrative = (
                f"### Market Overview: {data.get('category', 'D2C Footwear')}\n\n"
                f"The verified benchmark cohort contains **{bench.get('total_active_products', 0):,} styles** "
                f"and **{bench.get('total_active_skus', 0):,} SKUs** across {len(brands)} active brands (*{b_list_str}*).\n\n"
                f"• **Median Listed Price:** ₹{bench.get('median_price_inr', 0):,.0f} across all listed variants.\n"
                f"• **Promotional Penetration:** Cohort median of {bench.get('median_discount_ratio', 0):.1f}% of catalog listings discounted.\n"
                f"• **Assortment Dispersion:** Active style count ranges from {bench.get('min_products', 0):,} styles to {bench.get('max_products', 0):,} styles."
            )
            return SynthesizedResponse(
                narrative=narrative,
                cited_evidence_ids=cited_ids,
                suggested_followups=["Who has more styles?", "Who is cheaper?", "What is my brand missing?"],
                visual_navigation_target="Market",
                visual_navigation_label="Explore Market Snapshot →"
            )

        # 2. find_brand_gaps
        elif tool_name == "find_brand_gaps":
            t = data.get("target_brand", {})
            missing_cats = data.get("missing_categories", [])
            style_diff = data.get("style_breadth_difference", 0)
            dens_diff = data.get("variant_density_difference", 0.0)
            cat_str = ", ".join(missing_cats) if missing_cats else "None (all major standardized categories represented)"

            narrative = (
                f"### Observable Catalog Differences for {t.get('name', 'Your Brand')}\n\n"
                f"Analyzing public storefront listings reveals the following empirical differences:\n\n"
                f"• **Category Presence:** Categories observed in comparison brands but absent in {t.get('name', 'your')}'s catalog: **{cat_str}**.\n"
                f"• **Assortment Breadth:** Comparison peers list up to **{data.get('max_peer_styles', 0):,} styles**, compared to **{t.get('styles', 0):,} styles** for {t.get('name', 'your brand')} (a difference of {style_diff:,} styles).\n"
                f"• **Option Depth:** Comparison peers offer up to **{dens_diff:+.2f} more SKU variants per style**.\n\n"
                f"> ⚠️ **Methodological Guardrail:** BrandSignal describes observable characteristics in public catalog listings. "
                f"This does **NOT** constitute a strategic recommendation to expand your catalog or launch new categories. "
                f"The business owner decides what strategy to implement based on operational focus."
            )
            return SynthesizedResponse(
                narrative=narrative,
                cited_evidence_ids=cited_ids,
                suggested_followups=["Compare pricing with competitors", "What categories do competitors sell?", "Who discounts the most?"],
                visual_navigation_target="Gaps",
                visual_navigation_label="Explore Gap Explorer →"
            )

        # 3. get_data_availability
        elif tool_name == "get_data_availability":
            available = data.get("available", False)
            market_label = data.get("market") or data.get("category") or "this market"
            if not available:
                # Find if other tools executed in the batch (e.g. web search, youtube)
                web_findings = []
                yt_findings = []
                for tr in tool_results[1:]:
                    if tr.tool_name == "search_public_web" and tr.success:
                        web_findings = tr.evidence_ids
                    elif tr.tool_name == "search_youtube" and tr.success:
                        yt_findings = tr.evidence_ids

                narrative = (
                    f"### Data Availability: {market_label}\n\n"
                    f"BrandSignal does not currently have structured catalog and benchmark datasets in the local analytical warehouse for **{market_label}**.\n\n"
                    f"• **Warehouse Coverage:** Empirical catalog snapshots are currently established for the Indian D2C Footwear benchmark cohort.\n"
                    f"• **Public Research:** BrandSignal initiated public web and video research adapters. "
                    f"Found {len(web_findings)} public knowledge items and {len(yt_findings)} creator review signals.\n\n"
                    f"> ℹ️ *Competitor discovery is not currently available for this market in local tables. BrandSignal does not fabricate unsupported brand comparisons.*"
                )
                return SynthesizedResponse(
                    narrative=narrative,
                    cited_evidence_ids=cited_ids,
                    suggested_followups=["Show verified footwear demo data", "Search YouTube for reviews", "What markets are supported?"],
                    visual_navigation_target="Evidence",
                    visual_navigation_label="View Public Evidence →"
                )
            else:
                return SynthesizedResponse(
                    narrative=f"Structured catalog data is available in the warehouse for **{market_label}** across {len(data.get('brands', []))} brands.",
                    cited_evidence_ids=cited_ids,
                    suggested_followups=["What is happening in my market?", "Compare prices", "Where are the gaps?"],
                    visual_navigation_target="Market",
                    visual_navigation_label="Explore Market →"
                )

        # 4. search_youtube
        elif tool_name == "search_youtube":
            v_count = data.get("video_count", 0)
            q = data.get("query", "")
            narrative = (
                f"### Public Video Content (YouTube)\n\n"
                f"Observed **{v_count} public video results** for query *'{q}'* via official YouTube Data API v3.\n\n"
            )
            for eid in cited_ids[:4]:
                narrative += f"• Recorded public review video signal.\n"
            narrative += (
                f"\n> ⚠️ **Methodological Guardrail:** YouTube content reflects public creator and consumer video uploads. "
                f"It does **NOT** indicate brand sales volume, conversion rates, or market share."
            )
            return SynthesizedResponse(
                narrative=narrative,
                cited_evidence_ids=cited_ids,
                suggested_followups=["Search web articles", "What is happening in my market?", "Compare brands"],
                visual_navigation_target="Evidence",
                visual_navigation_label="Inspect Video Evidence →"
            )

        # 5. search_public_web
        elif tool_name == "search_public_web":
            findings = data.get("findings_count", 0)
            q = data.get("query", "")
            narrative = (
                f"### Public Web Intelligence\n\n"
                f"Retrieved **{findings} public web observations** for query *'{q}'*.\n\n"
                f"Public domain snippets and knowledge references have been indexed into the evidence store without fabrication."
            )
            return SynthesizedResponse(
                narrative=narrative,
                cited_evidence_ids=cited_ids,
                suggested_followups=["Search YouTube reviews", "What data is in warehouse?", "Explore evidence registry"],
                visual_navigation_target="Evidence",
                visual_navigation_label="Explore Evidence Registry →"
            )

        # 6. compare_brands
        elif tool_name == "compare_brands":
            b_a = data.get("brand_a", {})
            b_b = data.get("brand_b", {})
            narrative = (
                f"### Head-to-Head Comparison: {b_a.get('name')} vs {b_b.get('name')}\n\n"
                f"Observable differences from public storefront snapshots and Google Trends:\n\n"
                f"• **Catalog Breadth:** {b_a.get('name')} lists **{b_a.get('styles', 0):,} styles** ({b_a.get('skus', 0):,} SKUs), "
                f"while {b_b.get('name')} lists **{b_b.get('styles', 0):,} styles** ({b_b.get('skus', 0):,} SKUs).\n"
                f"• **Price Positioning:** {b_a.get('name')} has a median listed price of **₹{b_a.get('median_price', 0):,.0f}** (PPI {b_a.get('ppi', 0):.2f}), "
                f"compared to **₹{b_b.get('median_price', 0):,.0f}** (PPI {b_b.get('ppi', 0):.2f}) for {b_b.get('name')}.\n"
                f"• **Promotional Intensity:** {b_a.get('name')} discounts **{b_a.get('discount_ratio', 0):.1f}%** of catalog "
                f"(median markdown {b_a.get('median_discount_depth', 0):.1f}%), versus **{b_b.get('discount_ratio', 0):.1f}%** "
                f"(median markdown {b_b.get('median_discount_depth', 0):.1f}%) for {b_b.get('name')}.\n"
                f"• **Search Attention:** {b_a.get('name')} holds an average cohort relative search share of **{b_a.get('avg_cohort_share', 0):.1f}%**, "
                f"compared to **{b_b.get('avg_cohort_share', 0):.1f}%** for {b_b.get('name')}."
            )
            return SynthesizedResponse(
                narrative=narrative,
                cited_evidence_ids=cited_ids,
                suggested_followups=["Who discounts more?", "Where does my brand have gaps?", "What changed recently?"],
                visual_navigation_target="Competitors",
                visual_navigation_label="Explore Competitor Lens →"
            )

        # 7. compare_prices
        elif tool_name == "compare_prices":
            t = data.get("target", {})
            comps = data.get("comparisons", [])
            narrative = (
                f"### Pricing Architecture Comparison\n\n"
                f"• **Target Brand ({t.get('name')}):** Median listed price is **₹{t.get('median_price', 0):,.0f}** "
                f"(Price Positioning Index: `{t.get('ppi', 0):.2f}` vs cohort median ₹{t.get('cohort_median_price', 0):,.0f}).\n"
                f"• **Price Spread (IQR):** Middle-50% price spread spans ₹{t.get('price_iqr', 0):,.0f}.\n\n"
                f"**Competitor Benchmarks:**\n"
            )
            for c in comps:
                narrative += f"• **{c['brand_name']}:** Median ₹{c['median_price']:,.0f} (PPI `{c['ppi']:.2f}`, IQR ₹{c['price_iqr']:,.0f})\n"

            return SynthesizedResponse(
                narrative=narrative,
                cited_evidence_ids=cited_ids,
                suggested_followups=["Who discounts the most?", "What is my brand missing?", "How does search attention compare?"],
                visual_navigation_target="Competitors",
                visual_navigation_label="Explore Pricing Analysis →"
            )

        # 8. get_search_trends
        elif tool_name == "get_search_trends":
            t = data.get("target_brand", {})
            s = data.get("search_stats", {})
            narrative = (
                f"### 53-Week Search Interest Trajectory: {t.get('name')}\n\n"
                f"• **Mean RSI:** {s.get('mean_rsi', 0.0):.1f} / 100 on Google Trends India Web Search.\n"
                f"• **Annual Peak:** RSI reached {s.get('max_rsi', 0):.0f} during week starting `{s.get('peak_week', 'N/A')}`.\n"
                f"• **Cohort Attention Share:** Averages **{s.get('avg_cohort_share', 0.0):.1f}%** of relative search attention within the cohort.\n\n"
                f"> ℹ️ *Note: Google Trends values reflect normalized search interest [0-100], not absolute search volume or sales.*"
            )
            return SynthesizedResponse(
                narrative=narrative,
                cited_evidence_ids=cited_ids,
                suggested_followups=["Who gets the most search attention?", "Any search spikes recently?", "Compare with competitors"],
                visual_navigation_target="Trends",
                visual_navigation_label="Explore Trend Explorer →"
            )

        # Default tool synthesis
        else:
            return SynthesizedResponse(
                narrative=f"Executed analytical tool `{tool_name}` successfully. Found {len(cited_ids)} verified evidence items.",
                cited_evidence_ids=cited_ids,
                suggested_followups=["What's happening in my market?", "What is my brand missing?", "Who is cheaper?"],
                visual_navigation_target="Evidence",
                visual_navigation_label="Inspect Evidence Explorer →"
            )


class GeminiProvider(LLMProvider):
    """
    Live Google Gemini LLM provider using the google-genai SDK.
    Employs structured output constraints and validates tools against ToolRegistry.
    """

    def __init__(self, api_key: Optional[str] = None, model: str = "gemini-2.5-flash"):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        self.model = model
        self.fallback = DeterministicHybridProvider()

    def plan_tools(
        self,
        query: str,
        context: BrandContext,
        history: Optional[List[Dict[str, str]]] = None
    ) -> LLMPlan:
        if not self.api_key:
            raise LLMConfigurationError("Gemini API key is required but not configured. Set GEMINI_API_KEY in .env.")

        try:
            from google import genai
            from google.genai import types

            client = genai.Client(api_key=self.api_key)
            prompt = (
                f"{TOOL_PLANNING_PROMPT}\n\n"
                f"CURRENT BRAND CONTEXT:\n{context.to_dict()}\n\n"
                f"USER QUERY:\n{query}\n\n"
                f"Respond with a valid JSON object matching the LLMPlan schema:\n"
                f'{{"intent": str, "clarification_needed": bool, "clarification_question": str|null, '
                f'"tool_calls": [{{"tool_name": str, "arguments": dict}}], "visual_action": str|null}}\n'
            )
            response = client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_PROMPT,
                    temperature=0.1,
                    response_mime_type="application/json"
                )
            )
            data = json.loads(response.text)

            # Strict validation against registered tools
            raw_calls = data.get("tool_calls", [])
            valid_calls = []
            for tc in raw_calls:
                t_name = tc.get("tool_name", "")
                if t_name in ToolRegistry.ALL_REGISTERED_TOOLS:
                    valid_calls.append(ToolCall(tool_name=t_name, arguments=tc.get("arguments", {})))

            return LLMPlan(
                intent=data.get("intent", "UNKNOWN"),
                clarification_needed=data.get("clarification_needed", False),
                clarification_question=data.get("clarification_question"),
                tool_calls=valid_calls,
                visual_action=data.get("visual_action")
            )
        except LLMConfigurationError:
            raise
        except Exception:
            # Fall back safely if network/quota issue
            return self.fallback.plan_tools(query, context, history)

    def synthesize_response(
        self,
        query: str,
        context: BrandContext,
        tool_results: List[ToolResult],
        history: Optional[List[Dict[str, str]]] = None
    ) -> SynthesizedResponse:
        if not self.api_key:
            raise LLMConfigurationError("Gemini API key is required but not configured. Set GEMINI_API_KEY in .env.")

        try:
            from google import genai
            from google.genai import types

            client = genai.Client(api_key=self.api_key)
            results_payload = [tr.to_dict() for tr in tool_results]
            available_evid_ids = []
            for tr in tool_results:
                available_evid_ids.extend(tr.evidence_ids)

            prompt = (
                f"{EVIDENCE_SYNTHESIS_PROMPT}\n\n"
                f"USER QUERY:\n{query}\n\n"
                f"BRAND CONTEXT:\n{context.to_dict()}\n\n"
                f"AVAILABLE EVIDENCE IDS:\n{available_evid_ids}\n\n"
                f"EXECUTED TOOL RESULTS (FACTUAL GROUND TRUTH):\n{json.dumps(results_payload, indent=2)}\n\n"
                f"Respond with a valid JSON object matching the SynthesizedResponse schema:\n"
                f'{{"narrative": str, "cited_evidence_ids": [str], "suggested_followups": [str], '
                f'"visual_navigation_target": str|null, "visual_navigation_label": str|null}}\n'
            )
            response = client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_PROMPT,
                    temperature=0.2,
                    response_mime_type="application/json"
                )
            )
            data = json.loads(response.text)
            cited = [cid for cid in data.get("cited_evidence_ids", []) if cid in available_evid_ids]
            if not cited and available_evid_ids:
                cited = available_evid_ids

            # Ensure zero token leakage in narrative
            raw_narrative = data.get("narrative", "")
            clean_narrative = re.sub(r'\[EVID-[^\]]+\]', '', raw_narrative).strip()

            return SynthesizedResponse(
                narrative=clean_narrative,
                cited_evidence_ids=cited,
                suggested_followups=data.get("suggested_followups", []),
                visual_navigation_target=data.get("visual_navigation_target"),
                visual_navigation_label=data.get("visual_navigation_label")
            )
        except LLMConfigurationError:
            raise
        except Exception:
            return self.fallback.synthesize_response(query, context, tool_results, history)


class AnthropicProvider(LLMProvider):
    """
    Live Anthropic Claude LLM provider using the anthropic SDK.
    Enforces non-prescriptive, evidence-grounded synthesis with tool validation.
    """

    def __init__(self, api_key: Optional[str] = None, model: str = "claude-3-5-sonnet-20241022"):
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        self.model = model
        self.fallback = DeterministicHybridProvider()

    def plan_tools(
        self,
        query: str,
        context: BrandContext,
        history: Optional[List[Dict[str, str]]] = None
    ) -> LLMPlan:
        if not self.api_key:
            raise LLMConfigurationError("Anthropic API key is required but not configured. Set ANTHROPIC_API_KEY in .env.")

        try:
            import anthropic
            client = anthropic.Anthropic(api_key=self.api_key)
            prompt = (
                f"{TOOL_PLANNING_PROMPT}\n\n"
                f"CURRENT BRAND CONTEXT:\n{context.to_dict()}\n\n"
                f"USER QUERY:\n{query}\n\n"
                f"Output ONLY a valid JSON object matching the LLMPlan schema:\n"
                f'{{"intent": str, "clarification_needed": bool, "clarification_question": str|null, '
                f'"tool_calls": [{{"tool_name": str, "arguments": dict}}], "visual_action": str|null}}\n'
            )
            message = client.messages.create(
                model=self.model,
                max_tokens=1024,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}]
            )
            raw = message.content[0].text
            if "```json" in raw:
                raw = raw.split("```json")[1].split("```")[0].strip()
            elif "```" in raw:
                raw = raw.split("```")[1].split("```")[0].strip()
            data = json.loads(raw)
            tool_calls = [
                ToolCall(tool_name=tc["tool_name"], arguments=tc.get("arguments", {}))
                for tc in data.get("tool_calls", [])
                if tc.get("tool_name") in ToolRegistry.ALL_REGISTERED_TOOLS
            ]
            return LLMPlan(
                intent=data.get("intent", "UNKNOWN"),
                clarification_needed=data.get("clarification_needed", False),
                clarification_question=data.get("clarification_question"),
                tool_calls=tool_calls,
                visual_action=data.get("visual_action")
            )
        except LLMConfigurationError:
            raise
        except Exception:
            return self.fallback.plan_tools(query, context, history)

    def synthesize_response(
        self,
        query: str,
        context: BrandContext,
        tool_results: List[ToolResult],
        history: Optional[List[Dict[str, str]]] = None
    ) -> SynthesizedResponse:
        if not self.api_key:
            raise LLMConfigurationError("Anthropic API key is required but not configured. Set ANTHROPIC_API_KEY in .env.")

        try:
            import anthropic
            client = anthropic.Anthropic(api_key=self.api_key)
            results_payload = [tr.to_dict() for tr in tool_results]
            available_evid_ids = []
            for tr in tool_results:
                available_evid_ids.extend(tr.evidence_ids)

            prompt = (
                f"{EVIDENCE_SYNTHESIS_PROMPT}\n\n"
                f"USER QUERY:\n{query}\n\n"
                f"BRAND CONTEXT:\n{context.to_dict()}\n\n"
                f"AVAILABLE EVIDENCE IDS:\n{available_evid_ids}\n\n"
                f"EXECUTED TOOL RESULTS:\n{json.dumps(results_payload, indent=2)}\n\n"
                f"Output ONLY a valid JSON object matching the SynthesizedResponse schema:\n"
                f'{{"narrative": str, "cited_evidence_ids": [str], "suggested_followups": [str], '
                f'"visual_navigation_target": str|null, "visual_navigation_label": str|null}}\n'
            )
            message = client.messages.create(
                model=self.model,
                max_tokens=2048,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}]
            )
            raw = message.content[0].text
            if "```json" in raw:
                raw = raw.split("```json")[1].split("```")[0].strip()
            elif "```" in raw:
                raw = raw.split("```")[1].split("```")[0].strip()
            data = json.loads(raw)
            cited = [cid for cid in data.get("cited_evidence_ids", []) if cid in available_evid_ids]

            raw_narrative = data.get("narrative", "")
            clean_narrative = re.sub(r'\[EVID-[^\]]+\]', '', raw_narrative).strip()

            return SynthesizedResponse(
                narrative=clean_narrative,
                cited_evidence_ids=cited or available_evid_ids,
                suggested_followups=data.get("suggested_followups", []),
                visual_navigation_target=data.get("visual_navigation_target"),
                visual_navigation_label=data.get("visual_navigation_label")
            )
        except LLMConfigurationError:
            raise
        except Exception:
            return self.fallback.synthesize_response(query, context, tool_results, history)


def get_llm_provider(require_llm: bool = False) -> LLMProvider:
    """
    Factory function returning the configured LLMProvider.
    Checks for configured API keys (Gemini, Claude) and returns the appropriate provider.
    If require_llm is True (or REQUIRE_LLM_KEY=1) and no key is configured, raises LLMConfigurationError.
    Defaults safely to DeterministicHybridProvider when no external API credentials are provided.
    """
    gemini_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if gemini_key and gemini_key.strip():
        return GeminiProvider(api_key=gemini_key.strip())

    anthropic_key = os.environ.get("ANTHROPIC_API_KEY")
    if anthropic_key and anthropic_key.strip():
        return AnthropicProvider(api_key=anthropic_key.strip())

    if require_llm or os.environ.get("REQUIRE_LLM_KEY") == "1":
        raise LLMConfigurationError("LLM API key is required but not configured. Set GEMINI_API_KEY or ANTHROPIC_API_KEY in .env.")

    return DeterministicHybridProvider()
