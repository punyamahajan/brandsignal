from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any

from backend.dependencies import get_orchestrator, reset_session
from backend.schemas.context import BrandContextRequest, BrandContextResponse
from src.orchestrator.service import ConversationalOrchestrator
from src.orchestrator.context import BrandContext

router = APIRouter(prefix="/api/context", tags=["context"])

@router.get("/{session_id}", response_model=BrandContextResponse)
def get_session_context(session_id: str):
    """Retrieves current active brand context for the specified session."""
    orch: ConversationalOrchestrator = get_orchestrator(session_id)
    ctx = orch.context
    return BrandContextResponse(
        brand_name=ctx.brand_name,
        industry=ctx.industry,
        category=ctx.category,
        geography=ctx.geography,
        business_model=ctx.business_model,
        target_customer=ctx.target_customer,
        price_positioning=ctx.price_positioning,
        customer_segment=ctx.customer_segment,
        is_demo_vertical=ctx.is_demo_vertical,
        demo_brand_id=ctx.demo_brand_id,
        competitors=ctx.competitors,
        status=ctx.status,
        summary=ctx.summary(),
        is_established=ctx.is_established()
    )

@router.post("/{session_id}", response_model=BrandContextResponse)
def update_session_context(session_id: str, req: BrandContextRequest):
    """Updates active brand context explicitly."""
    orch: ConversationalOrchestrator = get_orchestrator(session_id)
    ctx = orch.context
    if req.brand_name is not None:
        ctx.brand_name = req.brand_name
    if req.industry is not None:
        ctx.industry = req.industry
    if req.category is not None:
        ctx.category = req.category
    if req.geography is not None:
        ctx.geography = req.geography
    if req.business_model is not None:
        ctx.business_model = req.business_model
    if req.target_customer is not None:
        ctx.target_customer = req.target_customer
    if req.price_positioning is not None:
        ctx.price_positioning = req.price_positioning
    if req.customer_segment is not None:
        ctx.customer_segment = req.customer_segment
    if req.is_demo_vertical is not None:
        ctx.is_demo_vertical = req.is_demo_vertical
    if req.demo_brand_id is not None:
        ctx.demo_brand_id = req.demo_brand_id
    if req.competitors:
        ctx.competitors = req.competitors

    if ctx.is_established():
        ctx.status = "ESTABLISHED"

    orch.set_brand_context(ctx)

    return BrandContextResponse(
        brand_name=ctx.brand_name,
        industry=ctx.industry,
        category=ctx.category,
        geography=ctx.geography,
        business_model=ctx.business_model,
        target_customer=ctx.target_customer,
        price_positioning=ctx.price_positioning,
        customer_segment=ctx.customer_segment,
        is_demo_vertical=ctx.is_demo_vertical,
        demo_brand_id=ctx.demo_brand_id,
        competitors=ctx.competitors,
        status=ctx.status,
        summary=ctx.summary(),
        is_established=ctx.is_established()
    )

@router.post("/{session_id}/reset")
def reset_session_context(session_id: str):
    """Resets conversational history and brand context for the session."""
    reset_session(session_id)
    return {"status": "ok", "message": f"Session '{session_id}' has been reset."}
