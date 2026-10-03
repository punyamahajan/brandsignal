import pytest
from src.llm import LLMProvider, get_llm_provider, ToolCall, ToolResult, LLMPlan, SynthesizedResponse
from src.llm.provider import DeterministicHybridProvider
from src.orchestrator.context import BrandContext

def test_llm_provider_factory_fallback(monkeypatch):
    """Verifies that the factory safely yields a functional provider without requiring external API keys."""
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    provider = get_llm_provider()
    assert isinstance(provider, LLMProvider)
    assert isinstance(provider, DeterministicHybridProvider)

def test_tool_planning_schema():
    provider = DeterministicHybridProvider()
    ctx = BrandContext(brand_name="Neeman's", industry="Footwear", is_demo_vertical=True, demo_brand_id="neemans")

    plan = provider.plan_tools("Who has more styles?", ctx)
    assert isinstance(plan, LLMPlan)
    assert plan.intent == "ASSORTMENT_COMPARISON"
    assert len(plan.tool_calls) > 0
    assert plan.tool_calls[0].tool_name == "compare_assortment"
    assert plan.visual_action == "Gaps"

def test_synthesized_response_schema():
    provider = DeterministicHybridProvider()
    ctx = BrandContext(brand_name="Bacca Bucci", industry="Footwear", is_demo_vertical=True, demo_brand_id="baccabucci")

    # Mock tool result
    tool_res = ToolResult(
        tool_name="get_market_snapshot",
        success=True,
        data={
            "category": "D2C Footwear",
            "benchmarks": {"total_active_products": 2050, "total_active_skus": 10576, "median_price_inr": 1899.0, "median_discount_ratio": 95.8},
            "brands": [{"brand_name": "Bacca Bucci"}, {"brand_name": "Neeman's"}]
        },
        evidence_ids=["EVID-MOCK-01"]
    )

    resp = provider.synthesize_response("What is happening in my market?", ctx, [tool_res])
    assert isinstance(resp, SynthesizedResponse)
    assert len(resp.narrative) > 0
    assert "2,050 styles" in resp.narrative
    assert resp.cited_evidence_ids == ["EVID-MOCK-01"]
    assert resp.visual_navigation_target == "Market"

def test_pydantic_schema_validation():
    tc = ToolCall(tool_name="compare_prices", arguments={"target_brand": "baccabucci"})
    assert tc.tool_name == "compare_prices"
    assert tc.arguments["target_brand"] == "baccabucci"

    tr = ToolResult(tool_name="compare_prices", success=True, data={"median": 1499}, evidence_ids=["EVID-1"])
    assert tr.success is True
    assert tr.evidence_ids == ["EVID-1"]

def test_gemini_and_anthropic_provider_fallback():
    from src.llm.provider import GeminiProvider, AnthropicProvider
    ctx = BrandContext(brand_name="Neeman's", industry="Footwear", is_demo_vertical=True, demo_brand_id="neemans")

    # With dummy/invalid key, should fall back to deterministic hybrid provider safely without crashing
    gemini_prov = GeminiProvider(api_key="mock_invalid_key")
    plan = gemini_prov.plan_tools("Who has more styles?", ctx)
    assert isinstance(plan, LLMPlan)
    assert plan.intent == "ASSORTMENT_COMPARISON"

    anthropic_prov = AnthropicProvider(api_key="mock_invalid_key")
    plan_claude = anthropic_prov.plan_tools("Who has more styles?", ctx)
    assert isinstance(plan_claude, LLMPlan)
    assert plan_claude.intent == "ASSORTMENT_COMPARISON"
