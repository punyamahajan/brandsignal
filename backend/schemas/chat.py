from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

class ChatMessageRequest(BaseModel):
    message: str
    session_id: Optional[str] = "default"
    brand_context: Optional[Dict[str, Any]] = None

class EvidenceItemSchema(BaseModel):
    evidence_id: str
    source_name: str
    source_type: str
    source_url: Optional[str] = None
    collected_at: str
    brand_id: Optional[str] = None
    brand_name: Optional[str] = None
    metric: str
    observation: str
    value: Any = None
    raw_reference: Optional[str] = None
    dataset_name: Optional[str] = None
    limitation_note: Optional[str] = None

class ChatMessageResponse(BaseModel):
    session_id: str
    narrative: str
    brand_context: Dict[str, Any]
    cited_evidence: List[EvidenceItemSchema] = Field(default_factory=list)
    suggested_followups: List[str] = Field(default_factory=list)
    visual_navigation_target: Optional[str] = None
    visual_navigation_label: Optional[str] = None
    why_are_you_saying_this_md: str = ""
    is_clarification: bool = False
