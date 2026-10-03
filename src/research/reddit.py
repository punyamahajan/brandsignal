import time
import urllib.parse
import urllib.request
import json
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

from src.research.base import ResearchProvider, ResearchResult
from src.evidence.models import EvidenceItem

class RedditDiscussionProvider(ResearchProvider):
    """
    Public Reddit discussion and community sentiment research adapter.
    Queries public subreddit threads with strict politeness delays and custom User-Agent.
    """

    def __init__(self):
        super().__init__(politeness_delay_sec=2.0)

    @property
    def name(self) -> str:
        return "reddit"

    @property
    def is_available(self) -> bool:
        return True

    @property
    def status_description(self) -> str:
        return "Active (Public Reddit JSON API with 2.0s politeness delay)"

    def search(self, query: str, **kwargs) -> ResearchResult:
        t0 = time.time()
        self.enforce_politeness()

        evidence_items = []
        try:
            encoded = urllib.parse.quote_plus(query)
            url = f"https://www.reddit.com/search.json?q={encoded}&limit=3&sort=relevance"
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "BrandSignalMarketResearch/1.0 (academic analysis; contact@brandsignal.dev)"}
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode("utf-8"))

            posts = data.get("data", {}).get("children", [])
            for p in posts[:2]:
                p_data = p.get("data", {})
                title = p_data.get("title", "")
                sub = p_data.get("subreddit_name_prefixed", "r/all")
                score = p_data.get("score", 0)
                permalink = f"https://reddit.com{p_data.get('permalink', '')}"

                item = EvidenceItem(
                    evidence_id=f"EVID-REDDIT-{int(time.time()*1000)%100000}",
                    source_name=f"Reddit Community Discussion ({sub})",
                    source_type="public_discussion",
                    source_url=permalink,
                    collected_at=datetime.now(timezone.utc).isoformat(),
                    brand_id="public_community",
                    brand_name=query.title(),
                    metric="public_discussion_thread",
                    observation=f"Discussion Thread: '{title[:120]}' (Upvotes: {score})",
                    value={"subreddit": sub, "score": score, "title": title},
                    confidence=0.80,
                    dataset_name="Public Reddit API",
                    limitation_note="Unstructured public opinion; does not represent statistically sampled consumer sentiment."
                )
                evidence_items.append(item)

            return ResearchResult(
                provider_name=self.name,
                query=query,
                success=True,
                evidence_items=evidence_items,
                raw_data={"thread_count": len(posts)},
                execution_time_ms=(time.time() - t0) * 1000.0
            )
        except Exception as e:
            # Handle rate limiting or network unavailability cleanly
            return ResearchResult(
                provider_name=self.name,
                query=query,
                success=False,
                error_message=f"Reddit public discussion search rate-limited or unavailable: {e}",
                execution_time_ms=(time.time() - t0) * 1000.0
            )
