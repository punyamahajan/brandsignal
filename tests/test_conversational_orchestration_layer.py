import pytest
import os
from unittest.mock import patch, MagicMock

from src.orchestrator.service import ConversationalOrchestrator, OrchestratorResponse
from src.orchestrator.context import BrandContext, BrandContextManager
from src.orchestrator.competitor_discovery import HybridCompetitorDiscoveryProvider, CandidateCompetitor
from src.evidence.models import EvidenceStore, EvidenceItem
from src.tools.registry import ToolRegistry
from src.tools.analytics_tools import AnalyticsToolsEngine
from src.llm.base import LLMConfigurationError
from src.llm.provider import DeterministicHybridProvider, GeminiProvider, AnthropicProvider, get_llm_provider
from src.llm.schemas import ToolCall, ToolResult
from src.research.youtube import YouTubeContentProvider
from src.research.web_search import PublicWebSearchProvider

@pytest.fixture
def orchestrator():
    """Provides a fresh ConversationalOrchestrator instance for testing."""
    return ConversationalOrchestrator(
        llm_provider=DeterministicHybridProvider(),
        evidence_store=EvidenceStore(),
        competitor_provider=HybridCompetitorDiscoveryProvider()
    )


# 1. "hi" -> conversational greeting, NOT market overview
def test_greeting_hi(orchestrator):
    res = orchestrator.process_turn("hi")
    assert res.is_clarification is True
    assert "BrandSignal" in res.narrative
    assert "styles" not in res.narrative
    assert "Market Overview" not in res.narrative
    assert len(res.cited_evidence) == 0


# 2. "hello" -> conversational greeting
def test_greeting_hello(orchestrator):
    res = orchestrator.process_turn("hello")
    assert res.is_clarification is True
    assert "Tell me about your brand" in res.narrative
    assert len(res.cited_evidence) == 0


# 3. "what can you do?" -> conversational explanation of capabilities, no analytics
def test_capabilities_query(orchestrator):
    res = orchestrator.process_turn("what can you do?")
    assert res.is_clarification is True
    assert "BrandSignal" in res.narrative
    assert "pricing architecture" in res.narrative or "market" in res.narrative
    assert len(res.cited_evidence) == 0


# 4. "I run a stationery brand." -> recognizes industry = stationery, no assumption of footwear or D2C India
def test_industry_stationery_recognition(orchestrator):
    res = orchestrator.process_turn("I run a stationery brand.")
    ctx = orchestrator.context
    assert ctx.industry == "Stationery"
    assert ctx.is_demo_vertical is False
    assert ctx.geography is None  # Does not assume India
    assert ctx.business_model is None  # Does not assume D2C
    assert len(ctx.competitors) == 0  # Does not populate footwear competitors
    assert res.is_clarification is True
    assert "stationery" in res.narrative.lower()
    assert "Footwear" not in res.narrative


# 5. "I run a D2C footwear brand." -> recognizes industry = footwear, business_model = D2C
def test_industry_footwear_d2c_recognition(orchestrator):
    res = orchestrator.process_turn("I run a D2C footwear brand.")
    ctx = orchestrator.context
    assert ctx.industry == "Footwear"
    assert ctx.business_model == "D2C"
    assert ctx.is_demo_vertical is False  # Not demo unless explicitly selected
    assert res.is_clarification is True


# 6. missing geography -> asks user for geography when required
def test_missing_geography_clarification(orchestrator):
    res = orchestrator.process_turn("I run a footwear brand.")
    assert "geography" in res.narrative.lower() or "market" in res.narrative.lower()


# 7. competitor discovery unavailable -> returns "Competitor discovery is not currently available for this market." (e.g. stationery)
def test_competitor_discovery_unavailable():
    provider = HybridCompetitorDiscoveryProvider()
    candidates, msg = provider.discover_competitors(industry="Stationery")
    assert len(candidates) == 0
    assert "Competitor discovery is not currently available for Stationery" in msg


# 8. YouTube tool invocation -> search_youtube executed with structured EvidenceItem output
def test_youtube_tool_invocation():
    engine = AnalyticsToolsEngine()
    data, evidence = engine.search_youtube(query="Neeman's shoe review", max_results=2)
    assert data["query"] == "Neeman's shoe review"
    assert "guardrail_note" in data
    assert "sales or market share" in data["guardrail_note"]
    # If API key configured, evidence items exist and are certified
    if evidence:
        assert all(it.source_type == "youtube_video" for it in evidence)
        assert all("sales" in it.limitation_note for it in evidence)


# 9. web search tool invocation -> search_public_web executed with structured EvidenceItem output
def test_web_search_tool_invocation():
    provider = PublicWebSearchProvider()
    items = provider.search_public_web("stationery brands")
    assert isinstance(items, list)
    if items:
        assert all(it.source_type == "web_search" for it in items)
        assert all(it.source_url is not None for it in items)


