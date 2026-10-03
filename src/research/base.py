from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
import time

from src.evidence.models import EvidenceItem

@dataclass
class ResearchResult:
    """Standardized response from an external research provider."""
    provider_name: str
    query: str
    success: bool
    evidence_items: List[EvidenceItem] = field(default_factory=list)
    raw_data: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    status_code: Optional[int] = None
    execution_time_ms: float = 0.0


class ResearchProvider(ABC):
    """
    Abstract interface for public market intelligence adapters.
    Adheres strictly to politeness delays, rate limits, and transparent error handling.
    """

    def __init__(self, politeness_delay_sec: float = 1.0, user_agent: Optional[str] = None):
        self.politeness_delay_sec = politeness_delay_sec
        self.user_agent = user_agent or "BrandSignalResearch/1.0 (academic/market analysis; contact@brandsignal.dev)"
        self._last_request_time = 0.0

    def enforce_politeness(self) -> None:
        """Enforces rate-limiting politeness delays between sequential requests."""
        elapsed = time.time() - self._last_request_time
        if elapsed < self.politeness_delay_sec:
            time.sleep(self.politeness_delay_sec - elapsed)
        self._last_request_time = time.time()

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider identifier."""
        pass

    @property
    @abstractmethod
    def is_available(self) -> bool:
        """Indicates if the provider has necessary credentials and network readiness."""
        pass

    @property
    @abstractmethod
    def status_description(self) -> str:
        """Human-readable explanation of provider readiness."""
        pass

    @abstractmethod
    def search(self, query: str, **kwargs) -> ResearchResult:
        """Executes a research query and converts findings into verified EvidenceItem objects."""
        pass
