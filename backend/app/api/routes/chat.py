from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from typing import List

from app.core.security import get_current_user
from app.models.chat import ChatRequest, ChatResponse, ConversationHistory
from app.services.chat_service import chat_with_documents, stream_chat_with_documents
from app.db.mongodb import get_collection

router = APIRouter()


@router.post("/", response_model=ChatResponse)
async def chat(request: ChatRequest, current_user: dict = Depends(get_current_user)):
    """Send a message and receive an AI response based on uploaded documents."""
    if not request.document_ids:
        raise HTTPException(status_code=400, detail="At least one document_id is required")

    # Verify documents belong to user
    doc_collection = await get_collection("documents")
    user_id = str(current_user["_id"])
    for doc_id in request.document_ids:
        doc = await doc_collection.find_one({"_id": doc_id, "owner_id": user_id})
        if not doc:
            raise HTTPException(status_code=404, detail=f"Document {doc_id} not found")

    if request.stream:
        return StreamingResponse(
            stream_chat_with_documents(
                request.message,
                request.document_ids,
                request.conversation_id,
                user_id,
            ),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
            },
        )

    result = await chat_with_documents(
        request.message,
        request.document_ids,
        request.conversation_id,
        user_id,
    )

    return {
        "conversation_id": result["conversation_id"],
        "message": {
            "role": "assistant",
            "content": result["answer"],
            "sources": result.get("sources", []),
            "timestamp_refs": result.get("relevant_timestamps", []),
        },
        "relevant_timestamps": result.get("relevant_timestamps", []),
    }


@router.get("/conversations", response_model=List[ConversationHistory])
async def list_conversations(current_user: dict = Depends(get_current_user)):
    """List all conversations for the current user."""
    collection = await get_collection("conversations")
    cursor = collection.find({"user_id": str(current_user["_id"])}).sort("updated_at", -1)
    convs = await cursor.to_list(length=50)
    return [
        {
            "id": c["_id"],
            "document_ids": c["document_ids"],
            "messages": c.get("messages", []),
            "created_at": c["created_at"],
            "updated_at": c["updated_at"],
        }
        for c in convs
    ]


@router.get("/conversations/{conversation_id}", response_model=ConversationHistory)
async def get_conversation(conversation_id: str, current_user: dict = Depends(get_current_user)):
    """Get a specific conversation with full history."""
    collection = await get_collection("conversations")
    conv = await collection.find_one({"_id": conversation_id, "user_id": str(current_user["_id"])})
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {
        "id": conv["_id"],
        "document_ids": conv["document_ids"],
        "messages": conv.get("messages", []),
        "created_at": conv["created_at"],
        "updated_at": conv["updated_at"],
    }


@router.delete("/conversations/{conversation_id}", status_code=204)
async def delete_conversation(conversation_id: str, current_user: dict = Depends(get_current_user)):
    """Delete a conversation."""
    collection = await get_collection("conversations")
    result = await collection.delete_one({"_id": conversation_id, "user_id": str(current_user["_id"])})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Conversation not found")
