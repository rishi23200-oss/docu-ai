import logging
from typing import List, AsyncGenerator, Optional
from datetime import datetime

from openai import AsyncOpenAI

from app.core.config import settings
from app.db.mongodb import get_collection
from app.services.document_service import semantic_search
from app.services.media_service import find_relevant_timestamps

logger = logging.getLogger(__name__)
client = AsyncOpenAI(
    api_key=settings.OPENAI_API_KEY,
    base_url=settings.OPENAI_BASE_URL
)

SYSTEM_PROMPT = """You are DocuAI, an expert AI assistant that answers questions based on provided document context.

Rules:
- Answer ONLY based on the provided context chunks. Do not use outside knowledge.
- If the context doesn't contain enough information, say so clearly.
- For audio/video sources, mention the relevant timestamps when available.
- Be concise but thorough. Use bullet points for lists.
- Always cite which document the information came from when possible.
"""


async def get_or_create_conversation(conversation_id: Optional[str], document_ids: List[str], user_id: str) -> dict:
    """Get existing conversation or create a new one."""
    collection = await get_collection("conversations")

    if conversation_id:
        conv = await collection.find_one({"_id": conversation_id, "user_id": user_id})
        if conv:
            return conv

    # Create new
    from bson import ObjectId
    new_conv = {
        "_id": str(ObjectId()),
        "user_id": user_id,
        "document_ids": document_ids,
        "messages": [],
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }
    await collection.insert_one(new_conv)
    return new_conv


async def add_message_to_conversation(conversation_id: str, message: dict):
    """Append a message to conversation history."""
    collection = await get_collection("conversations")
    await collection.update_one(
        {"_id": conversation_id},
        {
            "$push": {"messages": message},
            "$set": {"updated_at": datetime.utcnow()},
        },
    )


async def chat_with_documents(
    user_message: str,
    document_ids: List[str],
    conversation_id: Optional[str],
    user_id: str,
) -> dict:
    """Non-streaming chat: retrieve context, call LLM, return full response."""
    # 1. Retrieve relevant chunks via FAISS
    relevant_chunks = await semantic_search(document_ids, user_message, top_k=5)

    context = "\n\n---\n\n".join([
        f"[Document: {c['document_id']}]\n{c['chunk_text']}"
        for c in relevant_chunks
    ])

    # 2. Get/create conversation and build history
    conversation = await get_or_create_conversation(conversation_id, document_ids, user_id)
    history = conversation.get("messages", [])[-10:]  # last 10 messages

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    if context:
        messages.append({
            "role": "user",
            "content": f"Context from uploaded documents:\n{context}\n\nPlease use this context to answer questions.",
        })
        messages.append({
            "role": "assistant",
            "content": "I've reviewed the document context and I'm ready to answer your questions.",
        })

    for msg in history:
        messages.append({"role": msg["role"], "content": msg["content"]})

    messages.append({"role": "user", "content": user_message})

    # 3. Call OpenAI
    response = await client.chat.completions.create(
        model=settings.OPENAI_MODEL,
        messages=messages,
        temperature=0.3,
        max_tokens=1000,
    )
    answer = response.choices[0].message.content

    # 4. Find relevant timestamps for media documents
    docs_collection = await get_collection("documents")
    relevant_timestamps = []
    for doc_id in document_ids:
        doc = await docs_collection.find_one({"_id": doc_id})
        if doc and doc.get("file_type") in ("audio", "video"):
            ts = await find_relevant_timestamps(doc_id, answer)
            for t in ts:
                t["document_id"] = doc_id
                t["filename"] = doc.get("filename", "")
            relevant_timestamps.extend(ts)

    # 5. Save messages
    user_msg = {"role": "user", "content": user_message, "timestamp": datetime.utcnow().isoformat()}
    assistant_msg = {
        "role": "assistant",
        "content": answer,
        "timestamp": datetime.utcnow().isoformat(),
        "sources": relevant_chunks[:3],
    }
    await add_message_to_conversation(conversation["_id"], user_msg)
    await add_message_to_conversation(conversation["_id"], assistant_msg)

    return {
        "conversation_id": conversation["_id"],
        "answer": answer,
        "sources": relevant_chunks[:3],
        "relevant_timestamps": relevant_timestamps,
    }


async def stream_chat_with_documents(
    user_message: str,
    document_ids: List[str],
    conversation_id: Optional[str],
    user_id: str,
) -> AsyncGenerator[str, None]:
    """Streaming chat: yields SSE-formatted chunks."""
    relevant_chunks = await semantic_search(document_ids, user_message, top_k=5)
    context = "\n\n---\n\n".join([
        f"[Document: {c['document_id']}]\n{c['chunk_text']}"
        for c in relevant_chunks
    ])

    conversation = await get_or_create_conversation(conversation_id, document_ids, user_id)
    history = conversation.get("messages", [])[-10:]

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    if context:
        messages.append({"role": "user", "content": f"Context:\n{context}\n\nAnswer based on this."})
        messages.append({"role": "assistant", "content": "Ready to answer based on the context."})

    for msg in history:
        messages.append({"role": msg["role"], "content": msg["content"]})
    messages.append({"role": "user", "content": user_message})

    full_answer = ""
    stream = await client.chat.completions.create(
        model=settings.OPENAI_MODEL,
        messages=messages,
        temperature=0.3,
        max_tokens=1000,
        stream=True,
    )
    async for chunk in stream:
        text = chunk.choices[0].delta.content or ""
        if text:
            full_answer += text
            yield f"data: {text}\n\n"

    # Save to history
    user_msg = {"role": "user", "content": user_message, "timestamp": datetime.utcnow().isoformat()}
    assistant_msg = {"role": "assistant", "content": full_answer, "timestamp": datetime.utcnow().isoformat()}
    await add_message_to_conversation(conversation["_id"], user_msg)
    await add_message_to_conversation(conversation["_id"], assistant_msg)
