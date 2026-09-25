import os
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

from backend.config import config
from backend.vector_store import BeansVectorStore
from backend.rag_agent import BeansRAGAgent

app = FastAPI(
    title="Beans.ai RAG Support Agent",
    description="Intelligent RAG pipeline grounding answers on Beans Route docs and YouTube tutorials with second-level timestamps.",
    version="1.0.0"
)

# Enable CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize singletons
vector_store = BeansVectorStore()
agent = BeansRAGAgent(vector_store=vector_store)

class ChatRequest(BaseModel):
    query: str
    history: Optional[List[Dict[str, str]]] = []

class ChatResponse(BaseModel):
    model_config = {"protected_namespaces": ()}
    answer: str
    reasoning: Optional[str] = ""
    sources: List[Dict[str, Any]]
    guardrail_triggered: bool
    model_used: str

@app.get("/api/health")
def health_check():
    stats = vector_store.get_stats()
    return {
        "status": "online",
        "model": config.GROQ_MODEL,
        "embedding_model": config.EMBEDDING_MODEL_NAME,
        "vector_store_chunks": stats["total_chunks"],
        "similarity_threshold": config.SIMILARITY_THRESHOLD,
        "top_k": config.TOP_K
    }

@app.post("/api/chat", response_model=ChatResponse)
def chat_endpoint(req: ChatRequest):
    if not req.query or not req.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty.")
    
    try:
        result = agent.answer_query(req.query.strip())
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"RAG generation error: {str(e)}")

@app.get("/api/sources")
def list_sources():
    stats = vector_store.get_stats()
    return {
        "stats": stats
    }

# Serve frontend static assets
frontend_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")
if os.path.exists(frontend_dir):
    app.mount("/static", StaticFiles(directory=frontend_dir), name="static")

    @app.get("/")
    def serve_index():
        return FileResponse(os.path.join(frontend_dir, "index.html"))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
