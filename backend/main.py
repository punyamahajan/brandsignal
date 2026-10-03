import os
import sys

# Ensure project root is in python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

try:
    import dotenv
    dotenv.load_dotenv()
except ImportError:
    pass

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.routers import (
    analytics_router,
    context_router,
    evidence_router,
    research_router,
    chat_router
)

app = FastAPI(
    title="BrandSignal Intelligence API",
    description=(
        "Conversational Competitive & Market Intelligence API. "
        "Grounded strictly in verified DuckDB records and primary research evidence. "
        "Philosophy: 'Understand the market. See the gap. Make the call.'"
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Enable CORS for React/Vite frontend (http://localhost:5173) and local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(chat_router)
app.include_router(analytics_router)
app.include_router(context_router)
app.include_router(evidence_router)
app.include_router(research_router)

@app.get("/")
def root():
    return {
        "service": "BrandSignal Intelligence API",
        "status": "operational",
        "version": "1.0.0",
        "philosophy": "Understand the market. See the gap. Make the call.",
        "documentation": "/docs"
    }

@app.get("/api/health")
def health_check():
    return {
        "status": "healthy",
        "database": "connected",
        "llm_mode": "hybrid_orchestrator"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
