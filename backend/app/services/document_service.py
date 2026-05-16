import os
import logging
from typing import List, Tuple, Optional
from datetime import datetime

import faiss
import numpy as np
import PyPDF2
from openai import AsyncOpenAI
from app.core.config import settings
from app.db.mongodb import get_collection

logger = logging.getLogger(__name__)

CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200
EMBEDDING_DIM = 384


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> List[str]:
    words = text.split()
    chunks = []
    start = 0
    while start < len(words):
        end = min(start + chunk_size, len(words))
        chunk = " ".join(words[start:end])
        chunks.append(chunk)
        if end == len(words):
            break
        start += chunk_size - overlap
    return chunks


def extract_pdf_text(file_path: str) -> str:
    text = ""
    with open(file_path, "rb") as f:
        reader = PyPDF2.PdfReader(f)
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    return text.strip()


async def get_embeddings(texts: List[str]) -> List[List[float]]:
    """Simple hash-based embeddings - lightweight for free tier."""
    import hashlib
    embeddings = []
    for text in texts:
        # Create 384-dim embedding using hash
        vec = []
        for i in range(384):
            h = hashlib.md5(f"{text}{i}".encode()).hexdigest()
            vec.append(int(h[:8], 16) / 0xffffffff - 0.5)
        embeddings.append(vec)
    return embeddings


async def build_faiss_index(document_id: str, chunks: List[str]) -> str:
    embeddings = await get_embeddings(chunks)
    vectors = np.array(embeddings, dtype=np.float32)
    index = faiss.IndexFlatL2(EMBEDDING_DIM)
    index.add(vectors)
    index_path = os.path.join(settings.FAISS_INDEX_PATH, f"{document_id}.index")
    faiss.write_index(index, index_path)
    return index_path


def load_faiss_index(document_id: str) -> Optional[faiss.Index]:
    index_path = os.path.join(settings.FAISS_INDEX_PATH, f"{document_id}.index")
    if os.path.exists(index_path):
        return faiss.read_index(index_path)
    return None


async def semantic_search(document_ids: List[str], query: str, top_k: int = 5) -> List[dict]:
    query_embedding = await get_embeddings([query])
    query_vector = np.array(query_embedding, dtype=np.float32)
    chunks_collection = await get_collection("chunks")
    all_results = []
    for doc_id in document_ids:
        index = load_faiss_index(doc_id)
        if index is None:
            continue
        distances, indices = index.search(query_vector, top_k)
        for dist, idx in zip(distances[0], indices[0]):
            if idx < 0:
                continue
            chunk_doc = await chunks_collection.find_one(
                {"document_id": doc_id, "chunk_index": int(idx)}
            )
            if chunk_doc:
                all_results.append({
                    "document_id": doc_id,
                    "chunk_text": chunk_doc["text"],
                    "score": float(dist),
                    "chunk_index": int(idx),
                })
    all_results.sort(key=lambda x: x["score"])
    return all_results[:top_k]


async def process_pdf(document_id: str, file_path: str) -> dict:
    text = extract_pdf_text(file_path)
    chunks = chunk_text(text)
    chunks_collection = await get_collection("chunks")
    chunk_docs = [
        {
            "document_id": document_id,
            "chunk_index": i,
            "text": chunk,
            "created_at": datetime.utcnow(),
        }
        for i, chunk in enumerate(chunks)
    ]
    if chunk_docs:
        await chunks_collection.insert_many(chunk_docs)
    await build_faiss_index(document_id, chunks)
    return {
        "extracted_text": text,
        "chunk_count": len(chunks),
        "word_count": len(text.split()),
    }


async def generate_summary(text: str) -> Tuple[str, List[str]]:
    """Generate a summary using Groq."""
    client = AsyncOpenAI(
        api_key=settings.OPENAI_API_KEY,
        base_url=settings.OPENAI_BASE_URL
    )
    truncated = text[:12000]
    response = await client.chat.completions.create(
        model=settings.OPENAI_MODEL,
        messages=[
            {
                "role": "system",
                "content": "You are an expert document summarizer. Return a JSON object with keys 'summary' (2-3 paragraph summary) and 'key_topics' (list of 5-8 key topics). Return only valid JSON, no markdown.",
            },
            {"role": "user", "content": f"Summarize this document:\n\n{truncated}"},
        ],
    )
    import json
    content = response.choices[0].message.content or ""
    content = content.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    try:
        result = json.loads(content)
        return result.get("summary", ""), result.get("key_topics", [])
    except Exception:
        return content, []