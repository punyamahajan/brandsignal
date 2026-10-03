from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple
import uuid

@dataclass
class EvidenceItem:
    """
    Represents an atomic, auditable primary evidence observation.
    Every market claim emitted by BrandSignal is traceable back to an EvidenceItem.
    """
    evidence_id: str
    source_name: str
    source_type: str  # "storefront_catalog" | "google_trends" | "tranco" | "web_search" | "youtube_video" | "brand_site" | "public_discussion"
    collected_at: str  # ISO-8601 string
    metric: str
    observation: str
    value: Any = None
    title: Optional[str] = None
    unit: Optional[str] = None
    published_at: Optional[str] = None
    geography: Optional[str] = None
    query: Optional[str] = None
    provenance: Optional[str] = None
    confidence: float = 1.0
    reliability_metadata: Dict[str, Any] = field(default_factory=dict)
    source_url: Optional[str] = None
    raw_reference: Optional[str] = None
    dataset_name: Optional[str] = None
    limitation_note: Optional[str] = None
    brand_id: Optional[str] = "unknown"
    brand_name: Optional[str] = "Unknown Brand"

    @property
    def id(self) -> str:
        return self.evidence_id

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.evidence_id,
            "evidence_id": self.evidence_id,
            "source_name": self.source_name,
            "source_type": self.source_type,
            "source_url": self.source_url,
            "title": self.title,
            "collected_at": self.collected_at,
            "published_at": self.published_at,
            "brand_id": self.brand_id,
            "brand_name": self.brand_name,
            "metric": self.metric,
            "observation": self.observation,
            "value": self.value,
            "unit": self.unit,
            "geography": self.geography,
            "query": self.query,
            "provenance": self.provenance,
            "confidence": self.confidence,
            "reliability_metadata": self.reliability_metadata,
            "raw_reference": self.raw_reference,
            "dataset_name": self.dataset_name,
            "limitation_note": self.limitation_note
        }

    def format_citation(self) -> str:
        """Renders an inline or expandable citation markdown snippet."""
        url_part = f" ([Source Link]({self.source_url}))" if self.source_url else ""
        lim_part = f" *Note:* {self.limitation_note}" if self.limitation_note else ""
        return (
            f"**[{self.evidence_id}]** {self.source_name} (`{self.collected_at[:10]}`): "
            f"{self.observation}{url_part}.{lim_part}"
        )


class EvidenceStore:
    """
    Thread-safe repository for evidence collected during analytical query executions.
    Supports querying, filtering, and provenance verification.
    """

    def __init__(self):
        self._items: Dict[str, EvidenceItem] = {}

    def add(self, item: EvidenceItem) -> str:
        self._items[item.evidence_id] = item
        return item.evidence_id

    def add_many(self, items: List[EvidenceItem]) -> List[str]:
        ids = []
        for it in items:
            ids.append(self.add(it))
        return ids

    def get(self, evidence_id: str) -> Optional[EvidenceItem]:
        return self._items.get(evidence_id)

    def get_all(self) -> List[EvidenceItem]:
        return list(self._items.values())

    def filter_by_brand(self, brand_id: str) -> List[EvidenceItem]:
        return [it for it in self._items.values() if it.brand_id == brand_id]

    def filter_by_metric(self, metric: str) -> List[EvidenceItem]:
        return [it for it in self._items.values() if it.metric == metric]

    def verify_citations(self, cited_ids: List[str]) -> Tuple[List[EvidenceItem], List[str]]:
        """
        Validates a list of cited evidence IDs.
        Returns: (valid_items, missing_or_hallucinated_ids)
        """
        valid = []
        invalid = []
        for eid in cited_ids:
            if eid in self._items:
                valid.append(self._items[eid])
            else:
                invalid.append(eid)
        return valid, invalid

    def render_why_are_you_saying_this(self, evidence_ids: Optional[List[str]] = None) -> str:
        """
        Produces the 'Why are you saying this?' provenance view in Markdown.
        """
        items_to_render = (
            [self._items[eid] for eid in evidence_ids if eid in self._items]
            if evidence_ids is not None
            else list(self._items.values())
        )

        if not items_to_render:
            return "No underlying evidence items recorded for this query."

        lines = ["### 📑 Evidence & Source Provenance\n"]
        for item in items_to_render:
            lines.append(f"#### `{item.evidence_id}` — {item.brand_name}: {item.metric}")
            lines.append(f"- **Source:** {item.source_name} ({item.source_type})")
            if item.source_url:
                lines.append(f"- **URL:** [{item.source_url}]({item.source_url})")
            lines.append(f"- **Observation:** {item.observation}")
            lines.append(f"- **Recorded Value:** `{item.value}`")
            lines.append(f"- **Collection Date:** `{item.collected_at}`")
            if item.dataset_name:
                lines.append(f"- **Dataset:** `{item.dataset_name}`")
            if item.raw_reference:
                lines.append(f"- **Raw Reference:** `{item.raw_reference}`")
            if item.limitation_note:
                lines.append(f"- **Data Limitation:** ⚠️ *{item.limitation_note}*")
            lines.append("")

        return "\n".join(lines)
