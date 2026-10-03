from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional

class ToolCall(BaseModel):
    """Specification of an analytical or research tool invocation."""
    tool_name: str
    arguments: Dict[str, Any] = Field(default_factory=dict)

class ToolResult(BaseModel):
    """Output received from executing an analytical or research tool."""
    tool_name: str
    success: bool
    data: Dict[str, Any] = Field(default_factory=dict)
    evidence_ids: List[str] = Field(default_factory=list)
    error: Optional[str] = None

class LLMPlan(BaseModel):
    """Structured plan produced by the LLM from user query + brand context."""
    intent: str
    clarification_needed: bool = False
    clarification_question: Optional[str] = None
    tool_calls: List[ToolCall] = Field(default_factory=list)
    visual_action: Optional[str] = None

class SynthesizedResponse(BaseModel):
    """Final guardrailed response ready for presentation to the business owner."""
    narrative: str
    cited_evidence_ids: List[str] = Field(default_factory=list)
    suggested_followups: List[str] = Field(default_factory=list)
    visual_navigation_target: Optional[str] = None  # "Market" | "Competitors" | "Gaps" | "Trends" | "Evidence"
    visual_navigation_label: Optional[str] = None
