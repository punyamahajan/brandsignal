import pytest
from src.orchestrator.context import BrandContext, BrandContextManager
from src.orchestrator.service import ConversationalOrchestrator, OrchestratorResponse

def test_greeting_does_not_route_to_market_analytics():
    """
    CRITICAL REQUIREMENT:
    Input 'hi' must return a natural greeting and invitation to describe the user's brand.
    It must NOT route 'hi' into a market analytics intent or execute DuckDB queries.
    """
    orch = ConversationalOrchestrator()
    resp = orch.process_turn("hi")

    assert resp.is_clarification is True
    assert "BrandSignal" in resp.narrative
    assert "Tell me about your brand" in resp.narrative
    assert len(resp.cited_evidence) == 0

def test_greeting_variations():
    orch = ConversationalOrchestrator()
    for greeting in ["hello", "Hey", "Good morning", "greetings"]:
        resp = orch.process_turn(greeting)
        assert resp.is_clarification is True
        assert len(resp.cited_evidence) == 0

def test_cross_industry_brand_context_extraction():
    """
    CRITICAL REQUIREMENT:
    'My company sells premium coffee' or 'I run a soft drink brand called Pepsi'
    must recognize industries outside footwear rather than failing.
    """
    ctx_pepsi = BrandContextManager.extract_from_text("I run a soft drink brand called Pepsi.")
    assert ctx_pepsi.brand_name == "Pepsi"
    assert ctx_pepsi.industry == "Beverages"
    assert ctx_pepsi.is_demo_vertical is False

    ctx_coffee = BrandContextManager.extract_from_text("My company sells premium coffee.")
    assert ctx_coffee.industry == "Coffee"
    assert ctx_coffee.price_positioning == "Premium / High-End"
    assert ctx_coffee.is_demo_vertical is False

    ctx_beauty = BrandContextManager.extract_from_text("We sell D2C skincare serums.")
    assert ctx_beauty.industry == "Beauty"
    assert ctx_beauty.is_demo_vertical is False

def test_footwear_demo_vertical_recognition():
    """Verifies that mentioning demo footwear brands maps to the verified vertical dataset."""
    ctx_bb = BrandContextManager.extract_from_text("How does Bacca Bucci perform?")
    assert ctx_bb.is_demo_vertical is True
    assert ctx_bb.demo_brand_id == "baccabucci"

    ctx_neemans = BrandContextManager.extract_from_text("Compare with Neeman's")
    assert ctx_neemans.is_demo_vertical is True
    assert ctx_neemans.demo_brand_id == "neemans"

def test_multi_turn_session_context_persistence():
    """Tests conversational continuity over multiple user turns."""
    orch = ConversationalOrchestrator()

    # Turn 1: Onboarding greeting
    t1 = orch.process_turn("Hi")
    assert t1.is_clarification is True

    # Turn 2: Establish brand context
    t2 = orch.process_turn("I run a D2C footwear brand focused on affordable everyday sneakers.")
    assert orch.context.is_established() is True
    assert orch.context.industry == "Footwear"

    # Turn 3: Inquiry referencing competitor
    t3 = orch.process_turn("How do our prices compare against Neeman's?")
    assert len(t3.cited_evidence) > 0
    assert t3.visual_navigation_target in ["Competitors", "Market"]
    assert "Neeman's" in t3.narrative

def test_unknown_brand_triggers_clarification():
    """Verifies that vague queries without context ask a clarifying question."""
    orch = ConversationalOrchestrator()
    resp = orch.process_turn("What do you think?")
    assert resp.is_clarification is True
