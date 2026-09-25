import os
from dotenv import load_dotenv

# Load .env file
load_dotenv()

class Config:
    GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
    GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
    GROQ_FALLBACK_MODEL = os.getenv("GROQ_FALLBACK_MODEL", "openai/gpt-oss-20b")
    
    # RAG Retrieval parameters
    SIMILARITY_THRESHOLD = float(os.getenv("SIMILARITY_THRESHOLD", "0.35"))
    TOP_K = int(os.getenv("TOP_K", "5"))
    
    # Storage
    CHROMA_PERSIST_DIR = os.getenv("CHROMA_PERSIST_DIR", "./data/chroma_db")
    COLLECTION_NAME = "beans_knowledge_base"
    
    # Embedding Model: local sentence-transformers all-MiniLM-L6-v2 (384-dimensional)
    EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"

config = Config()
