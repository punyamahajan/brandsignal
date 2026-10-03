import time
import re
import urllib.request
import urllib.parse
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

from src.research.base import ResearchProvider, ResearchResult
from src.evidence.models import EvidenceItem

class BrandSiteResearchProvider(ResearchProvider):
    """
    Brand storefront and website metadata analyzer.
    Extracts public brand identity, category tags, and storefront endpoints politely.
    Respects rate limits, politeness delays, and does not attempt CAPTCHA bypassing.
    """

    def __init__(self):
        super().__init__(politeness_delay_sec=2.0)

    @property
    def name(self) -> str:
        return "brand_site"

    @property
    def is_available(self) -> bool:
        return True

    @property
    def status_description(self) -> str:
        return "Active (Public HTTP storefront & meta parser with 2.0s delay)"

    def search_brand_site(self, domain_or_url: str) -> List[EvidenceItem]:
        """Direct tool entry point returning structured EvidenceItem list."""
        res = self.search(domain_or_url)
        return res.evidence_items if res.success else []

    def search(self, domain_or_url: str, **kwargs) -> ResearchResult:
        t0 = time.time()
        self.enforce_politeness()

        target_url = domain_or_url.strip()
        if not target_url.startswith("http://") and not target_url.startswith("https://"):
            target_url = f"https://{target_url}"

        evidence_items: List[EvidenceItem] = []
        try:
            req = urllib.request.Request(
                target_url,
                headers={"User-Agent": self.user_agent, "Accept": "text/html"}
            )
            with urllib.request.urlopen(req, timeout=6) as resp:
                html = resp.read(15000).decode("utf-8", errors="ignore")

            title_match = re.search(r"<title>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
            desc_match = re.search(r'<meta\s+name=["\']description["\']\s+content=["\'](.*?)["\']', html, re.IGNORECASE)

            title = title_match.group(1).strip() if title_match else domain_or_url
            description = desc_match.group(1).strip() if desc_match else "Official brand website storefront"
            is_shopify = "cdn.shopify.com" in html or "Shopify.theme" in html

            item = EvidenceItem(
                evidence_id=f"EVID-SITE-{int(time.time()*1000)%100000}",
                source_name=f"Official Brand Domain ({domain_or_url})",
                source_type="brand_site",
                source_url=target_url,
                title=title[:80],
                collected_at=datetime.now(timezone.utc).isoformat(),
                brand_id=domain_or_url.replace(".", "_").replace("/", "_"),
                brand_name=title[:30],
                metric="storefront_metadata",
                observation=f"Meta Description: {description[:150]} (Platform: {'Shopify' if is_shopify else 'Custom'})",
                value={"title": title, "is_shopify": is_shopify, "description": description[:150]},
                confidence=0.95,
                dataset_name="Official Domain Metadata",
                limitation_note="Subject to merchant website availability and robots.txt permissions."
            )
            evidence_items.append(item)

            return ResearchResult(
                provider_name=self.name,
                query=domain_or_url,
                success=True,
                evidence_items=evidence_items,
                raw_data={"url": target_url, "title": title, "is_shopify": is_shopify},
                execution_time_ms=(time.time() - t0) * 1000.0
            )
        except Exception as e:
            return ResearchResult(
                provider_name=self.name,
                query=domain_or_url,
                success=False,
                error_message=f"Brand website inspection unavailable or timed out: {e}",
                execution_time_ms=(time.time() - t0) * 1000.0
            )

# Backward-compatible alias
BrandSiteProvider = BrandSiteResearchProvider