# 10. analytics tool invocation -> get_market_snapshot executed on verified data
def test_analytics_tool_invocation():
    engine = AnalyticsToolsEngine()
    data, evidence = engine.get_market_snapshot(category="D2C Footwear")
    assert data["benchmarks"]["total_active_products"] == 2050
    assert data["benchmarks"]["total_active_skus"] == 10576
    assert len(evidence) == 4


# 11. mixed research + analytics query -> executes research + data availability for non-footwear
def test_mixed_research_query(orchestrator):
    # Establish stationery context first
    orchestrator.process_turn("I run a stationery brand.")
    # Ask market question
    res = orchestrator.process_turn("What is happening in my market?")
    assert res.is_clarification is False
    assert "Data Availability: Stationery" in res.narrative
    assert "Public Research" in res.narrative


# 12. follow-up query using conversation context
def test_followup_query_using_context(orchestrator):
    orchestrator.process_turn("I run a stationery brand called PaperCrafters.")
    assert orchestrator.context.brand_name == "PaperCrafters"
    assert orchestrator.context.industry == "Stationery"

    # Follow-up
    res = orchestrator.process_turn("Where am I lacking?")
    assert "PaperCrafters" in res.brand_context.brand_name
    assert res.brand_context.industry == "Stationery"


# 13. unknown industry -> explains that BrandSignal does not have warehouse data
def test_unknown_industry_handling():
    engine = AnalyticsToolsEngine()
    data, evidence = engine.get_data_availability(industry="Aerospace")
    assert data["available"] is False
    assert "Structured catalog and benchmark dataset is not available" in data["message"]
    assert len(evidence) == 1
    assert evidence[0].value["available"] is False


# 14. missing LLM key -> raises clear LLMConfigurationError, does not pretend LLM ran
def test_missing_llm_key_error(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    provider = GeminiProvider(api_key=None)
    with pytest.raises(LLMConfigurationError) as exc_info:
        provider.plan_tools("What's happening in my market?", BrandContext())
    assert "Gemini API key is required" in str(exc_info.value)

    with pytest.raises(LLMConfigurationError):
        get_llm_provider(require_llm=True)


# 15. missing YouTube key -> YouTube tool reports unavailable gracefully without crashing
def test_missing_youtube_key(monkeypatch):
    monkeypatch.delenv("YOUTUBE_API_KEY", raising=False)
    yt = YouTubeContentProvider(api_key="")
    assert yt.is_available is False
    res = yt.search("test query")
    assert res.success is False
    assert "YouTube provider is unconfigured" in res.error_message
    assert len(res.evidence_items) == 0



# 16. provider failure -> web search failure handled gracefully without crashing
def test_provider_failure_handling(monkeypatch):
    provider = PublicWebSearchProvider()
    with patch("urllib.request.urlopen", side_effect=Exception("Connection reset by peer")):
        res = provider.search("test query")
        assert res.success is False
        assert "Public web search unavailable" in res.error_message
        assert len(res.evidence_items) == 0


# 17. evidence provenance -> every cited item traced in EvidenceStore with valid provenance
def test_evidence_provenance(orchestrator):
    orchestrator.set_brand_context(BrandContext(
        brand_name="Neeman's",
        industry="Footwear",
        is_demo_vertical=True,
        demo_brand_id="neemans"
    ))
    res = orchestrator.process_turn("What is happening in my market?")
    assert len(res.cited_evidence) > 0
    for it in res.cited_evidence:
        stored = orchestrator.evidence_store.get(it.evidence_id)
        assert stored is not None
        assert stored.evidence_id == it.evidence_id
        assert stored.source_name is not None
    assert "### 📑 Evidence & Source Provenance" in res.why_are_you_saying_this_md


# 18. evidence token leakage -> raw internal evidence IDs do NOT leak into user-facing narrative text
def test_evidence_token_leakage(orchestrator):
    orchestrator.set_brand_context(BrandContext(
        brand_name="Bacca Bucci",
        industry="Footwear",
        is_demo_vertical=True,
        demo_brand_id="baccabucci"
    ))
    res = orchestrator.process_turn("What is happening in my market?")
    # Narrative must not contain raw tokens like [EVID-SNAP-BACCABUCCI]
    assert "[EVID-" not in res.narrative
    assert "[EVID" not in res.narrative


# 19. hallucinated tool rejection -> tool planning rejecting tools that do not exist in ToolRegistry
def test_hallucinated_tool_rejection():
    registry = ToolRegistry()
    assert registry.is_registered("get_market_snapshot") is True
    assert registry.is_registered("hallucinated_magic_tool") is False

    res = registry.execute_tool(ToolCall(tool_name="hallucinated_magic_tool", arguments={}))
    assert res.success is False
    assert "Unrecognized or unregistered tool" in res.error


# 20. hallucinated metric rejection -> synthesis cannot cite evidence IDs that were not returned by executed tools
def test_hallucinated_metric_rejection(orchestrator):
    store = orchestrator.evidence_store
    # Try to verify an ID that was never added
    valid, missing = store.verify_citations(["EVID-FAKE-99999", "EVID-HALLUCINATED"])
    assert len(valid) == 0
    assert "EVID-FAKE-99999" in missing
    assert "EVID-HALLUCINATED" in missing
