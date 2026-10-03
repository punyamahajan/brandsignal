from typing import Dict, Any, List, Optional

from src.research.base import ResearchProvider, ResearchResult
from src.research.web_search import WebSearchProvider
from src.research.brand_site import BrandSiteProvider
from src.research.trends import SearchTrendsProvider
from src.research.reddit import RedditDiscussionProvider
from src.research.youtube import YouTubeContentProvider
from src.evidence.models import EvidenceItem

class SourceRegistry:
    """
    Central registry for public market intelligence adapters.
    Manages provider lifecycles, configuration statuses, and research orchestration.
    """

    def __init__(self):
        self._providers: Dict[str, ResearchProvider] = {
            "web_search": WebSearchProvider(),
            "brand_site": BrandSiteProvider(),
            "trends": SearchTrendsProvider(),
            "reddit": RedditDiscussionProvider(),
            "youtube": YouTubeContentProvider()
        }

    def register_provider(self, provider: ResearchProvider) -> None:
        """Enables runtime addition of custom or third-party research adapters."""
        self._providers[provider.name] = provider

    def get_provider(self, name: str) -> Optional[ResearchProvider]:
        return self._providers.get(name)

    def list_providers(self) -> List[Dict[str, Any]]:
        """Reports the operational readiness and requirements of all registered research adapters."""
        status_list = []
        for name, p in self._providers.items():
            status_list.append({
                "name": name,
                "is_available": p.is_available,
                "status_description": p.status_description
            })
        return status_list

    def research_brand_or_category(self, query: str, provider_names: Optional[List[str]] = None) -> List[EvidenceItem]:
        """
        Executes multi-source research across available providers.
        Returns combined, validated EvidenceItem list.
        """
        targets = provider_names or ["web_search", "brand_site", "trends", "reddit"]
        combined_evidence: List[EvidenceItem] = []

        for name in targets:
            provider = self._providers.get(name)
            if provider and provider.is_available:
                try:
                    res: ResearchResult = provider.search(query)
                    if res.success and res.evidence_items:
                        combined_evidence.extend(res.evidence_items)
                except Exception:
                    continue

        return combined_evidence
