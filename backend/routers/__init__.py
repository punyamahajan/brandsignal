from backend.routers.analytics import router as analytics_router
from backend.routers.context import router as context_router
from backend.routers.evidence import router as evidence_router
from backend.routers.research import router as research_router
from backend.routers.chat import router as chat_router

__all__ = [
    "analytics_router",
    "context_router",
    "evidence_router",
    "research_router",
    "chat_router"
]
