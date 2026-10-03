from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
import re

from src.orchestrator.context import BrandContext, BrandContextManager
from src.orchestrator.competitor_discovery import CompetitorDiscoveryProvider, HybridCompetitorDiscoveryProvider
from src.evidence.models import EvidenceStore, EvidenceItem
from src.llm.base import LLMProvider
from src.llm.provider import get_llm_provider
from src.llm.schemas import LLMPlan, ToolResult, SynthesizedResponse
from src.tools.registry import ToolRegistry

@dataclass
class OrchestratorResponse:
    """Full conversational turn response delivered to the presentation layer."""
    narrative: str
    brand_context: BrandContext
    cited_evidence: List[EvidenceItem] = field(default_factory=list)
    suggested_followups: List[str] = field(default_factory=list)
    visual_navigation_target: Optional[str] = None  # "Market" | "Competitors" | "Gaps" | "Trends" | "Evidence"
    visual_navigation_label: Optional[str] = None
    why_are_you_saying_this_md: str = ""
    is_clarification: bool = False

class ConversationalOrchestrator:
    """
    Master orchestrator for BrandSignal hybrid conversational intelligence.
    Maintains session memory, updates dynamic brand context, coordinates tool planning,
    executes deterministic tools against DuckDB/research sources, and verifies citations.
    Enforces strict zero-leakage, non-prescriptive, and fact-vs-interpretation boundaries.
    """

    def __init__(
        self,
        llm_provider: Optional[LLMProvider] = None,
        evidence_store: Optional[EvidenceStore] = None,
        competitor_provider: Optional[CompetitorDiscoveryProvider] = None
    ):
        self.evidence_store = evidence_store or EvidenceStore()
        self.llm_provider = llm_provider or get_llm_provider()
        self.tool_registry = ToolRegistry(evidence_store=self.evidence_store)
        self.competitor_provider = competitor_provider or HybridCompetitorDiscoveryProvider()
        self.context = BrandContext()
        self.history: List[Dict[str, str]] = []

    def set_brand_context(self, context: BrandContext) -> None:
        self.context = context

    def process_turn(self, query: str) -> OrchestratorResponse:
        """Processes a single conversational turn end-to-end."""
        # 1. Update brand context from natural language input
        self.context = BrandContextManager.extract_from_text(query, current_context=self.context)

        # 2. Plan tools via LLM provider
        plan: LLMPlan = self.llm_provider.plan_tools(
            query=query,
            context=self.context,
            history=self.history
        )

        # 3. Handle conversational clarification / onboarding / greetings
        if plan.clarification_needed and plan.clarification_question:
            self.history.append({"role": "user", "content": query})
            self.history.append({"role": "assistant", "content": plan.clarification_question})

            followups = [
                "I run a stationery brand.",
                "I run a D2C footwear brand.",
                "What data do you have in the warehouse?"
            ]
            if self.context.industry:
                followups = [
                    f"What is happening in {self.context.industry}?",
                    f"Search YouTube for {self.context.industry} reviews",
                    "What data is available in the warehouse?"
                ]

            return OrchestratorResponse(
                narrative=plan.clarification_question,
                brand_context=self.context,
                cited_evidence=[],
                suggested_followups=followups,
                is_clarification=True,
                why_are_you_saying_this_md="No empirical tools were executed for this greeting/clarification turn."
            )

        # 4. Validate and execute planned tools
        tool_results: List[ToolResult] = self.tool_registry.execute_many(plan.tool_calls)

        # 5. Synthesize evidence into natural language response
        synthesized: SynthesizedResponse = self.llm_provider.synthesize_response(
            query=query,
            context=self.context,
            tool_results=tool_results,
            history=self.history
        )

        # 6. Verify citations & reject hallucinated evidence IDs
        valid_items, missing_ids = self.evidence_store.verify_citations(synthesized.cited_evidence_ids)

        # 7. Zero Token Leakage: guarantee raw evidence IDs do not leak into narrative
        clean_narrative = re.sub(r'\[EVID-[^\]]+\]', '', synthesized.narrative)
        clean_narrative = re.sub(r'\s{2,}', ' ', clean_narrative).strip()

        # 8. Generate 'Why are you saying this?' provenance Markdown for audit
        why_md = self.evidence_store.render_why_are_you_saying_this(
            evidence_ids=[it.evidence_id for it in valid_items] if valid_items else None
        )

        # Update conversational history
        self.history.append({"role": "user", "content": query})
        self.history.append({"role": "assistant", "content": clean_narrative})

        return OrchestratorResponse(
            narrative=clean_narrative,
            brand_context=self.context,
            cited_evidence=valid_items,
            suggested_followups=synthesized.suggested_followups,
            visual_navigation_target=synthesized.visual_navigation_target or plan.visual_action,
            visual_navigation_label=synthesized.visual_navigation_label or f"Explore in {plan.visual_action} →",
            why_are_you_saying_this_md=why_md,
            is_clarification=False
        )
