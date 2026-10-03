import pytest
from src.research import SourceRegistry, ResearchProvider, ResearchResult
from src.research.web_search import WebSearchProvider
from src.research.brand_site import BrandSiteProvider
from src.research.trends import SearchTrendsProvider
from src.research.reddit import RedditDiscussionProvider
from src.research.youtube import YouTubeContentProvider

def test_source_registry_registration_and_listing():
    reg = SourceRegistry()
    providers = reg.list_providers()
    names = [p["name"] for p in providers]

    assert "web_search" in names
    assert "brand_site" in names
    assert "trends" in names
    assert "reddit" in names
    assert "youtube" in names

def test_unconfigured_youtube_fails_gracefully(monkeypatch):
    """
    CRITICAL REQUIREMENT:
    If live access/API credentials are unavailable, clearly mark unavailable providers
    rather than fabricating data.
    """
    monkeypatch.delenv("YOUTUBE_API_KEY", raising=False)
    yt = YouTubeContentProvider(api_key=None)
    assert yt.is_available is False
    assert "Requires YOUTUBE_API_KEY" in yt.status_description

    res = yt.search("footwear reviews")
    assert res.success is False
    assert "unconfigured" in res.error_message.lower()
    assert len(res.evidence_items) == 0

def test_trends_provider_offline_duckdb():
    trends = SearchTrendsProvider()
    assert trends.is_available is True
    res = trends.search("neemans")
    assert res.success is True
    assert len(res.evidence_items) > 0
    assert res.evidence_items[0].source_type == "google_trends"
    assert "relative_search_interest" in res.evidence_items[0].metric

def test_politeness_delay_enforcement():
    provider = WebSearchProvider()
    assert provider.politeness_delay_sec >= 1.0
    t_start = provider._last_request_time
    provider.enforce_politeness()
    assert provider._last_request_time >= t_start
