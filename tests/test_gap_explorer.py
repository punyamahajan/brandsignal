import pytest
from src.tools.analytics_tools import AnalyticsToolsEngine

@pytest.fixture
def analytics_engine():
    return AnalyticsToolsEngine()

def test_gap_explorer_detects_observable_differences(analytics_engine):
    """
    Verifies that the Gap Explorer detects:
    1. Unrepresented categories in target brand (e.g. Plaeto lacks Boots, Running)
    2. Style breadth delta vs peer peak
    3. Option / variant density delta
    """
    data, evidence = analytics_engine.find_brand_gaps("plaeto")

    assert "missing_categories" in data
    assert len(data["missing_categories"]) > 0
    assert "Boots" in data["missing_categories"]
    assert data["style_breadth_difference"] > 0
    assert data["max_peer_styles"] == 1077
    assert len(evidence) == 1
    assert "EVID-GAP-PLAETO" in evidence[0].evidence_id

def test_gap_explorer_strict_non_prescriptive_guardrail(analytics_engine):
    """
    CRITICAL METHODOLOGICAL REQUIREMENT:
    Gap Explorer must NOT recommend actions (e.g. 'you should launch X').
    It must explicitly disclaimer that observed differences do NOT constitute strategic advice.
    """
    data, evidence = analytics_engine.find_brand_gaps("plaeto")
    ev_item = evidence[0]

    assert "does NOT constitute strategic advice" in ev_item.limitation_note or "does NOT constitute" in ev_item.limitation_note
    # Verify no prescriptive words in observation
    obs_lower = ev_item.observation.lower()
    for forbidden in ["you should", "we recommend", "strategy", "must launch", "ought to"]:
        assert forbidden not in obs_lower

def test_bacca_bucci_gap_analysis(analytics_engine):
    """Bacca Bucci has the broadest style catalog, so its style gap should be 0."""
    data, evidence = analytics_engine.find_brand_gaps("baccabucci")
    assert data["style_breadth_difference"] == 0
    assert len(evidence) == 1
