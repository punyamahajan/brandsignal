import pytest
from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)

def test_root_and_health():
    res = client.get("/")
    assert res.status_code == 200
    data = res.json()
    assert data["service"] == "BrandSignal Intelligence API"
    assert data["status"] == "operational"

    health = client.get("/api/health")
    assert health.status_code == 200
    assert health.json()["status"] == "healthy"

def test_analytics_snapshot_dates_and_brands():
    dates_res = client.get("/api/analytics/snapshot-dates")
    assert dates_res.status_code == 200
    dates = dates_res.json()
    assert isinstance(dates, list)
    assert "2026-09-29" in dates

    brands_res = client.get("/api/analytics/brands")
    assert brands_res.status_code == 200
    brands = brands_res.json()
    assert len(brands) == 4
    brand_ids = [b["id"] for b in brands]
    assert "neemans" in brand_ids
    assert "baccabucci" in brand_ids

def test_analytics_market_snapshot():
    res = client.get("/api/analytics/market?category=D2C%20Footwear&snapshot_date=2026-09-29")
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["category"] == "D2C Footwear"
    assert len(data["brands"]) == 4
    assert "benchmarks" in data
    assert data["benchmarks"]["total_active_products"] == 2050

def test_analytics_brand_comparison():
    res = client.get("/api/analytics/compare?brand_a=baccabucci&brand_b=neemans")
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["brand_a"]["id"] == "baccabucci"
    assert data["brand_b"]["id"] == "neemans"
    assert data["brand_a"]["styles"] == 1077
    assert data["brand_b"]["styles"] == 628

def test_analytics_pricing_and_assortment():
    price_res = client.get("/api/analytics/pricing?target_brand=baccabucci")
    assert price_res.status_code == 200
    pdata = price_res.json()["data"]
    assert pdata["target"]["median_price"] == 1499.0
    assert len(pdata["comparisons"]) == 3

    assort_res = client.get("/api/analytics/assortment?target_brand=neemans")
    assert assort_res.status_code == 200
    adata = assort_res.json()["data"]
    assert adata["target"]["styles"] == 628

def test_analytics_gaps_endpoint():
    res = client.get("/api/analytics/gaps?target_brand=baccabucci")
    assert res.status_code == 200
    gdata = res.json()["data"]
    assert "target_brand" in gdata
    assert "missing_categories" in gdata

def test_analytics_trends_and_spikes():
    trend_res = client.get("/api/analytics/trends/neemans")
    assert trend_res.status_code == 200
    tdata = trend_res.json()["data"]
    assert tdata["target_brand"]["name"] == "Neeman's"
    assert "search_stats" in tdata
    assert tdata["search_stats"]["mean_rsi"] > 0

    spike_res = client.get("/api/analytics/spikes?min_abs_delta=5")
    assert spike_res.status_code == 200
    spdata = spike_res.json()["data"]
    assert len(spdata["spikes"]) > 0

def test_context_lifecycle():
    session_id = "test-session-123"

    # 1. Get initial context
    res = client.get(f"/api/context/{session_id}")
    assert res.status_code == 200
    assert res.json()["is_established"] is False

    # 2. Update context
    update_res = client.post(f"/api/context/{session_id}", json={
        "brand_name": "Test Brand",
        "industry": "Footwear",
        "category": "Sneakers",
        "price_positioning": "Mid-Tier"
    })
    assert update_res.status_code == 200
    ctx = update_res.json()
    assert ctx["brand_name"] == "Test Brand"
    assert ctx["is_established"] is True

    # 3. Reset context
    reset_res = client.post(f"/api/context/{session_id}/reset")
    assert reset_res.status_code == 200

    # 4. Verify context is fresh
    fresh_res = client.get(f"/api/context/{session_id}")
    assert fresh_res.json()["is_established"] is False

def test_chat_message_greeting_and_onboarding():
    res = client.post("/api/chat/message", json={
        "message": "Hi",
        "session_id": "test-chat-session"
    })
    assert res.status_code == 200
    body = res.json()
    assert body["is_clarification"] is True
    assert "BrandSignal" in body["narrative"]
    assert len(body["suggested_followups"]) > 0

def test_chat_message_market_overview():
    res = client.post("/api/chat/message", json={
        "message": "What is happening in my market?",
        "session_id": "test-chat-market",
        "brand_context": {
            "industry": "Footwear",
            "category": "D2C Footwear",
            "is_demo_vertical": True
        }
    })
    assert res.status_code == 200
    body = res.json()
    assert body["is_clarification"] is False
    assert "2,050 styles" in body["narrative"]
    assert len(body["cited_evidence"]) > 0
    assert body["visual_navigation_target"] == "Market"
    assert len(body["why_are_you_saying_this_md"]) > 0

def test_chat_message_competitor_comparison():
    res = client.post("/api/chat/message", json={
        "message": "Compare Bacca Bucci with Neeman's",
        "session_id": "test-chat-comp"
    })
    assert res.status_code == 200
    body = res.json()
    assert "1,077 styles" in body["narrative"]
    assert "628 styles" in body["narrative"]
    assert body["visual_navigation_target"] == "Competitors"

def test_chat_message_gap_analysis():
    res = client.post("/api/chat/message", json={
        "message": "What is my brand missing?",
        "session_id": "test-chat-gaps",
        "brand_context": {
            "brand_name": "Bacca Bucci",
            "demo_brand_id": "baccabucci",
            "is_demo_vertical": True
        }
    })
    assert res.status_code == 200
    body = res.json()
    assert "Observable Catalog Differences" in body["narrative"]
    assert "Methodological Guardrail" in body["narrative"]
    assert body["visual_navigation_target"] == "Gaps"


def test_research_providers_endpoint():
    res = client.get("/api/research/providers")
    assert res.status_code == 200
    providers = res.json()
    names = [p["name"] for p in providers]
    assert "youtube" in names
    assert "web_search" in names

def test_chat_message_with_serialized_brand_context():
    """Verifies that sending full serialized BrandContext (with boolean is_established and string summary) does not overwrite instance methods."""
    res = client.post("/api/chat/message", json={
        "message": "What is happening in my market?",
        "session_id": "test-context-serialization",
        "brand_context": {
            "brand_name": "Neeman's",
            "industry": "Footwear",
            "category": "Sneakers",
            "is_established": True,
            "summary": "Brand: Neeman's | Industry: Footwear"
        }
    })
    assert res.status_code == 200
    body = res.json()
    assert body["is_clarification"] is False
    assert "2,050 styles" in body["narrative"]

