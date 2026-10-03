import os
from typing import Dict, Optional

from src.orchestrator.service import ConversationalOrchestrator
from src.tools.analytics_tools import AnalyticsToolsEngine
from src.research.source_registry import SourceRegistry
from src.evidence.models import EvidenceStore
from src.llm.provider import get_llm_provider

# Global in-memory session cache for conversational orchestrators
_SESSIONS: Dict[str, ConversationalOrchestrator] = {}
_ANALYTICS_TOOLS: Optional[AnalyticsToolsEngine] = None
_SOURCE_REGISTRY: Optional[SourceRegistry] = None
_GLOBAL_EVIDENCE_STORE: Optional[EvidenceStore] = None

def get_analytics_tools() -> AnalyticsToolsEngine:
    global _ANALYTICS_TOOLS
    if _ANALYTICS_TOOLS is None:
        _ANALYTICS_TOOLS = AnalyticsToolsEngine()
    return _ANALYTICS_TOOLS

def get_source_registry() -> SourceRegistry:
    global _SOURCE_REGISTRY
    if _SOURCE_REGISTRY is None:
        _SOURCE_REGISTRY = SourceRegistry()
    return _SOURCE_REGISTRY

def get_evidence_store() -> EvidenceStore:
    global _GLOBAL_EVIDENCE_STORE
    if _GLOBAL_EVIDENCE_STORE is None:
        _GLOBAL_EVIDENCE_STORE = EvidenceStore()
    return _GLOBAL_EVIDENCE_STORE

def get_orchestrator(session_id: str = "default") -> ConversationalOrchestrator:
    """
    Returns the persistent ConversationalOrchestrator instance for the given session_id.
    Creates a new instance if one does not exist.
    """
    global _SESSIONS
    if session_id not in _SESSIONS:
        ev_store = get_evidence_store()
        llm = get_llm_provider()
        _SESSIONS[session_id] = ConversationalOrchestrator(
            llm_provider=llm,
            evidence_store=ev_store
        )
    return _SESSIONS[session_id]

def reset_session(session_id: str = "default") -> None:
    """Clears conversational history and context for a session."""
    global _SESSIONS
    if session_id in _SESSIONS:
        del _SESSIONS[session_id]
