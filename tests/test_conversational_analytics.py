import pytest
import pandas as pd
from typing import Dict, Any

from src.conversation.entity_resolver import EntityResolver, CANONICAL_BRANDS
from src.conversation.intent_engine import IntentEngine, IntentMatch
from src.conversation.analytics_service import AnalyticsService
from src.conversation.query_planner import QueryPlanner, QueryPlan, ExecutionResult
from src.conversation.response_generator import ResponseGenerator, ChatResponse

# =============================================================================
# 1. ENTITY RESOLVER TESTS
# =============================================================================

def test_entity_resolver_brand_normalization():
    """Verifies that common aliases, misspellings, and casings resolve to canonical brand IDs."""
    test_cases = [
        ("neemans", "neemans"),
        ("Neeman's", "neemans"),
        ("neeman", "neemans"),
        ("Bacca Bucci", "baccabucci"),
        ("bacca buci", "baccabucci"),
        ("baccabucci", "baccabucci"),
        ("elevar", "elevarsports"),
        ("Elevar Sports", "elevarsports"),
        ("plaeto", "plaeto"),
        ("plato", "plaeto"),
    ]
    for raw_name, expected_id in test_cases:
        assert EntityResolver.normalize_brand_name(raw_name) == expected_id, f"Failed for '{raw_name}'"

def test_entity_resolver_target_and_comparison_extraction():
    """Verifies self-reference resolution and target vs comparison split."""
    # Head to head query with self-reference
    query1 = "How does my brand compare with Neeman's?"
    target1, comps1 = EntityResolver.extract_brands(query1, default_target_brand="baccabucci")
    assert target1 == "baccabucci"
    assert comps1 == ["neemans"]

    # Explicit two-brand query
    query2 = "Compare Elevar Sports vs Plaeto"
    target2, comps2 = EntityResolver.extract_brands(query2, default_target_brand="baccabucci")
    assert target2 == "elevarsports"
    assert comps2 == ["plaeto"]

    # Market question with no explicit brands
    query3 = "What is happening in my market?"
    target3, comps3 = EntityResolver.extract_brands(query3, default_target_brand="baccabucci")
    assert target3 == "baccabucci"
    assert comps3 == []

def test_entity_resolver_metrics_and_time():
    """Verifies metric dimension and temporal period extraction."""
    assert "pricing" in EntityResolver.extract_metrics("What is our pricing strategy?")
    assert "discounting" in EntityResolver.extract_metrics("Who offers deeper markdowns and sales?")
    assert "assortment" in EntityResolver.extract_metrics("Who has more styles and variants?")
    assert "search" in EntityResolver.extract_metrics("What is our relative search attention?")

    assert EntityResolver.extract_time_period("Any recent spikes last week?") == "recent"
    assert EntityResolver.extract_time_period("12-month Google Trends trajectory") == "12m"


# =============================================================================
# 2. INTENT ENGINE TESTS
# =============================================================================

@pytest.mark.parametrize("query,expected_intent", [
    ("I have a D2C footwear brand. What is happening in my market?", "MARKET_OVERVIEW"),
    ("What is trending right now?", "MARKET_OVERVIEW"),
    ("How is my brand performing compared with Neeman's?", "COMPETITOR_COMPARISON"),
    ("Compare Bacca Bucci with Elevar Sports", "COMPETITOR_COMPARISON"),
    ("Who has more styles?", "ASSORTMENT_COMPARISON"),
    ("Who has the biggest catalog?", "ASSORTMENT_COMPARISON"),
    ("Who is cheaper?", "PRICE_COMPARISON"),
    ("How do our prices compare against Neeman's?", "PRICE_COMPARISON"),
    ("Who discounts the most?", "DISCOUNT_COMPARISON"),
    ("Who has deeper markdowns?", "DISCOUNT_COMPARISON"),
    ("What happened to search interest?", "SEARCH_TREND"),
    ("Who gets the most search attention?", "SEARCH_COMPARISON"),
    ("What changed recently?", "RECENT_CHANGE"),
    ("Any search spikes recently?", "RECENT_CHANGE"),
    ("What are competitors doing differently from my brand?", "BRAND_DIFFERENCE"),
    ("Where is my brand different from the other brands?", "BRAND_DIFFERENCE"),
    ("What is my brand missing?", "BRAND_MISSING"),
    ("Where are my catalog gaps?", "BRAND_MISSING"),
    ("What categories do they sell?", "CATEGORY_MIX"),
    ("What is PPI?", "EXPLAIN_METRIC"),
    ("Explain variant density", "EXPLAIN_METRIC"),
    ("What data is available?", "DATA_AVAILABILITY"),
    ("help", "HELP"),
    ("asdkjasdkjh2873198", "UNKNOWN"),
])
def test_intent_classification(query, expected_intent):
    """Verifies deterministic classification across core conversational intents."""
    match = IntentEngine.classify(query)
    assert match.intent == expected_intent, f"Query '{query}' classified as '{match.intent}', expected '{expected_intent}'"


# =============================================================================
# 3. ANALYTICS SERVICE TESTS (READ-ONLY DATABASE QUERIES)
# =============================================================================

@pytest.fixture(scope="module")
def analytics():
    return AnalyticsService()

