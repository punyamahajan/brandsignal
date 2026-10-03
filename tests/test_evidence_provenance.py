import pytest
from src.evidence.models import EvidenceItem, EvidenceStore

def test_evidence_item_creation_and_serialization():
    item = EvidenceItem(
        evidence_id="EVID-TEST-01",
        source_name="Neeman's Digital Storefront Crawl",
        source_type="storefront_catalog",
        source_url="https://neemans.com/products.json",
        collected_at="2026-09-29T00:00:00Z",
        brand_id="neemans",
        brand_name="Neeman's",
        metric="active_styles",
        observation="628 styles listed on storefront",
        value=628,
        confidence=1.0,
        dataset_name="brandsignal.duckdb",
        raw_reference="fact_brand_snapshot_features",
        limitation_note="Storefront asking prices; does not include coupon discounts."
    )
    d = item.to_dict()
    assert d["evidence_id"] == "EVID-TEST-01"
    assert d["brand_id"] == "neemans"
    assert d["value"] == 628
    assert "Source Link" in item.format_citation()

def test_evidence_store_crud_and_filtering():
    store = EvidenceStore()
    i1 = EvidenceItem(
        evidence_id="EVID-1",
        source_name="Storefront",
        source_type="storefront_catalog",
        collected_at="2026-09-29T00:00:00Z",
        brand_id="baccabucci",
        brand_name="Bacca Bucci",
        metric="active_styles",
        observation="1,077 styles",
        value=1077
    )
    i2 = EvidenceItem(
        evidence_id="EVID-2",
        source_name="Google Trends",
        source_type="google_trends",
        collected_at="2026-09-29T00:00:00Z",
        brand_id="neemans",
        brand_name="Neeman's",
        metric="relative_search_interest",
        observation="Mean RSI 33.1",
        value=33.1
    )

    store.add_many([i1, i2])
    assert len(store.get_all()) == 2
    assert store.get("EVID-1") == i1
    assert len(store.filter_by_brand("baccabucci")) == 1
    assert len(store.filter_by_metric("relative_search_interest")) == 1

def test_evidence_verification_and_hallucination_rejection():
    """Verifies that cited evidence IDs are matched against real recorded items, rejecting fake IDs."""
    store = EvidenceStore()
    real_item = EvidenceItem(
        evidence_id="EVID-REAL-01",
        source_name="Storefront Crawl",
        source_type="storefront_catalog",
        collected_at="2026-09-29T00:00:00Z",
        brand_id="plaeto",
        brand_name="Plaeto",
        metric="median_price",
        observation="₹1,799",
        value=1799.0
    )
    store.add(real_item)

    cited = ["EVID-REAL-01", "EVID-HALLUCINATED-99"]
    valid, missing = store.verify_citations(cited)

    assert len(valid) == 1
    assert valid[0].evidence_id == "EVID-REAL-01"
    assert missing == ["EVID-HALLUCINATED-99"]

def test_why_are_you_saying_this_rendering():
    store = EvidenceStore()
    item = EvidenceItem(
        evidence_id="EVID-PROV-01",
        source_name="Storefront Crawl",
        source_type="storefront_catalog",
        source_url="https://baccabucci.com/products.json",
        collected_at="2026-09-29T00:00:00Z",
        brand_id="baccabucci",
        brand_name="Bacca Bucci",
        metric="catalog_scale",
        observation="1,077 styles",
        value=1077,
        dataset_name="fact_brand_snapshot_features",
        raw_reference="fact_brand_snapshot_features",
        limitation_note="Single point in time"
    )
    store.add(item)
    why_md = store.render_why_are_you_saying_this(["EVID-PROV-01"])

    assert "Why are you saying this?" not in why_md or "Evidence & Source Provenance" in why_md
    assert "EVID-PROV-01" in why_md
    assert "Bacca Bucci" in why_md
    assert "Single point in time" in why_md
