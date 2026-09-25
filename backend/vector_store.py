import os
from typing import List, Dict, Any, Optional
import chromadb
from chromadb.config import Settings
from chromadb.utils import embedding_functions
from backend.config import config

class BeansVectorStore:
    def __init__(self, persist_directory: str = config.CHROMA_PERSIST_DIR):
        self.persist_directory = persist_directory
        os.makedirs(self.persist_directory, exist_ok=True)
        
        # Initialize ChromaDB persistent client
        self.client = chromadb.PersistentClient(path=self.persist_directory)
        
        # Use ONNX / SentenceTransformers embedding function for local, free execution
        try:
            self.embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
                model_name=config.EMBEDDING_MODEL_NAME
            )
        except Exception:
            # Fallback to Chroma's default lightweight ONNX MiniLM
            self.embedding_function = embedding_functions.DefaultEmbeddingFunction()
            
        self.collection = self.client.get_or_create_collection(
            name=config.COLLECTION_NAME,
            embedding_function=self.embedding_function,
            metadata={"hnsw:space": "cosine"}  # Use Cosine distance
        )

    def add_chunks(self, chunks: List[Dict[str, Any]], batch_size: int = 100) -> int:
        """
        Adds pre-processed chunks (documents & YouTube segments) into ChromaDB with HNSW indexing.
        """
        if not chunks:
            return 0

        total_added = 0
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i:i + batch_size]
            ids = [c["chunk_id"] for c in batch]
            documents = [c["text"] for c in batch]
            
            # Prepare metadata (ChromaDB supports str, int, float, bool)
            metadatas = []
            for c in batch:
                meta = {
                    "source_type": str(c.get("source_type", "document")),
                    "title": str(c.get("title", "")),
                    "url": str(c.get("url", "")),
                    "deep_link": str(c.get("deep_link", c.get("url", ""))),
                    "start_seconds": float(c.get("start_seconds", 0.0)),
                    "timestamp_str": str(c.get("timestamp_str", "00:00")),
                    "video_id": str(c.get("video_id", ""))
                }
                metadatas.append(meta)

            self.collection.upsert(
                ids=ids,
                documents=documents,
                metadatas=metadatas
            )
            total_added += len(batch)
            print(f"Indexed {total_added}/{len(chunks)} chunks in ChromaDB...")

        return total_added

    def query(self, query_text: str, top_k: int = config.TOP_K, threshold: float = config.SIMILARITY_THRESHOLD) -> List[Dict[str, Any]]:
        """
        Executes HNSW Approximate Nearest Neighbor search using Cosine distance.
        Filters results by similarity threshold: similarity = 1 - cosine_distance.
        """
        results = self.collection.query(
            query_texts=[query_text],
            n_results=top_k,
            include=["documents", "metadatas", "distances"]
        )

        candidates = []
        if not results or not results["documents"] or not results["documents"][0]:
            return candidates

        docs = results["documents"][0]
        metas = results["metadatas"][0]
        distances = results["distances"][0]

        for rank, (doc, meta, dist) in enumerate(zip(docs, metas, distances), 1):
            # ChromaDB cosine space returns distance in [0, 2]
            # Cosine similarity = 1 - distance
            similarity = round(1.0 - float(dist), 4)

            # Apply similarity threshold guardrail
            if similarity >= threshold:
                candidates.append({
                    "rank": rank,
                    "text": doc,
                    "similarity": similarity,
                    "distance": round(float(dist), 4),
                    "metadata": meta,
                    "source_type": meta.get("source_type"),
                    "title": meta.get("title"),
                    "deep_link": meta.get("deep_link"),
                    "timestamp_str": meta.get("timestamp_str"),
                    "start_seconds": meta.get("start_seconds", 0.0)
                })

        return candidates

    def get_stats(self) -> Dict[str, Any]:
        """Returns statistics on indexed data."""
        count = self.collection.count()
        return {
            "total_chunks": count,
            "collection_name": config.COLLECTION_NAME,
            "persist_dir": self.persist_directory
        }
