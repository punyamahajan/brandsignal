import os
import time
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

from src.research.base import ResearchProvider, ResearchResult
from src.evidence.models import EvidenceItem

class YouTubeContentProvider(ResearchProvider):
    """
    YouTube video reviews and creator content metadata provider.
    Requires YOUTUBE_API_KEY environment variable. Fails gracefully if unconfigured.
    Never exposes API key. Public video metadata only; does NOT represent sales volume or market share.
    """

    def __init__(self, api_key: Optional[str] = None):
        super().__init__(politeness_delay_sec=1.0)
        self.api_key = api_key if api_key is not None else os.getenv("YOUTUBE_API_KEY")

    @property
    def name(self) -> str:
        return "youtube"

    @property
    def is_available(self) -> bool:
        return bool(self.api_key and self.api_key.strip())

    @property
    def status_description(self) -> str:
        if self.is_available:
            return "Active (YouTube Data v3 API Key configured)"
        return "Unavailable (Requires YOUTUBE_API_KEY environment variable)"

    def search_youtube(self, query: str, max_results: int = 5) -> List[EvidenceItem]:
        """Direct tool entry point returning structured EvidenceItem list."""
        res = self.search(query, max_results=max_results)
        return res.evidence_items if res.success else []

    def search(self, query: str, **kwargs) -> ResearchResult:
        t0 = time.time()
        if not self.is_available:
            return ResearchResult(
                provider_name=self.name,
                query=query,
                success=False,
                error_message="YouTube provider is unconfigured. Set YOUTUBE_API_KEY environment variable to enable public video metadata research.",
                execution_time_ms=0.0
            )

        try:
            import requests

            max_results = min(int(kwargs.get("max_results", 5)), 10)
            url = "https://www.googleapis.com/youtube/v3/search"
            params = {
                "part": "snippet",
                "q": query,
                "maxResults": max_results,
                "type": "video",
                "key": self.api_key
            }

            resp = requests.get(url, params=params, timeout=10)
            if resp.status_code != 200:
                return ResearchResult(
                    provider_name=self.name,
                    query=query,
                    success=False,
                    error_message=f"YouTube Data API returned status {resp.status_code}.",
                    execution_time_ms=(time.time() - t0) * 1000.0
                )

            data = resp.json()
            items = data.get("items", [])
            evidence_items: List[EvidenceItem] = []

            for it in items:
                v_id = it.get("id", {}).get("videoId")
                snippet = it.get("snippet", {})
                if v_id:
                    v_title = snippet.get("title", "")
                    channel = snippet.get("channelTitle", "Creator")
                    published_at = snippet.get("publishTime") or snippet.get("publishedAt")
                    evidence_items.append(EvidenceItem(
                        evidence_id=f"EVID-YT-{v_id}",
                        source_name=f"YouTube: {channel}",
                        source_type="youtube_video",
                        source_url=f"https://www.youtube.com/watch?v={v_id}",
                        title=v_title,
                        published_at=published_at,
                        collected_at=datetime.now(timezone.utc).isoformat(),
                        query=query,
                        brand_id="youtube_content",
                        brand_name=channel,
                        metric="public_video_content",
                        observation=f"Public Video: '{v_title}' by {channel} (Published: {published_at})",
                        value={
                            "videoId": v_id,
                            "title": v_title,
                            "channelTitle": channel,
                            "publishTime": published_at
                        },
                        confidence=0.90,
                        raw_reference="youtube#searchResult",
                        limitation_note="Public video content metadata only; does NOT indicate sales volume or consumer market share."
                    ))

            return ResearchResult(
                provider_name=self.name,
                query=query,
                success=True,
                evidence_items=evidence_items,
                raw_response={"item_count": len(items)},
                execution_time_ms=(time.time() - t0) * 1000.0
            )
        except Exception as e:
            return ResearchResult(
                provider_name=self.name,
                query=query,
                success=False,
                error_message=f"YouTube API request exception: {str(e)}",
                execution_time_ms=(time.time() - t0) * 1000.0
            )
