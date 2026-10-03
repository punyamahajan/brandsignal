from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any, List, Optional

from backend.dependencies import get_evidence_store, get_orchestrator
from backend.schemas.chat import EvidenceItemSchema
from src.evidence.models import EvidenceStore, EvidenceItem

router = APIRouter(prefix="/api/evidence", tags=["evidence"])

@router.get("/{evidence_id}", response_model=EvidenceItemSchema)
def get_evidence_by_id(evidence_id: str, store: EvidenceStore = Depends(get_evidence_store)):
    """Retrieves full primary source provenance for a specific evidence identifier."""
    item = store.get(evidence_id)
    if not item:
        raise HTTPException(status_code=404, detail=f"Evidence item '{evidence_id}' not found.")
    return EvidenceItemSchema(**item.to_dict())

@router.get("/session/{session_id}", response_model=List[EvidenceItemSchema])
def get_session_evidence(session_id: str):
    """Retrieves all evidence records generated or cited during the session."""
    orch = get_orchestrator(session_id)
    items = orch.evidence_store.list_all()
    return [EvidenceItemSchema(**it.to_dict()) for it in items]

@router.get("/provenance/why-md")
def get_provenance_markdown(session_id: str = "default", store: EvidenceStore = Depends(get_evidence_store)):
    """Generates the Markdown audit trail for all active evidence."""
    orch = get_orchestrator(session_id)
    md = orch.evidence_store.render_why_are_you_saying_this()
    return {"markdown": md}
