import os
import time
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
import urllib.parse
import urllib.request
import json

from src.research.base import ResearchProvider, ResearchResult
from src.evidence.models import EvidenceItem

class PublicWebSearchProvider(ResearchProvider):
    """
    Public web search adapter for brand and category market intelligence.
    Uses public knowledge and search endpoints politely with rate limiting.
    Fails gracefully if unconfigured or network is unavailable; never fabricates results.
    """

    def __init__(self, api_key: Optional[str] = None):
        super().__init__(politeness_delay_sec=1.5)
        self.api_key = api_key or os.getenv("SERPAPI_API_KEY")

    @property
    def name(self) -> str:
        return "web_search"

    @property
    def is_available(self) -> bool:
        return True  # Fallback to public knowledge endpoint

    @property
    def status_description(self) -> str:
        if self.api_key:
            return "Active (SerpAPI Key configured)"
        return "Active (Public search endpoint with politeness throttling)"

    def search_public_web(self, query: str) -> List[EvidenceItem]:
        """Direct tool entry point returning structured EvidenceItem list."""
        res = self.search(query)
        return res.evidence_items if res.success else []

    def search(self, query: str, **kwargs) -> ResearchResult:
        t0 = time.time()
        self.enforce_politeness()

        evidence_items: List[EvidenceItem] = []
        try:
            encoded = urllib.parse.quote_plus(query)
            url = f"https://api.duckduckgo.com/?q={encoded}&format=json&no_html=1&skip_disambig=1"
            req = urllib.request.Request(url, headers={"User-Agent": self.user_agent})
            
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode("utf-8"))

            abstract = data.get("AbstractText", "")
            heading = data.get("Heading", query)
            source_url = data.get("AbstractURL", "")

            # If instant answer exists
            if abstract:
                item = EvidenceItem(
                    evidence_id=f"EVID-WEB-{int(time.time()*1000)%100000}",
                    source_name=f"Public Web: {data.get('AbstractSource', 'Search Index')}",
                    source_type="web_search",
                    source_url=source_url or "https://duckduckgo.com",
                    title=heading,
                    collected_at=datetime.now(timezone.utc).isoformat(),
                    query=query,
                    brand_id="public_web",
                    brand_name=heading,
                    metric="public_web_overview",
                    observation=abstract[:250],
                    value={"abstract": abstract[:250], "heading": heading},
                    confidence=0.85,
                    dataset_name="Public Web Search",
                    limitation_note="Public search index snippet; subject to search engine indexing freshness."
                )
                evidence_items.append(item)

            # Check related topics
            topics = data.get("RelatedTopics", [])
            for t in topics[:2]:
                if isinstance(t, dict) and "Text" in t:
                    t_text = t.get("Text", "")
                    t_url = t.get("FirstURL", "")
                    if t_text:
                        evidence_items.append(EvidenceItem(
                            evidence_id=f"EVID-WEB-{int(time.time()*1000 + len(evidence_items))%100000}",
                            source_name="Public Web: Related Knowledge",
                            source_type="web_search",
                            source_url=t_url or "https://duckduckgo.com",
                            title=t_text[:50],
                            collected_at=datetime.now(timezone.utc).isoformat(),
                            query=query,
                            brand_id="public_web",
                            brand_name=heading,
                            metric="public_web_topic",
                            observation=t_text[:200],
                            value=t_text[:100],
                            confidence=0.80,
                            dataset_name="Public Web Search",
                            limitation_note="Aggregated search topic snippet."
                        ))

            return ResearchResult(
                provider_name=self.name,
                query=query,
                success=True,
                evidence_items=evidence_items,
                raw_data={"heading": heading, "result_count": len(evidence_items)},
                execution_time_ms=(time.time() - t0) * 1000.0
            )
        except Exception as e:
            return ResearchResult(
                provider_name=self.name,
                query=query,
                success=False,
                error_message=f"Public web search unavailable or timed out: {e}",
                execution_time_ms=(time.time() - t0) * 1000.0
            )

# Backward-compatible alias
WebSearchProvider = PublicWebSearchProvider
