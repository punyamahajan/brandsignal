from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple

@dataclass
class CandidateCompetitor:
    """
    Structured representation of a candidate competitor discovered for a brand or category.
    Includes provenance, source URL, and confidence metadata.
    """
    brand: str
    category: str
    geography: Optional[str] = None
    reason: str = ""
    source: str = ""
    source_url: Optional[str] = None
    confidence: float = 1.0
    quality_metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "brand": self.brand,
            "category": self.category,
            "geography": self.geography,
            "reason": self.reason,
            "source": self.source,
            "source_url": self.source_url,
            "confidence": self.confidence,
            "quality_metadata": self.quality_metadata
        }


class CompetitorDiscoveryProvider(ABC):
    """
    Abstract interface for dynamic and catalog-based competitor discovery.
    Guarantees no hallucination or fabrication of competitors.
    """

    @abstractmethod
    def discover_competitors(
        self,
        industry: Optional[str] = None,
        category: Optional[str] = None,
        geography: Optional[str] = None,
        brand_context: Optional[Any] = None
    ) -> Tuple[List[CandidateCompetitor], Optional[str]]:
        """
        Discovers candidate competitors for a given industry/category.
        Returns:
            Tuple[List[CandidateCompetitor], Optional[str]]
            - list of CandidateCompetitor objects
            - status/unavailable message if discovery is not available for this market
        """
        pass


class HybridCompetitorDiscoveryProvider(CompetitorDiscoveryProvider):
    """
    Production competitor discovery provider.
    - Preserves verified footwear cohort as an explicit demo/benchmark dataset.
    - For unknown/arbitrary industries (e.g. stationery), returns a structured
      unavailable status without fabricating competitors.
    """

    # Verified benchmark cohort for demo purposes
    KNOWN_FOOTWEAR_BENCHMARK = [
        {"id": "baccabucci", "name": "Bacca Bucci", "category": "D2C Footwear", "geo": "IN"},
        {"id": "neemans", "name": "Neeman's", "category": "D2C Footwear", "geo": "IN"},
        {"id": "elevarsports", "name": "Elevar Sports", "category": "D2C Footwear", "geo": "IN"},
        {"id": "plaeto", "name": "Plaeto", "category": "D2C Footwear", "geo": "IN"},
    ]

    def discover_competitors(
        self,
        industry: Optional[str] = None,
        category: Optional[str] = None,
        geography: Optional[str] = None,
        brand_context: Optional[Any] = None
    ) -> Tuple[List[CandidateCompetitor], Optional[str]]:
        ind = (industry or (brand_context.industry if brand_context else "") or "").lower().strip()
        cat = (category or (brand_context.category if brand_context else "") or "").lower().strip()
        is_demo = getattr(brand_context, "is_demo_vertical", False) if brand_context else False
        demo_id = getattr(brand_context, "demo_brand_id", None) if brand_context else None

        # Explicit footwear demo cohort
        if is_demo or demo_id or ("footwear" in ind and is_demo):
            candidates = []
            for b in self.KNOWN_FOOTWEAR_BENCHMARK:
                if demo_id and b["id"] == demo_id:
                    continue
                candidates.append(CandidateCompetitor(
                    brand=b["name"],
                    category=b["category"],
                    geography=b["geo"],
                    reason="Verified Indian D2C Footwear Benchmark Cohort Member",
                    source="BrandSignal Verified Footwear Benchmark Registry",
                    source_url=f"https://{b['id']}.com" if b['id'] != "plaeto" else "https://plaeto.in",
                    confidence=1.0,
                    quality_metadata={"dataset": "fact_brand_snapshot_features", "verified": True}
                ))
            return candidates, None

        # Arbitrary/unsupported markets (e.g. stationery, beverages)
        market_label = category or industry or "this market"
        return [], f"Competitor discovery is not currently available for {market_label}."