def test_analytics_market_overview(analytics):
    overview = analytics.get_market_overview("2026-09-29")
    assert "benchmarks" in overview
    assert "brands" in overview
    assert len(overview["brands"]) == 4
    assert overview["benchmarks"]["total_active_products"] == 2050
    assert overview["benchmarks"]["total_active_skus"] == 10576

def test_analytics_compare_brands(analytics):
    res = analytics.compare_brands("baccabucci", "neemans", "2026-09-29")
    assert "brand_a" in res
    assert "brand_b" in res
    assert res["brand_a"]["styles"] == 1077
    assert res["brand_b"]["styles"] == 628
    assert res["brand_a"]["median_price"] == 1499.0
    assert res["brand_b"]["median_price"] == 1999.0

def test_analytics_brand_gaps(analytics):
    plaeto_gaps = analytics.get_brand_gaps("plaeto", ["baccabucci", "elevarsports", "neemans"], "2026-09-29")
    assert "missing_categories" in plaeto_gaps
    assert len(plaeto_gaps["missing_categories"]) > 0
    assert "Boots" in plaeto_gaps["missing_categories"]
    assert plaeto_gaps["style_breadth_difference"] > 0

def test_analytics_invalid_brand_handled_gracefully(analytics):
    res = analytics.compare_brands("non_existent_brand", "neemans", "2026-09-29")
    assert "error" in res


# =============================================================================
# 4. QUERY PLANNER & EXECUTION TESTS
# =============================================================================

def test_query_planner_end_to_end(analytics):
    planner = QueryPlanner(analytics_service=analytics)

    exec_result = planner.execute("How does my brand compare with Neeman's?", active_brand_id="baccabucci")
    assert exec_result.success is True
    assert exec_result.plan.intent == "COMPETITOR_COMPARISON"
    assert exec_result.plan.target_brand == "baccabucci"
    assert "neemans" in exec_result.plan.comparison_brands
    assert "brand_a" in exec_result.data
    assert "brand_b" in exec_result.data

def test_query_planner_price_comparison(analytics):
    planner = QueryPlanner(analytics_service=analytics)
    exec_result = planner.execute("Who is cheaper?", active_brand_id="baccabucci")
    assert exec_result.success is True
    assert exec_result.plan.intent == "PRICE_COMPARISON"
    assert "target" in exec_result.data
    assert "comparisons" in exec_result.data


# =============================================================================
# 5. RESPONSE GENERATOR & GUARDRAILS TESTS
# =============================================================================

def test_response_generator_head_to_head(analytics):
    planner = QueryPlanner(analytics_service=analytics)
    res = planner.execute("How does my brand compare with Neeman's?", active_brand_id="baccabucci")
    chat_resp = ResponseGenerator.generate(res)

    assert isinstance(chat_resp, ChatResponse)
    assert len(chat_resp.text) > 0
    assert chat_resp.evidence_table is not None
    assert not chat_resp.evidence_table.empty
    assert chat_resp.explore_tab == 2
    assert "1,077" in chat_resp.text
    assert "628" in chat_resp.text

def test_response_generator_non_prescriptive_guardrails(analytics):
    """
    STRICT CONSTRAINT: BrandSignal responses must NOT contain prescriptive strategy advice,
    commercial recommendations, or predictive claims.
    """
    forbidden_phrases = [
        "you should",
        "we recommend",
        "strategy recommendation",
        "you must",
        "ought to",
        "action item",
        "increase your prices",
        "decrease your prices",
        "launch new products"
    ]

    test_queries = [
        "What is happening in my market?",
        "How does my brand compare with Neeman's?",
        "What is my brand missing?",
        "Who is cheaper?",
        "Who discounts the most?",
        "What changed recently?",
        "Where is my brand different from the other brands?"
    ]

    planner = QueryPlanner(analytics_service=analytics)
    for q in test_queries:
        exec_res = planner.execute(q, active_brand_id="baccabucci")
        resp = ResponseGenerator.generate(exec_res)
        text_lower = resp.text.lower()
        for phrase in forbidden_phrases:
            assert phrase not in text_lower, f"Prescriptive phrase '{phrase}' found in response to '{q}'"

def test_response_generator_gaps_has_explicit_guardrail(analytics):
    planner = QueryPlanner(analytics_service=analytics)
    exec_res = planner.execute("What is my brand missing?", active_brand_id="plaeto")
    resp = ResponseGenerator.generate(exec_res)

    assert "Methodological Guardrail" in resp.text
    assert "does **NOT** constitute a strategic recommendation" in resp.text
    assert resp.evidence_table is not None

def test_response_generator_unknown_and_help():
    exec_help = ExecutionResult(
        plan=QueryPlan("HELP", None, [], [], "snapshot", "2026-09-29", 1.0),
        data={"help": True},
        success=True
    )
    resp_help = ResponseGenerator.generate(exec_help)
    assert "Welcome to BrandSignal Conversational Analytics" in resp_help.text
    assert len(resp_help.suggested_followups) > 0

    exec_unknown = ExecutionResult(
        plan=QueryPlan("UNKNOWN", None, [], [], "snapshot", "2026-09-29", 0.0),
        data={"unknown": True},
        success=True
    )
    resp_unknown = ResponseGenerator.generate(exec_unknown)
    assert "I can analyze catalog breadth" in resp_unknown.text
