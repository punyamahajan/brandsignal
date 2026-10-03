import os
import duckdb
import pandas as pd
from typing import Dict, Any, List, Optional, Tuple

from src.evidence.models import EvidenceItem
from dashboard.data_loader import (
    load_brand_features,
    compute_cohort_benchmarks,
    load_category_mix,
    load_price_quantiles,
    load_search_demand_series,
    load_search_summary_stats,
    load_search_spikes
)
from src.research.source_registry import SourceRegistry

DEMO_BRAND_MAP = {
    "neemans": "Neeman's",
    "baccabucci": "Bacca Bucci",
    "elevarsports": "Elevar Sports",
    "plaeto": "Plaeto"
}

class AnalyticsToolsEngine:
    """
    Deterministic analytical functions exposed as tool execution targets.
    Reads verified metrics from DuckDB and attaches certified EvidenceItem instances.
    """

    def __init__(self, db_path: str = "data/processed/brandsignal.duckdb"):
        self.db_path = db_path
        self.source_registry = SourceRegistry()

    def get_market_snapshot(self, category: str = "D2C Footwear", snapshot_date: str = "2026-09-29") -> Tuple[Dict[str, Any], List[EvidenceItem]]:
        if category and "footwear" not in category.lower():
            return {
                "category": category,
                "error": f"Structured benchmark snapshot is not available for '{category}' in database.",
                "brands": [],
                "benchmarks": {}
            }, []

        df_feat = load_brand_features(self.db_path, snapshot_date)
        bench = compute_cohort_benchmarks(df_feat)
        evidence = []

        if not df_feat.empty:
            for _, r in df_feat.iterrows():
                b_id = str(r["brand_id"])
                b_name = str(r["brand_name"])
                evidence.append(EvidenceItem(
                    evidence_id=f"EVID-SNAP-{b_id.upper()}",
                    source_name=f"{b_name} Digital Storefront Crawl",
                    source_type="storefront_catalog",
                    source_url=f"https://{b_id}.com/products.json" if b_id != "plaeto" else "https://plaeto.in/products.json",
                    collected_at=f"{snapshot_date}T00:00:00Z",
                    brand_id=b_id,
                    brand_name=b_name,
                    metric="active_catalog_scale",
                    observation=f"{int(r['active_product_count']):,} styles and {int(r['active_sku_count']):,} SKUs (Median Price: ₹{float(r['price_median_inr']):,.0f})",
                    value={"styles": int(r["active_product_count"]), "skus": int(r["active_sku_count"]), "median_price": float(r["price_median_inr"])},
                    raw_reference="fact_brand_snapshot_features",
                    dataset_name="brandsignal.duckdb",
                    limitation_note="Point-in-time public storefront catalog crawl; does not reflect inventory stock counts."
                ))

        brands_list = []
        for _, r in df_feat.iterrows():
            brands_list.append({
                "brand_id": r["brand_id"],
                "brand_name": r["brand_name"],
                "active_styles": int(r["active_product_count"]),
                "active_skus": int(r["active_sku_count"]),
                "median_price": float(r["price_median_inr"]),
                "ppi": float(r["price_positioning_index"]),
                "discount_ratio": float(r["discounted_catalog_ratio"]),
                "tranco_rank": int(r["tranco_global_rank"]) if pd.notna(r["tranco_global_rank"]) else None
            })

        data = {
            "category": category,
            "snapshot_date": snapshot_date,
            "benchmarks": bench,
            "brands": brands_list
        }
        return data, evidence

    def find_competitors(self, brand_name: str, category: Optional[str] = None) -> Tuple[Dict[str, Any], List[EvidenceItem]]:
        """Discovers known cohort peers or searches public domain for outside competitors."""
        cleaned_b = brand_name.lower().replace("'", "").replace(" ", "")
        evidence = []

        # If part of demo footwear cohort
        if any(b_id in cleaned_b for b_id in DEMO_BRAND_MAP):
            peers = [name for b_id, name in DEMO_BRAND_MAP.items() if b_id not in cleaned_b]
            for p in peers:
                evidence.append(EvidenceItem(
                    evidence_id=f"EVID-PEER-{p.replace(' ', '').upper()}",
                    source_name="BrandSignal D2C Footwear Benchmark Registry",
                    source_type="storefront_catalog",
                    collected_at="2026-09-29T00:00:00Z",
                    brand_id=p.lower().replace("'", "").replace(" ", ""),
                    brand_name=p,
                    metric="peer_competitor",
                    observation=f"Established Indian D2C footwear peer competing in footwear catalog.",
                    value=p,
                    dataset_name="dim_brand",
                    raw_reference="dim_brand"
                ))
            return {"brand_name": brand_name, "competitors": peers, "category": "D2C Footwear"}, evidence

        # Non-demo vertical discovery via public search
        res = self.source_registry.research_brand_or_category(f"{brand_name} competitors {category or ''}")
        return {"brand_name": brand_name, "competitors": [], "category": category, "discovered_count": len(res)}, res

    def compare_brands(self, target_brand: str, comparison_brand: str, snapshot_date: str = "2026-09-29") -> Tuple[Dict[str, Any], List[EvidenceItem]]:
        df_feat = load_brand_features(self.db_path, snapshot_date)
        df_search = load_search_summary_stats(self.db_path)
        bench = compute_cohort_benchmarks(df_feat)
        evidence = []

        row_a = df_feat[df_feat["brand_id"] == target_brand]
        row_b = df_feat[df_feat["brand_id"] == comparison_brand]

        if row_a.empty or row_b.empty:
            return {"error": f"One or both brands ({target_brand}, {comparison_brand}) not found in dataset."}, []

        da = row_a.iloc[0]
        db = row_b.iloc[0]

        sa = df_search[df_search["brand_id"] == target_brand].iloc[0] if not df_search[df_search["brand_id"] == target_brand].empty else {}
        sb = df_search[df_search["brand_id"] == comparison_brand].iloc[0] if not df_search[df_search["brand_id"] == comparison_brand].empty else {}

        # Build evidence items
        evidence.append(EvidenceItem(
            evidence_id=f"EVID-COMP-{target_brand.upper()}",
            source_name=f"{da['brand_name']} Public Storefront Crawl",
            source_type="storefront_catalog",
            collected_at=f"{snapshot_date}T00:00:00Z",
            brand_id=target_brand,
            brand_name=da["brand_name"],
            metric="head_to_head_metrics",
            observation=f"{int(da['active_product_count']):,} styles, ₹{float(da['price_median_inr']):,.0f} median price",
            value={"styles": int(da["active_product_count"]), "price": float(da["price_median_inr"])},
            raw_reference="fact_brand_snapshot_features",
            dataset_name="brandsignal.duckdb"
        ))
        evidence.append(EvidenceItem(
            evidence_id=f"EVID-COMP-{comparison_brand.upper()}",
            source_name=f"{db['brand_name']} Public Storefront Crawl",
            source_type="storefront_catalog",
            collected_at=f"{snapshot_date}T00:00:00Z",
            brand_id=comparison_brand,
            brand_name=db["brand_name"],
            metric="head_to_head_metrics",
            observation=f"{int(db['active_product_count']):,} styles, ₹{float(db['price_median_inr']):,.0f} median price",
            value={"styles": int(db["active_product_count"]), "price": float(db["price_median_inr"])},
            raw_reference="fact_brand_snapshot_features",
            dataset_name="brandsignal.duckdb"
        ))

        data = {
            "brand_a": {
                "id": target_brand,
                "name": da["brand_name"],
                "styles": int(da["active_product_count"]),
                "skus": int(da["active_sku_count"]),
                "variant_density": float(da["variant_density"]),
                "median_price": float(da["price_median_inr"]),
                "ppi": float(da["price_positioning_index"]),
                "discount_ratio": float(da["discounted_catalog_ratio"]),
                "median_discount_depth": float(da["median_discount_depth_pct"]) if pd.notna(da["median_discount_depth_pct"]) else 0.0,
                "avg_cohort_share": float(sa.get("avg_cohort_share", 0.0)) if pd.notna(sa.get("avg_cohort_share")) else 0.0
            },
            "brand_b": {
                "id": comparison_brand,
                "name": db["brand_name"],
                "styles": int(db["active_product_count"]),
                "skus": int(db["active_sku_count"]),
                "variant_density": float(db["variant_density"]),
                "median_price": float(db["price_median_inr"]),
                "ppi": float(db["price_positioning_index"]),
                "discount_ratio": float(db["discounted_catalog_ratio"]),
                "median_discount_depth": float(db["median_discount_depth_pct"]) if pd.notna(db["median_discount_depth_pct"]) else 0.0,
                "avg_cohort_share": float(sb.get("avg_cohort_share", 0.0)) if pd.notna(sb.get("avg_cohort_share")) else 0.0
            },
            "benchmarks": bench
        }
        return data, evidence

    def find_brand_gaps(self, target_brand: str, comparison_brands: Optional[List[str]] = None, snapshot_date: str = "2026-09-29") -> Tuple[Dict[str, Any], List[EvidenceItem]]:
        """
        Calculates observable assortment and category coverage gaps.
        Strict non-prescriptive guardrail.
        """
        df_feat = load_brand_features(self.db_path, snapshot_date)
        df_cat = load_category_mix(self.db_path, snapshot_date)
        comps = comparison_brands or [b for b in DEMO_BRAND_MAP if b != target_brand]
        evidence = []

        target_row = df_feat[df_feat["brand_id"] == target_brand]
        if target_row.empty:
            return {"error": f"Target brand '{target_brand}' not found."}, []

        t_data = target_row.iloc[0]
        t_categories = set(df_cat[df_cat["brand_id"] == target_brand]["category_std"].unique())

        peer_cat_df = df_cat[df_cat["brand_id"].isin(comps)]
        peer_categories = set(peer_cat_df["category_std"].unique())
        missing_categories = sorted(list(peer_categories - t_categories))

        max_peer_styles = int(df_feat[df_feat["brand_id"].isin(comps)]["active_product_count"].max())
        style_gap = max(0, max_peer_styles - int(t_data["active_product_count"]))

        max_peer_density = float(df_feat[df_feat["brand_id"].isin(comps)]["variant_density"].max())
        density_diff = round(max_peer_density - float(t_data["variant_density"]), 2)

        ev_id = f"EVID-GAP-{target_brand.upper()}"
        evidence.append(EvidenceItem(
            evidence_id=ev_id,
            source_name="Catalog Assortment & Category Mix Benchmark",
            source_type="storefront_catalog",
            collected_at=f"{snapshot_date}T00:00:00Z",
            brand_id=target_brand,
            brand_name=t_data["brand_name"],
            metric="assortment_gap",
            observation=f"Missing Categories: {', '.join(missing_categories) if missing_categories else 'None'}; Breadth difference: {style_gap:,} styles below peer peak.",
            value={"missing_categories": missing_categories, "style_gap": style_gap},
            dataset_name="fact_brand_category_mix",
            raw_reference="fact_brand_snapshot_features",
            limitation_note="BrandSignal reports observable characteristics; this does NOT constitute strategic advice to launch new categories."
        ))

        data = {
            "target_brand": {
                "id": target_brand,
                "name": t_data["brand_name"],
                "styles": int(t_data["active_product_count"]),
                "variant_density": float(t_data["variant_density"])
            },
            "missing_categories": missing_categories,
            "style_breadth_difference": style_gap,
            "max_peer_styles": max_peer_styles,
            "variant_density_difference": density_diff if density_diff > 0 else 0.0
        }
        return data, evidence

    def compare_prices(self, target_brand: str, comparison_brands: Optional[List[str]] = None, snapshot_date: str = "2026-09-29") -> Tuple[Dict[str, Any], List[EvidenceItem]]:
        df_feat = load_brand_features(self.db_path, snapshot_date)
        bench = compute_cohort_benchmarks(df_feat)
        comps = comparison_brands or [b for b in DEMO_BRAND_MAP if b != target_brand]
        evidence = []

        t_row = df_feat[df_feat["brand_id"] == target_brand]
        if t_row.empty:
            return {"error": f"Target brand '{target_brand}' not found."}, []
        t_data = t_row.iloc[0]

        comp_list = []
        for c_id in comps:
            c_row = df_feat[df_feat["brand_id"] == c_id]
            if not c_row.empty:
                cd = c_row.iloc[0]
                comp_list.append({
                    "brand_id": c_id,
                    "brand_name": cd["brand_name"],
                    "median_price": float(cd["price_median_inr"]),
                    "price_iqr": float(cd["price_iqr_inr"]),
                    "ppi": float(cd["price_positioning_index"])
                })

        evidence.append(EvidenceItem(
            evidence_id=f"EVID-PRICE-{target_brand.upper()}",
            source_name=f"{t_data['brand_name']} Public Storefront Crawl",
            source_type="storefront_catalog",
            collected_at=f"{snapshot_date}T00:00:00Z",
            brand_id=target_brand,
            brand_name=t_data["brand_name"],
            metric="price_median_inr",
            observation=f"Median listed price is ₹{float(t_data['price_median_inr']):,.0f} (PPI: {float(t_data['price_positioning_index']):.2f})",
            value=float(t_data["price_median_inr"]),
            dataset_name="fact_brand_snapshot_features",
            raw_reference="fact_brand_snapshot_features",
            limitation_note="Listed asking prices; does not include checkout coupon codes or cashbacks."
        ))

        data = {
            "target": {
                "id": target_brand,
                "name": t_data["brand_name"],
                "median_price": float(t_data["price_median_inr"]),
                "price_iqr": float(t_data["price_iqr_inr"]),
                "ppi": float(t_data["price_positioning_index"]),
                "cohort_median_price": bench.get("median_price_inr", 1899.0)
            },
            "comparisons": comp_list
        }
        return data, evidence

    def compare_discounting(self, target_brand: str, comparison_brands: Optional[List[str]] = None, snapshot_date: str = "2026-09-29") -> Tuple[Dict[str, Any], List[EvidenceItem]]:
        df_feat = load_brand_features(self.db_path, snapshot_date)
        comps = comparison_brands or [b for b in DEMO_BRAND_MAP if b != target_brand]
        evidence = []

        t_row = df_feat[df_feat["brand_id"] == target_brand]
        if t_row.empty:
            return {"error": f"Target brand '{target_brand}' not found."}, []
        t_data = t_row.iloc[0]

        evidence.append(EvidenceItem(
            evidence_id=f"EVID-DISC-{target_brand.upper()}",
            source_name=f"{t_data['brand_name']} Digital Storefront Crawl",
            source_type="storefront_catalog",
            collected_at=f"{snapshot_date}T00:00:00Z",
            brand_id=target_brand,
            brand_name=t_data["brand_name"],
            metric="discounted_catalog_ratio",
            observation=f"{float(t_data['discounted_catalog_ratio']):.1f}% of catalog discounted with median markdown {float(t_data['median_discount_depth_pct']):.1f}%",
            value=float(t_data["discounted_catalog_ratio"]),
            dataset_name="fact_brand_snapshot_features",
            raw_reference="fact_brand_snapshot_features"
        ))

        comp_list = []
        for c_id in comps:
            c_row = df_feat[df_feat["brand_id"] == c_id]
            if not c_row.empty:
                cd = c_row.iloc[0]
                comp_list.append({
                    "brand_id": c_id,
                    "brand_name": cd["brand_name"],
                    "discount_ratio": float(cd["discounted_catalog_ratio"]),
                    "median_discount_depth": float(cd["median_discount_depth_pct"]) if pd.notna(cd["median_discount_depth_pct"]) else 0.0
                })

        data = {
            "target": {
                "id": target_brand,
                "name": t_data["brand_name"],
                "discount_ratio": float(t_data["discounted_catalog_ratio"]),
                "median_discount_depth": float(t_data["median_discount_depth_pct"]) if pd.notna(t_data["median_discount_depth_pct"]) else 0.0
            },
            "comparisons": comp_list
        }
        return data, evidence

    def compare_assortment(self, target_brand: str, comparison_brands: Optional[List[str]] = None, snapshot_date: str = "2026-09-29") -> Tuple[Dict[str, Any], List[EvidenceItem]]:
        df_feat = load_brand_features(self.db_path, snapshot_date)
        comps = comparison_brands or [b for b in DEMO_BRAND_MAP if b != target_brand]
        evidence = []

        t_row = df_feat[df_feat["brand_id"] == target_brand]
        if t_row.empty:
            return {"error": f"Target brand '{target_brand}' not found."}, []
        t_data = t_row.iloc[0]

        evidence.append(EvidenceItem(
            evidence_id=f"EVID-ASSORT-{target_brand.upper()}",
            source_name=f"{t_data['brand_name']} Public Storefront Crawl",
            source_type="storefront_catalog",
            collected_at=f"{snapshot_date}T00:00:00Z",
            brand_id=target_brand,
            brand_name=t_data["brand_name"],
            metric="active_styles",
            observation=f"Catalog lists {int(t_data['active_product_count']):,} active styles ({int(t_data['active_sku_count']):,} SKUs, {float(t_data['variant_density']):.2f} variants/style)",
            value=int(t_data["active_product_count"]),
            dataset_name="fact_brand_snapshot_features",
            raw_reference="fact_brand_snapshot_features"
        ))

        comp_list = []
        for c_id in comps:
            c_row = df_feat[df_feat["brand_id"] == c_id]
            if not c_row.empty:
                cd = c_row.iloc[0]
                comp_list.append({
                    "brand_id": c_id,
                    "brand_name": cd["brand_name"],
                    "styles": int(cd["active_product_count"]),
                    "skus": int(cd["active_sku_count"]),
                    "variant_density": float(cd["variant_density"])
                })

        data = {
            "target": {
                "id": target_brand,
                "name": t_data["brand_name"],
                "styles": int(t_data["active_product_count"]),
                "skus": int(t_data["active_sku_count"]),
                "variant_density": float(t_data["variant_density"])
            },
            "comparisons": comp_list
        }
        return data, evidence

    def get_search_trends(self, brand_id: str) -> Tuple[Dict[str, Any], List[EvidenceItem]]:
        df_summary = load_search_summary_stats(self.db_path)
        evidence = []

        b_row = df_summary[df_summary["brand_id"] == brand_id]
        if b_row.empty:
            return {"error": f"Search demand data for '{brand_id}' not found."}, []
        bs = b_row.iloc[0]
        b_name = DEMO_BRAND_MAP.get(brand_id, brand_id.title())
        peak_str = str(bs["peak_week"]) if "peak_week" in bs and pd.notna(bs["peak_week"]) else "Annual Peak"

        ev_id = f"EVID-TREND-{brand_id.upper()}"
        evidence.append(EvidenceItem(
            evidence_id=ev_id,
            source_name="Official Google Trends 53-Week Series (India, Web Search)",
            source_type="google_trends",
            source_url="https://trends.google.com/trends/",
            collected_at="2026-09-29T00:00:00Z",
            brand_id=brand_id,
            brand_name=b_name,
            metric="relative_search_interest",
            observation=f"Mean RSI: {float(bs['mean_rsi']):.1f} / 100 (Peak: {float(bs['max_rsi']):.0f})",
            value=float(bs["mean_rsi"]),
            dataset_name="google_trends_india_12m.csv",
            raw_reference="fact_search_demand",
            limitation_note="Google Trends index [0-100] measures relative search interest, not search query volume or sales."
        ))

        data = {
            "target_brand": {"id": brand_id, "name": b_name},
            "search_stats": {
                "mean_rsi": float(bs["mean_rsi"]),
                "median_rsi": float(bs["median_rsi"]),
                "max_rsi": float(bs["max_rsi"]),
                "min_rsi": float(bs["min_rsi"]),
                "peak_week": peak_str,
                "avg_cohort_share": float(bs["avg_cohort_share"]) if pd.notna(bs["avg_cohort_share"]) else 0.0
            }
        }
        return data, evidence

    def get_recent_changes(self, min_abs_delta: int = 5) -> Tuple[Dict[str, Any], List[EvidenceItem]]:
        df_spikes = load_search_spikes(self.db_path, min_abs_delta)
        evidence = []

        spikes_list = []
        if not df_spikes.empty:
            for idx, r in df_spikes.iterrows():
                b_name = DEMO_BRAND_MAP.get(r["brand_id"], r["brand_id"])
                spikes_list.append({
                    "brand_id": r["brand_id"],
                    "brand_name": b_name,
                    "week_str": str(r["week_str"]),
                    "rsi_change": int(r["rsi_change"]),
                    "prev_rsi": float(r["prev_rsi"]),
                    "current_rsi": float(r["current_rsi"])
                })

            top_spike = spikes_list[0]
            evidence.append(EvidenceItem(
                evidence_id="EVID-SPIKE-TOP",
                source_name="Google Trends Weekly Fluctuation Monitor",
                source_type="google_trends",
                collected_at="2026-09-29T00:00:00Z",
                brand_id=top_spike["brand_id"],
                brand_name=top_spike["brand_name"],
                metric="rsi_weekly_change",
                observation=f"Week-over-week RSI jump of {top_spike['rsi_change']:+d} (from {top_spike['prev_rsi']} to {top_spike['current_rsi']}) starting {top_spike['week_str']}",
                value=int(top_spike["rsi_change"]),
                dataset_name="google_trends_india_12m.csv",
                raw_reference="fact_search_demand",
                limitation_note="Fluctuations are strictly descriptive; BrandSignal does not attribute causes without primary proof."
            ))

        return {"spikes": spikes_list, "min_threshold": min_abs_delta}, evidence

    def get_category_mix(self, brand_id: str, snapshot_date: str = "2026-09-29") -> Tuple[Dict[str, Any], List[EvidenceItem]]:
        df_cat = load_category_mix(self.db_path, snapshot_date)
        evidence = []

        b_rows = df_cat[df_cat["brand_id"] == brand_id]
        if b_rows.empty:
            return {"error": f"Category mix for '{brand_id}' not found."}, []

        b_name = DEMO_BRAND_MAP.get(brand_id, brand_id.title())
        cats = []
        for _, r in b_rows.iterrows():
            cats.append({
                "category": r["category_std"],
                "sku_count": int(r["category_sku_count"]),
                "share_pct": float(r["category_share_pct"])
            })

        evidence.append(EvidenceItem(
            evidence_id=f"EVID-CATMIX-{brand_id.upper()}",
            source_name=f"{b_name} Product Type Standardization Layer",
            source_type="storefront_catalog",
            collected_at=f"{snapshot_date}T00:00:00Z",
            brand_id=brand_id,
            brand_name=b_name,
            metric="category_sku_mix",
            observation=f"Catalog partitioned across {len(cats)} standardized categories.",
            value={"categories_count": len(cats)},
            dataset_name="fact_brand_category_mix",
            raw_reference="fact_brand_category_mix"
        ))

        return {"brand_id": brand_id, "brand_name": b_name, "categories": cats}, evidence

    def get_data_availability(
        self,
        brand_name: Optional[str] = None,
        category: Optional[str] = None,
        industry: Optional[str] = None
    ) -> Tuple[Dict[str, Any], List[EvidenceItem]]:
        """
        Verifies whether structured empirical catalog data exists in DuckDB for a requested entity.
        """
        cat_lower = (category or "").lower()
        ind_lower = (industry or "").lower()
        b_lower = (brand_name or "").lower().replace("'", "").replace(" ", "")

        is_footwear_demo = (
            "footwear" in cat_lower or 
            "footwear" in ind_lower or 
            any(k in b_lower for k in DEMO_BRAND_MAP)
        )

        evidence = []
        if is_footwear_demo:
            ev = EvidenceItem(
                evidence_id="EVID-AVAIL-FOOTWEAR",
                source_name="BrandSignal Analytical Warehouse",
                source_type="database_registry",
                collected_at="2026-09-29T00:00:00Z",
                metric="data_availability",
                observation="Full structured catalog snapshot, price features, and Google Trends available for 4 D2C footwear brands.",
                value={"available": True, "category": "D2C Footwear", "brand_count": 4},
                dataset_name="brandsignal.duckdb"
            )
            evidence.append(ev)
            return {
                "available": True,
                "category": "D2C Footwear",
                "tables": ["fact_catalog_snapshot", "fact_brand_snapshot_features", "fact_search_demand"],
                "brands": list(DEMO_BRAND_MAP.values())
            }, evidence

        # Unsupported market
        market_label = category or industry or brand_name or "this category"
        ev = EvidenceItem(
            evidence_id="EVID-AVAIL-UNSUPPORTED",
            source_name="BrandSignal Analytical Warehouse",
            source_type="database_registry",
            collected_at="2026-09-29T00:00:00Z",
            metric="data_availability",
            observation=f"Structured catalog and benchmark dataset is not available in local DuckDB for {market_label}. Public research tools must be used.",
            value={"available": False, "market": market_label},
            dataset_name="brandsignal.duckdb"
        )
        evidence.append(ev)
        return {
            "available": False,
            "market": market_label,
            "message": f"Structured catalog and benchmark dataset is not available in local DuckDB for {market_label}. BrandSignal must rely on public web and video research tools."
        }, evidence

    def search_public_web(self, query: str) -> Tuple[Dict[str, Any], List[EvidenceItem]]:
        """Executes polite public web search and returns structured EvidenceItems."""
        provider = self.source_registry.get_provider("web_search")
        if not provider:
            return {"error": "Web search provider not available", "query": query}, []
        res = provider.search(query)
        data = {
            "query": query,
            "success": res.success,
            "findings_count": len(res.evidence_items),
            "error": res.error_message if not res.success else None
        }
        return data, res.evidence_items

    def search_brand_site(self, domain_or_url: str) -> Tuple[Dict[str, Any], List[EvidenceItem]]:
        """Politely inspects public brand domain metadata and storefront structure."""
        provider = self.source_registry.get_provider("brand_site")
        if not provider:
            return {"error": "Brand site provider not available", "url": domain_or_url}, []
        res = provider.search(domain_or_url)
        data = {
            "target": domain_or_url,
            "success": res.success,
            "findings_count": len(res.evidence_items),
            "error": res.error_message if not res.success else None
        }
        return data, res.evidence_items

    def search_youtube(self, query: str, max_results: int = 5) -> Tuple[Dict[str, Any], List[EvidenceItem]]:
        """Searches YouTube video content using official Data API v3 key."""
        provider = self.source_registry.get_provider("youtube")
        if not provider:
            return {"error": "YouTube provider not available", "query": query}, []
        res = provider.search(query, max_results=max_results)
        data = {
            "query": query,
            "success": res.success,
            "video_count": len(res.evidence_items),
            "error": res.error_message if not res.success else None,
            "guardrail_note": "Public video metadata only; does not represent sales or market share."
        }
        return data, res.evidence_items

    def search_public_sources(self, query: str) -> Tuple[Dict[str, Any], List[EvidenceItem]]:
        """Gathers public web intelligence for non-demo categories/brands."""
        evidence = self.source_registry.research_brand_or_category(query)
        data = {
            "query": query,
            "findings_count": len(evidence),
            "sources": [e.source_name for e in evidence]
        }
        return data, evidence

