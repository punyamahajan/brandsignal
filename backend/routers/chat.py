from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from typing import Dict, Any, List, Optional
import json
import asyncio

from backend.dependencies import get_orchestrator
from backend.schemas.chat import ChatMessageRequest, ChatMessageResponse, EvidenceItemSchema
from src.orchestrator.service import ConversationalOrchestrator, OrchestratorResponse
from src.orchestrator.context import BrandContext

router = APIRouter(prefix="/api/chat", tags=["chat"])

@router.post("/message", response_model=ChatMessageResponse)
def send_chat_message(req: ChatMessageRequest):
    """
    Core conversational intelligence endpoint.
    Maintains session state, invokes LLM tool planning, executes deterministic
    DuckDB analytics and public research adapters, and verifies all citations.
    """
    session_id = req.session_id or "default"
    orch: ConversationalOrchestrator = get_orchestrator(session_id)

    # If brand context overrides provided in request, apply them
    if req.brand_context:
        ctx = orch.context
        ctx.update_from_dict(req.brand_context)
        orch.set_brand_context(ctx)

    # Process conversational turn
    res: OrchestratorResponse = orch.process_turn(req.message)

    return ChatMessageResponse(
        session_id=session_id,
        narrative=res.narrative,
        brand_context=res.brand_context.to_dict(),
        cited_evidence=[EvidenceItemSchema(**it.to_dict()) for it in res.cited_evidence],
        suggested_followups=res.suggested_followups,
        visual_navigation_target=res.visual_navigation_target,
        visual_navigation_label=res.visual_navigation_label,
        why_are_you_saying_this_md=res.why_are_you_saying_this_md,
        is_clarification=res.is_clarification
    )

@router.get("/history/{session_id}")
def get_chat_history(session_id: str):
    """Returns conversation turn history for the session."""
    orch = get_orchestrator(session_id)
    return {"session_id": session_id, "history": orch.history}

@router.post("/stream")
async def stream_chat_message(req: ChatMessageRequest):
    """
    Server-Sent Events (SSE) streaming endpoint for real-time conversational UX.
    Streams token narrative, tool execution status, and verified evidence.
    """
    session_id = req.session_id or "default"
    orch: ConversationalOrchestrator = get_orchestrator(session_id)

    if req.brand_context:
        ctx = orch.context
        ctx.update_from_dict(req.brand_context)
        orch.set_brand_context(ctx)

    async def event_generator():
        yield f"event: status\ndata: {json.dumps({'status': 'planning_tools'})}\n\n"
        await asyncio.sleep(0.01)

        # Process turn through orchestrator
        res: OrchestratorResponse = orch.process_turn(req.message)

        # Stream narrative words with low latency
        words = res.narrative.split(" ")
        for i, word in enumerate(words):
            chunk = word + (" " if i < len(words) - 1 else "")
            payload = json.dumps({"token": chunk})
            yield f"event: token\ndata: {payload}\n\n"
            await asyncio.sleep(0.005)

        # Send complete final payload with evidence and navigation
        final_payload = json.dumps({
            "session_id": session_id,
            "narrative": res.narrative,
            "brand_context": res.brand_context.to_dict(),
            "cited_evidence": [it.to_dict() for it in res.cited_evidence],
            "suggested_followups": res.suggested_followups,
            "visual_navigation_target": res.visual_navigation_target,
            "visual_navigation_label": res.visual_navigation_label,
            "why_are_you_saying_this_md": res.why_are_you_saying_this_md,
            "is_clarification": res.is_clarification
        })
        yield f"event: done\ndata: {final_payload}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
