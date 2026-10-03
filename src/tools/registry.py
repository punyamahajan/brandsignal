from typing import Dict, Any, List, Optional, Callable, Set

from src.evidence.models import EvidenceStore, EvidenceItem
from src.llm.schemas import ToolCall, ToolResult
from src.tools.analytics_tools import AnalyticsToolsEngine

class ToolRegistry:
    """
    Central execution dispatcher for analytical and research tools.
    Safely executes tool calls against AnalyticsToolsEngine, populates EvidenceStore,
    and returns standardized ToolResult objects.
    Rejects any hallucinated or unregistered tool calls.
    """

    STRUCTURED_ANALYTICS_TOOLS: Set[str] = {
        "get_market_snapshot",
        "compare_brands",
        "compare_prices",
        "compare_assortment",
        "get_category_mix",
        "get_search_trends",
        "get_recent_changes",
        "find_brand_gaps",
        "get_data_availability",
        "find_competitors"
    }

    RESEARCH_TOOLS: Set[str] = {
        "search_public_web",
        "search_brand_site",
        "search_youtube",
        "search_public_sources"
    }

    ALL_REGISTERED_TOOLS: Set[str] = STRUCTURED_ANALYTICS_TOOLS | RESEARCH_TOOLS

    def __init__(self, evidence_store: Optional[EvidenceStore] = None):
        self.evidence_store = evidence_store or EvidenceStore()
        self.engine = AnalyticsToolsEngine()
        self._handlers: Dict[str, Callable[..., Any]] = {
            # Structured Analytics
            "get_market_snapshot": self.engine.get_market_snapshot,
            "find_competitors": self.engine.find_competitors,
            "compare_brands": self.engine.compare_brands,
            "find_brand_gaps": self.engine.find_brand_gaps,
            "compare_prices": self.engine.compare_prices,
            "compare_discounting": self.engine.compare_discounting,
            "compare_assortment": self.engine.compare_assortment,
            "get_search_trends": self.engine.get_search_trends,
            "get_recent_changes": self.engine.get_recent_changes,
            "get_category_mix": self.engine.get_category_mix,
            "get_data_availability": self.engine.get_data_availability,
            # Research
            "search_public_web": self.engine.search_public_web,
            "search_brand_site": self.engine.search_brand_site,
            "search_youtube": self.engine.search_youtube,
            "search_public_sources": self.engine.search_public_sources
        }

    def is_registered(self, tool_name: str) -> bool:
        """Verifies if a tool name is registered in the system."""
        return tool_name in self._handlers

    def execute_tool(self, call: ToolCall) -> ToolResult:
        """Executes a single tool call and records all generated evidence items."""
        if not self.is_registered(call.tool_name):
            return ToolResult(
                tool_name=call.tool_name,
                success=False,
                error=f"Unrecognized or unregistered tool '{call.tool_name}'. Tool execution rejected."
            )

        handler = self._handlers[call.tool_name]
        try:
            data, evidence_items = handler(**call.arguments)
            # Store evidence in audit store
            ev_ids = self.evidence_store.add_many(evidence_items)

            return ToolResult(
                tool_name=call.tool_name,
                success=True,
                data=data,
                evidence_ids=ev_ids
            )
        except Exception as e:
            return ToolResult(
                tool_name=call.tool_name,
                success=False,
                error=f"Tool execution failed: {str(e)}"
            )

    def execute_many(self, calls: List[ToolCall]) -> List[ToolResult]:
        return [self.execute_tool(c) for c in calls]
