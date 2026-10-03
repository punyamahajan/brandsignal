from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional

from src.orchestrator.context import BrandContext
from src.llm.schemas import LLMPlan, SynthesizedResponse, ToolResult

class LLMConfigurationError(Exception):
    """Raised when an LLM provider is invoked without a configured API key."""
    pass

class LLMProvider(ABC):
    """
    Abstract Base Class for LLM reasoning and synthesis providers.
    Decouples BrandSignal orchestration from specific model vendors.
    """

    @abstractmethod
    def plan_tools(
        self,
        query: str,
        context: BrandContext,
        history: Optional[List[Dict[str, str]]] = None
    ) -> LLMPlan:
        """
        Interprets natural language inquiry and maps to structured tool calls or clarification questions.
        """
        pass

    @abstractmethod
    def synthesize_response(
        self,
        query: str,
        context: BrandContext,
        tool_results: List[ToolResult],
        history: Optional[List[Dict[str, str]]] = None
    ) -> SynthesizedResponse:
        """
        Synthesizes tool output and verified evidence items into a guardrailed factual narrative.
        """
        pass
