from fastapi import APIRouter, Query, HTTPException, Depends
from typing import Dict, Any, List, Optional

from backend.dependencies import get_source_registry
from backend.schemas.chat import EvidenceItemSchema
from src.research.source_registry import SourceRegistry

router = APIRouter(prefix="/api/research", tags=["research"])

@router.get("/providers")
def list_providers(registry: SourceRegistry = Depends(get_source_registry)):
    """Reports status and readiness of external public research providers."""
    return registry.list_providers()

@router.get("/youtube", response_model=List[EvidenceItemSchema])
def search_youtube_reviews(
    query: str = Query(..., description="Search query for brand or product reviews"),
    max_results: int = Query(5, ge=1, le=10),
    registry: SourceRegistry = Depends(get_source_registry)
):
    """Executes read-only public video review research using YouTube Data API v3."""
    yt = registry.get_provider("youtube")
    if not yt or not yt.is_available:
        raise HTTPException(
            status_code=503,
            detail="YouTube Data API provider is not available or YOUTUBE_API_KEY is not configured."
        )

    result = yt.search(query, max_results=max_results)
    if not result.success:
        raise HTTPException(status_code=502, detail=result.error_message)

    return [EvidenceItemSchema(**item.to_dict()) for item in result.evidence_items]
