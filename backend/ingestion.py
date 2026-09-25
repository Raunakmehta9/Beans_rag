import json
import os
import re
from typing import List, Dict, Any
from backend.vector_store import BeansVectorStore

def chunk_document_text(text: str, max_words: int = 150, overlap_words: int = 30) -> List[str]:
    """Splits a document text into overlapping semantic windows."""
    paragraphs = [p.strip() for p in text.split("\n") if p.strip()]
    chunks = []
    current_words = []

    for para in paragraphs:
        p_words = para.split()
        if not p_words:
            continue
        
        if len(current_words) + len(p_words) <= max_words:
            current_words.extend(p_words)
        else:
            if current_words:
                chunks.append(" ".join(current_words))
            # Take overlap from end of current_words
            overlap = current_words[-overlap_words:] if len(current_words) > overlap_words else current_words
            current_words = overlap + p_words
            
    if current_words:
        chunks.append(" ".join(current_words))

    return chunks if chunks else [text]

def prepare_document_chunks(docs_file: str = "data/beans_knowledge.json") -> List[Dict[str, Any]]:
    if not os.path.exists(docs_file):
        print(f"Warning: {docs_file} does not exist.")
        return []

    with open(docs_file, "r", encoding="utf-8") as f:
        articles = json.load(f)

    doc_chunks = []
    for art in articles:
        art_id = art.get("id")
        title = art.get("title", "Untitled Guide")
        url = art.get("url", "")
        content = art.get("content", "").strip()

        if not content:
            continue

        raw_chunks = chunk_document_text(content, max_words=140, overlap_words=25)
        for idx, chunk_text in enumerate(raw_chunks):
            doc_chunks.append({
                "chunk_id": f"doc_{art_id}_{idx}",
                "source_type": "document",
                "title": title,
                "url": url,
                "deep_link": url,
                "start_seconds": 0.0,
                "timestamp_str": "Document",
                "video_id": "",
                "text": f"Article Title: {title}\nContent:\n{chunk_text}"
            })

    print(f"Prepared {len(doc_chunks)} chunks from {len(articles)} Zendesk articles.")
    return doc_chunks

def load_youtube_chunks(yt_file: str = "data/youtube_chunks.json") -> List[Dict[str, Any]]:
    if not os.path.exists(yt_file):
        print(f"Warning: {yt_file} does not exist yet. Run backend/scrape_youtube.py first.")
        return []

    with open(yt_file, "r", encoding="utf-8") as f:
        chunks = json.load(f)
    print(f"Loaded {len(chunks)} pre-processed YouTube chunks.")
    return chunks

def run_full_ingestion():
    print("=" * 60)
    print("Starting Beans.ai Knowledge Ingestion Pipeline")
    print("=" * 60)

    # 1. Load document chunks
    doc_chunks = prepare_document_chunks()

    # 2. Load YouTube chunks
    yt_chunks = load_youtube_chunks()

    all_chunks = doc_chunks + yt_chunks
    print(f"\nTotal combined chunks ready for vector store: {len(all_chunks)}")
    print(f" - Document Chunks: {len(doc_chunks)}")
    print(f" - YouTube Chunks:  {len(yt_chunks)}")

    if not all_chunks:
        print("No chunks to index!")
        return

    # 3. Index in ChromaDB
    print("\nInitializing ChromaDB with HNSW index...")
    vstore = BeansVectorStore()
    vstore.add_chunks(all_chunks)

    stats = vstore.get_stats()
    print("\n" + "=" * 60)
    print(f"Ingestion Complete! Vector Store Total Chunks: {stats['total_chunks']}")
    print("=" * 60)

if __name__ == "__main__":
    run_full_ingestion()
