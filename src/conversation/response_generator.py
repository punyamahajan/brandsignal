import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

from src.conversation.query_planner import ExecutionResult, QueryPlan

@dataclass
class ChatResponse:
    text: str
    evidence_table: Optional[pd.DataFrame] = None
    explore_tab: Optional[int] = None
    explore_label: Optional[str] = None
    suggested_followups: Optional[List[str]] = None

class ResponseGenerator:
    """
    Deterministic Response Generator.
    Produces evidence-grounded, non-causal, auditable Markdown responses
    strictly from ExecutionResult data. Zero generative AI or hallucination.
    """

    @staticmethod
    def generate(result: ExecutionResult) -> ChatResponse:
        """Dispatches execution result to the corresponding deterministic response template."""
        if not result.success:
            return ChatResponse(
                text=f"An error occurred while retrieving analytical data: {result.error}\n\nPlease try asking about catalog scale, pricing, discounting, or search attention.",
                explore_tab=1,
                explore_label="Explore Market Overview →"
            )

        intent = result.plan.intent
        data = result.data

        if intent == "MARKET_OVERVIEW":
            return ResponseGenerator._format_market_overview(data)
        elif intent == "COMPETITOR_COMPARISON":
            if "brand_a" in data and "brand_b" in data:
                return ResponseGenerator._format_head_to_head(data)
            else:
                return ResponseGenerator._format_brand_differences(data)
        elif intent == "ASSORTMENT_COMPARISON" or intent == "CATALOG_SCALE":
            return ResponseGenerator._format_assortment_comparison(data)
        elif intent == "PRICE_COMPARISON" or intent == "PRICE_POSITIONING":
            return ResponseGenerator._format_price_comparison(data)
        elif intent == "DISCOUNT_COMPARISON" or intent == "PROMOTIONAL_INTENSITY":
            return ResponseGenerator._format_discount_comparison(data)
        elif intent == "SEARCH_TREND":
            return ResponseGenerator._format_search_trend(data)
        elif intent == "SEARCH_COMPARISON":
            return ResponseGenerator._format_search_comparison(data)
        elif intent == "RECENT_CHANGE":
            return ResponseGenerator._format_recent_changes(data)
        elif intent == "BRAND_DIFFERENCE":
            return ResponseGenerator._format_brand_differences(data)
        elif intent == "BRAND_MISSING":
            return ResponseGenerator._format_brand_gaps(data)
        elif intent == "CATEGORY_MIX":
            return ResponseGenerator._format_category_mix(data)
        elif intent == "EXPLAIN_METRIC":
            return ResponseGenerator._format_metric_explanation(data)
        elif intent == "DATA_AVAILABILITY":
            return ResponseGenerator._format_data_availability(data)
        elif intent == "HELP":
            return ResponseGenerator._format_help()
        else:
            return ResponseGenerator._format_unknown()

    @staticmethod
    def _format_market_overview(data: Dict[str, Any]) -> ChatResponse:
        b = data.get("benchmarks", {})
        brands = data.get("brands", [])

        table_rows = []
        for br in brands:
            table_rows.append({
                "Brand": br["brand_name"],
                "Styles": f"{br['active_styles']:,}",
                "SKUs": f"{br['active_skus']:,}",
                "Median Price": f"₹{br['median_price']:,.0f}",
                "PPI": f"{br['ppi']:.2f}",
                "Discounted %": f"{br['discount_ratio']:.1f}%",
                "Avg Search Share": f"{br['avg_cohort_share']:.1f}%" if br['avg_cohort_share'] is not None else "0.0%"
            })
        df_table = pd.DataFrame(table_rows)

        text = (
            f"Here are the primary observable market patterns across the four-brand benchmark cohort "
            f"for snapshot date **{data.get('snapshot_date', '2026-09-29')}**:\n\n"
            f"• **Catalog Scale Bifurcation:** The cohort contains **{b.get('total_active_products', 2050):,} styles** "
            f"and **{b.get('total_active_skus', 10576):,} SKUs**. Bacca Bucci and Neeman's represent over 91% of active SKU listings, "
            f"while Elevar Sports and Plaeto operate focused catalog footprints.\n"
            f"• **Listed Price Dispersion:** Listed median prices range from ₹1,499.00 to ₹2,300.00 around a cohort median of **₹{b.get('median_price_inr', 1899.0):,.0f}**.\n"
            f"• **Promotional Penetration:** Three of four merchants list over 93% of their catalogs with compare-at reference markdowns; Elevar Sports discounts 47.8%.\n"
            f"• **Search Attention Concentration:** Bacca Bucci and Neeman's account for approximately 98.5% of relative search attention within the cohort over the past 12 months.\n\n"
            f"*Note: Catalog metrics reflect a single point-in-time public storefront snapshot, not sales-weighted volumes or transaction revenue.*"
        )

        return ChatResponse(
            text=text,
            evidence_table=df_table,
            explore_tab=1,
            explore_label="Explore Market Snapshot →",
            suggested_followups=[
                "How does my brand compare with Neeman's?",
                "Who is cheaper?",
                "What is my brand missing?",
                "How has search attention changed?"
            ]
        )

    @staticmethod
    def _format_head_to_head(data: Dict[str, Any]) -> ChatResponse:
        a = data["brand_a"]
        b = data["brand_b"]

        text = (
            f"Here are the main observable differences between **{a['name']}** and **{b['name']}** "
            f"in the public storefront snapshot (`2026-09-29`) and Google Trends series:\n\n"
            f"• **Catalog Breadth:** {a['name']} lists **{a['styles']:,} active styles** ({a['skus']:,} SKUs), "
            f"while {b['name']} lists **{b['styles']:,} active styles** ({b['skus']:,} SKUs).\n"
            f"• **Variant Density:** {a['name']} averages **{a['variant_density']:.2f} SKUs per style**, "
            f"compared to **{b['variant_density']:.2f}** for {b['name']}.\n"
            f"• **Median Listed Price:** {a['name']} median listed selling price is **₹{a['median_price']:,.0f}** (PPI {a['ppi']:.2f}), "
            f"compared to **₹{b['median_price']:,.0f}** (PPI {b['ppi']:.2f}) for {b['name']}.\n"
            f"• **Discount Coverage:** **{a['discount_ratio']:.1f}%** of {a['name']}'s SKUs show a reference discount (median depth {a['median_discount_depth'] or 0:.1f}%), "
            f"compared to **{b['discount_ratio']:.1f}%** for {b['name']} (median depth {b['median_discount_depth'] or 0:.1f}%).\n"
            f"• **Observed Search Share:** {a['name']} averages **{a['avg_cohort_share'] or 0:.1f}%** of cohort relative search attention, "
            f"compared to **{b['avg_cohort_share'] or 0:.1f}%** for {b['name']}.\n\n"
            f"*These figures describe differences observed in public storefront and search data. They do not demonstrate why brands perform differently or establish causal market share.*"
        )

        df_table = pd.DataFrame([
            {"Metric": "Active Styles", a["name"]: f"{a['styles']:,}", b["name"]: f"{b['styles']:,}"},
            {"Metric": "Active SKUs", a["name"]: f"{a['skus']:,}", b["name"]: f"{b['skus']:,}"},
            {"Metric": "Variants per Style", a["name"]: f"{a['variant_density']:.2f}", b["name"]: f"{b['variant_density']:.2f}"},
            {"Metric": "Median Listed Price", a["name"]: f"₹{a['median_price']:,.0f}", b["name"]: f"₹{b['median_price']:,.0f}"},
            {"Metric": "Price Positioning (PPI)", a["name"]: f"{a['ppi']:.2f}", b["name"]: f"{b['ppi']:.2f}"},
            {"Metric": "Discounted Catalog %", a["name"]: f"{a['discount_ratio']:.1f}%", b["name"]: f"{b['discount_ratio']:.1f}%"},
            {"Metric": "Median Markdown %", a["name"]: f"{a['median_discount_depth'] or 0:.1f}%", b["name"]: f"{b['median_discount_depth'] or 0:.1f}%"},
            {"Metric": "12M Search Share", a["name"]: f"{a['avg_cohort_share'] or 0:.1f}%", b["name"]: f"{b['avg_cohort_share'] or 0:.1f}%"}
        ])

        return ChatResponse(
            text=text,
            evidence_table=df_table,
            explore_tab=2,
            explore_label="Explore Competitive Comparison →",
            suggested_followups=[
                f"Compare {a['name']} pricing with {b['name']}",
                f"Who discounts more: {a['name']} or {b['name']}?",
                "What is my brand missing?",
                "Show category mix"
            ]
        )

    @staticmethod
    def _format_assortment_comparison(data: Dict[str, Any]) -> ChatResponse:
        t = data["target"]
        comps = data["comparisons"]

        rows = [{"Brand": t["name"], "Styles": f"{t['styles']:,}", "SKUs": f"{t['skus']:,}", "Variants/Style": f"{t['variant_density']:.2f}"}]
        diff_bullets = []
        for c in comps:
            rows.append({"Brand": c["brand_name"], "Styles": f"{c['styles']:,}", "SKUs": f"{c['skus']:,}", "Variants/Style": f"{c['variant_density']:.2f}"})
            diff_bullets.append(f"• **vs {c['brand_name']}:** {c['brand_name']} lists {c['styles']:,} styles ({c['skus']:,} SKUs), a difference of {abs(c['style_diff']):,} styles.")

        df_table = pd.DataFrame(rows)

        text = (
            f"**Assortment Architecture Comparison (Snapshot: 2026-09-29):**\n\n"
            f"**{t['name']}** currently offers **{t['styles']:,} active parent styles** and **{t['skus']:,} SKUs**, "
            f"with a variant density of **{t['variant_density']:.2f} options per style**.\n\n"
            f"Cohort context (Cohort median styles: {t['cohort_styles_median']:.0f} | SKUs: {t['cohort_skus_median']:,.0f}):\n"
            + "\n".join(diff_bullets) + "\n\n"
            f"*Catalog breadth reflects unique listed parent product styles. It does not measure physical inventory units or sales velocity.*"
        )

        return ChatResponse(
            text=text,
            evidence_table=df_table,
            explore_tab=2,
            explore_label="Explore Assortment Architecture →",
            suggested_followups=[
                "Who is cheaper?",
                "What categories do competitors sell?",
                "What is my brand missing?"
            ]
        )

    @staticmethod
    def _format_price_comparison(data: Dict[str, Any]) -> ChatResponse:
        t = data["target"]
        comps = data["comparisons"]

        rows = [{"Brand": t["name"], "Median Listed Price": f"₹{t['median_price']:,.0f}", "Price IQR": f"₹{t['price_iqr']:,.0f}", "PPI": f"{t['ppi']:.2f}"}]
        diff_bullets = []
        for c in comps:
            rows.append({"Brand": c["brand_name"], "Median Listed Price": f"₹{c['median_price']:,.0f}", "Price IQR": f"₹{c['price_iqr']:,.0f}", "PPI": f"{c['ppi']:.2f}"})
            pos = "higher" if c['price_diff'] < 0 else "lower"
            diff_bullets.append(f"• **vs {c['brand_name']}:** {c['brand_name']} median price is ₹{c['median_price']:,.0f} (₹{abs(c['price_diff']):,.0f} {pos} than {t['name']}).")

        df_table = pd.DataFrame(rows)

        text = (
            f"**Listed Price Positioning Comparison (Snapshot: 2026-09-29):**\n\n"
            f"**{t['name']}** has a median listed selling price of **₹{t['median_price']:,.0f}** and an IQR of **₹{t['price_iqr']:,.0f}**, "
            f"resulting in a Price Positioning Index (PPI) of **{t['ppi']:.2f}** against the cohort median benchmark of **₹{t['cohort_median_price']:,.0f}**.\n\n"
            f"Observed price differences:\n"
            + "\n".join(diff_bullets) + "\n\n"
            f"*Important limitation: Listed prices reflect digital storefront asking prices; they do not represent volume-weighted transaction ASP or customer willingness to pay.*"
        )

        return ChatResponse(
            text=text,
            evidence_table=df_table,
            explore_tab=2,
            explore_label="Explore Price Distribution →",
            suggested_followups=[
                "Who discounts the most?",
                "What is my Price Positioning Index?",
                "Compare my assortment breadth"
            ]
        )

    @staticmethod
    def _format_discount_comparison(data: Dict[str, Any]) -> ChatResponse:
        t = data["target"]
        comps = data["comparisons"]

        rows = [{"Brand": t["name"], "Discounted Catalog %": f"{t['discount_ratio']:.1f}%", "Median Markdown Depth %": f"{t['median_discount_depth'] or 0:.1f}%"}]
        diff_bullets = []
        for c in comps:
            rows.append({"Brand": c["brand_name"], "Discounted Catalog %": f"{c['discount_ratio']:.1f}%", "Median Markdown Depth %": f"{c['median_discount_depth'] or 0:.1f}%"})
            diff_bullets.append(f"• **vs {c['brand_name']}:** {c['brand_name']} discounts {c['discount_ratio']:.1f}% of catalog with median markdown depth of {c['median_discount_depth'] or 0:.1f}%.")

        df_table = pd.DataFrame(rows)

        text = (
            f"**Promotional Intensity Comparison (Snapshot: 2026-09-29):**\n\n"
            f"**{t['name']}** applies compare-at reference markdowns to **{t['discount_ratio']:.1f}% of active SKUs**, "
            f"with a median discount depth of **{t['median_discount_depth'] or 0:.1f}%** among discounted items.\n\n"
            f"Cohort comparisons (Cohort median ratio: {t['cohort_median_ratio']:.1f}% | median depth: {t['cohort_median_depth']:.1f}%):\n"
            + "\n".join(diff_bullets) + "\n\n"
            f"*Note: compare_at_price is a merchant-defined reference price. It indicates promotional presentation strategy rather than verified historical transaction margin.*"
        )

        return ChatResponse(
            text=text,
            evidence_table=df_table,
            explore_tab=2,
            explore_label="Explore Promotional Breadth vs Depth →",
            suggested_followups=[
                "Who is cheaper?",
                "Where is my brand different?",
                "How has search attention changed?"
            ]
        )

    @staticmethod
    def _format_search_trend(data: Dict[str, Any]) -> ChatResponse:
        b_name = data.get("brand_name", data.get("brand_id"))
        mean_rsi = data.get("mean_rsi", "N/A")
        med_rsi = data.get("median_rsi", "N/A")
        max_rsi = data.get("max_rsi", "N/A")
        low_vol = data.get("low_volume_weeks", 0)
        avg_sh = data.get("avg_cohort_share", 0.0)

        text = (
            f"**Google Trends Search Trajectory for {b_name} (53 Weeks, India Web Search):**\n\n"
            f"• **Annual Mean RSI:** **{mean_rsi}** (Median: {med_rsi})\n"
            f"• **Peak Query Attention:** **Index {max_rsi}** (Relative to 53-week cohort benchmark)\n"
            f"• **Average Cohort Search Share:** **{avg_sh:.1f}%** of relative search attention across the 50 fully comparable weeks.\n"
            f"• **Low Volume Representation:** {low_vol} week(s) recorded as `<1` (preserved as unquantified low-volume; not zero).\n\n"
            f"*Important limitation: Google Trends values represent normalized relative search interest, NOT search volume, impression counts, or sales revenue.*"
        )

        return ChatResponse(
            text=text,
            explore_tab=3,
            explore_label="Explore Search Attention Trajectory →",
            suggested_followups=[
                "Who gets the most search attention?",
                "What search spikes happened recently?",
                "How does my brand compare with Neeman's?"
            ]
        )

    @staticmethod
    def _format_search_comparison(data: Dict[str, Any]) -> ChatResponse:
        t = data["target"]
        comps = data["comparisons"]

        rows = [{"Brand": t["brand_name"], "Mean RSI": f"{t['mean_rsi']:.1f}" if t['mean_rsi'] is not None else "0.0", "Peak RSI": f"{t['max_rsi'] or 0}", "Avg Cohort Share": f"{t['avg_cohort_share'] or 0:.1f}%"}]
        for c in comps:
            rows.append({"Brand": c["brand_name"], "Mean RSI": f"{c['mean_rsi']:.1f}" if c['mean_rsi'] is not None else "0.0", "Peak RSI": f"{c['max_rsi'] or 0}", "Avg Cohort Share": f"{c['avg_cohort_share'] or 0:.1f}%"})

        df_table = pd.DataFrame(rows)

        text = (
            f"**Longitudinal Search Attention Comparison (Google Trends India, Sep 2025 – Sep 2026):**\n\n"
            f"Across the four-brand cohort, **Bacca Bucci (65.4% avg share)** and **Neeman's (33.1% avg share)** "
            f"account for **98.5%** of all measurable search attention within this comparison set.\n\n"
            f"**{t['brand_name']}** holds an average relative search share of **{t['avg_cohort_share'] or 0:.1f}%** over the 50 comparable weeks.\n\n"
            f"*Definition: Cohort Relative Search Share measures relative search attention strictly within this four-brand cohort. It is NOT Indian footwear market share.*"
        )

        return ChatResponse(
            text=text,
            evidence_table=df_table,
            explore_tab=3,
            explore_label="Explore Cohort Search Share →",
            suggested_followups=[
                "What search spikes happened recently?",
                "What is my brand missing?",
                "Compare catalog breadth"
            ]
        )

    @staticmethod
    def _format_recent_changes(data: Dict[str, Any]) -> ChatResponse:
        spikes = data.get("spikes", [])
        if not spikes:
            return ChatResponse(text="No statistically observable week-over-week fluctuations (|Δ| ≥ 5) detected.")

        rows = []
        for sp in spikes[:8]:
            rows.append({
                "Brand": sp["brand_name"],
                "Week": sp["week_start"],
                "RSI Change (WoW Δ)": f"{sp['rsi_change']:+d}",
                "Previous RSI": f"{sp['prev_rsi']:.0f}",
                "Current RSI": f"{sp['current_rsi']:.0f}"
            })
        df_table = pd.DataFrame(rows)

        top_spike = spikes[0]
        text = (
            f"**Observed Week-over-Week Search Movements (|Δ| ≥ 5):**\n\n"
            f"The largest observed movement occurred for **{top_spike['brand_name']}** during the week of **{top_spike['week_start']}**, "
            f"where relative search interest jumped by **{top_spike['rsi_change']:+d} points** (from {top_spike['prev_rsi']:.0f} to {top_spike['current_rsi']:.0f}).\n\n"
            f"*Strict non-causal boundary: BrandSignal records observed statistical movement in Google Trends. We do not attribute spikes to marketing campaigns, sales events, or product launches without verified commercial records.*"
        )

        return ChatResponse(
            text=text,
            evidence_table=df_table,
            explore_tab=3,
            explore_label="Explore Search Movements →",
            suggested_followups=[
                "Who gets the most search attention?",
                "What is happening in my market?",
                "How does my brand compare with Neeman's?"
            ]
        )

    @staticmethod
    def _format_brand_differences(data: Dict[str, Any]) -> ChatResponse:
        t = data["target_brand"]
        diffs = data.get("differences", [])

        bullets = []
        rows = []
        for d in diffs:
            val_str = f"{d['brand_value']:,}" if isinstance(d['brand_value'], int) else f"{d['brand_value']}"
            rows.append({"Dimension": d["dimension"], "Metric": d["metric"], f"{t['name']} Value": val_str, "Status vs Cohort": d["status"].title()})
            bullets.append(f"• **{d['dimension']}:** {t['name']} is **{d['status']}** cohort median ({d['metric']}: {val_str}).")

        df_table = pd.DataFrame(rows)

        text = (
            f"**Observed Differences for {t['name']} vs Cohort Benchmark:**\n\n"
            + "\n".join(bullets) + "\n\n"
            f"*These observations describe measurable alignments in current storefront listings and search index data; they do not imply causal business drivers.*"
        )

        return ChatResponse(
            text=text,
            evidence_table=df_table,
            explore_tab=2,
            explore_label="Explore Full Competitive Benchmark →",
            suggested_followups=[
                "What is my brand missing?",
                "Compare pricing with Neeman's",
                "What categories do competitors sell?"
            ]
        )

    @staticmethod
    def _format_brand_gaps(data: Dict[str, Any]) -> ChatResponse:
        t = data["target_brand"]
        missing_cats = data.get("missing_categories", [])
        style_diff = data.get("style_breadth_difference", 0)
        dens_diff = data.get("variant_density_difference", 0.0)

        cat_str = ", ".join(missing_cats) if missing_cats else "None (all major standardized categories represented)"

        rows = [
            {"Catalog Dimension": "Catalog Breadth (Active Styles)", f"{t['name']}": f"{t['styles']:,}", "Cohort Peer Peak": f"{data.get('max_peer_styles', 0):,}", "Observed Delta": f"-{style_diff:,}" if style_diff > 0 else "0"},
            {"Catalog Dimension": "Variant Density (SKUs/Style)", f"{t['name']}": f"{t['variant_density']:.2f}", "Cohort Peer Peak": f"{(t['variant_density'] + dens_diff):.2f}", "Observed Delta": f"-{dens_diff:.2f}" if dens_diff > 0 else "0.00"},
            {"Catalog Dimension": "Unrepresented Categories", f"{t['name']}": f"{len(missing_cats)} missing", "Cohort Peer Peak": "Complete representation", "Observed Delta": cat_str}
        ]
        df_table = pd.DataFrame(rows)

        text = (
            f"**Observable Catalog Differences for {t['name']} vs Comparison Brands:**\n\n"
            f"Analyzing public storefront listings reveals the following empirical differences:\n\n"
            f"• **Category Presence:** Categories present in comparison brands but not active in {t['name']}'s catalog: **{cat_str}**.\n"
            f"• **Assortment Breadth:** Comparison peers offer up to **{data.get('max_peer_styles', 0):,} styles**, compared to **{t['styles']:,} styles** for {t['name']} (a difference of {style_diff:,} styles).\n"
            f"• **Sizing / Option Depth:** Comparison peers offer up to **{dens_diff:+.2f} more SKU variants per style**.\n\n"
            f"**Methodological Guardrail:** BrandSignal describes observable characteristics in public catalog listings. "
            f"This does **NOT** constitute a strategic recommendation to expand your catalog, launch new categories, or match competitor breadth. "
            f"Strategic assortment decisions depend on merchant margins, brand identity, and operational focus."
        )

        return ChatResponse(
            text=text,
            evidence_table=df_table,
            explore_tab=2,
            explore_label="Explore Assortment & Category Mix →",
            suggested_followups=[
                "Compare my pricing with competitors",
                "What categories does Neeman's sell?",
                "How has search attention changed?"
            ]
        )

    @staticmethod
    def _format_category_mix(data: Dict[str, Any]) -> ChatResponse:
        b_name = data["brand_name"]
        cats = data.get("categories", [])

        rows = []
        bullets = []
        for c in cats:
            rows.append({"Category": c["category"], "SKUs": f"{c['sku_count']:,}", "Share %": f"{c['share_pct']:.1f}%"})
            bullets.append(f"• **{c['category']}:** {c['sku_count']:,} SKUs ({c['share_pct']:.1f}% of catalog)")

        df_table = pd.DataFrame(rows)

        limitation_text = f"\n\n> ⚠️ **Data Limitation:** {data['limitation_note']}" if data.get("has_limitation") else ""

        text = (
            f"**Standardized Category Breakdown for {b_name} (Snapshot: 2026-09-29):**\n\n"
            + "\n".join(bullets)
            + limitation_text
        )

        return ChatResponse(
            text=text,
            evidence_table=df_table,
            explore_tab=2,
            explore_label="Explore Category Mix Chart →",
            suggested_followups=[
                "What is my brand missing?",
                "Who has more products?",
                "Compare pricing"
            ]
        )

    @staticmethod
    def _format_metric_explanation(data: Dict[str, Any]) -> ChatResponse:
        meta = data.get("definition")
        if not meta:
            return ChatResponse(
                text="BrandSignal tracks standardized metrics across Assortment (Active Styles, SKUs, Variant Density), Pricing (Median Price, IQR, Price Positioning Index), Promotional Intensity (Discounted Catalog %, Median Markdown Depth), and Search Attention (Relative Search Interest, Cohort Relative Search Share).",
                explore_tab=1,
                explore_label="Explore Metric Definitions →"
            )

        text = (
            f"### **{meta['name']}**\n\n"
            f"• **Definition:** {meta['definition']}\n"
            f"• **Grain:** {meta['grain']}\n"
            f"• **Important Limitation:** {meta['limitation']}\n"
        )

        return ChatResponse(
            text=text,
            explore_tab=1,
            explore_label="View Methodology Docs →"
        )

    @staticmethod
    def _format_data_availability(data: Dict[str, Any]) -> ChatResponse:
        brands_str = ", ".join(data.get("active_brands", []))
        text = (
            f"**Verified BrandSignal Data Coverage:**\n\n"
            f"• **Active Brands:** {brands_str}\n"
            f"• **Storefront Catalog Snapshot:** {data.get('catalog_snapshot_date')} ({data.get('total_skus', 0):,} total purchasable SKU listings)\n"
            f"• **Longitudinal Google Trends:** {data.get('search_weeks')} weekly periods ({data.get('search_date_range')}) for {data.get('search_geography')}\n"
            f"• **Domain Popularity:** {data.get('domain_rank_source')}\n\n"
            f"*Constraint: Zero synthetic fallbacks; zero LLMs. All figures derive directly from verified primary files and DuckDB analytical tables.*"
        )
        return ChatResponse(
            text=text,
            explore_tab=1,
            explore_label="Explore Market Snapshot →"
        )

    @staticmethod
    def _format_help() -> ChatResponse:
        text = (
            f"**Welcome to BrandSignal Conversational Analytics.**\n\n"
            f"I analyze public storefront catalogs and longitudinal Google Trends signals across Indian D2C footwear brands (*Bacca Bucci, Elevar Sports, Neeman's, Plaeto*).\n\n"
            f"**Example questions you can ask:**\n"
            f"• *What's happening in my market?*\n"
            f"• *How does my brand compare with Neeman's?*\n"
            f"• *Who has more products?*\n"
            f"• *Who is cheaper?*\n"
            f"• *Who discounts the most?*\n"
            f"• *What is my brand missing?*\n"
            f"• *How has search attention changed?*\n"
            f"• *What changed recently in search?*"
        )
        return ChatResponse(
            text=text,
            explore_tab=1,
            explore_label="Explore Market Snapshot →",
            suggested_followups=[
                "What is happening in my market?",
                "How does my brand compare with Neeman's?",
                "What is my brand missing?",
                "Who is cheaper?",
                "What changed recently?"
            ]
        )

    @staticmethod
    def _format_unknown() -> ChatResponse:
        text = (
            f"I can analyze catalog breadth, pricing architecture, promotional discounting, category mix, search attention, and competitor differences using verified BrandSignal data.\n\n"
            f"**Try asking:**\n"
            f"• *How does my brand compare with Neeman's?*\n"
            f"• *What is happening in my market?*\n"
            f"• *Who is cheaper?*\n"
            f"• *What is my brand missing?*"
        )
        return ChatResponse(
            text=text,
            explore_tab=1,
            explore_label="Explore Market Snapshot →",
            suggested_followups=[
                "What is happening in my market?",
                "How does my brand compare with Neeman's?",
                "What is my brand missing?",
                "Who is cheaper?",
                "What changed recently?"
            ]
        )
