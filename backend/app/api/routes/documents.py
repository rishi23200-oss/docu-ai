import os
import uuid
import logging
from typing import List
from datetime import datetime

from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, BackgroundTasks, status
from fastapi.responses import FileResponse

from app.core.security import get_current_user
from app.core.config import settings
from app.db.mongodb import get_collection
from app.models.document import DocumentResponse, DocumentSummaryResponse, TimestampResponse, FileType, ProcessingStatus
from app.services.document_service import process_pdf, generate_summary
from app.services.media_service import process_media

router = APIRouter()
logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = {
    "pdf": FileType.PDF,
    "mp3": FileType.AUDIO,
    "wav": FileType.AUDIO,
    "m4a": FileType.AUDIO,
    "mp4": FileType.VIDEO,
    "mov": FileType.VIDEO,
    "avi": FileType.VIDEO,
    "mkv": FileType.VIDEO,
}


def get_file_type(filename: str) -> FileType:
    ext = filename.rsplit(".", 1)[-1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: .{ext}")
    return ALLOWED_EXTENSIONS[ext]


async def process_document_background(document_id: str, file_path: str, file_type: FileType):
    """Background task to process uploaded document."""
    collection = await get_collection("documents")
    try:
        await collection.update_one(
            {"_id": document_id},
            {"$set": {"status": ProcessingStatus.PROCESSING, "updated_at": datetime.utcnow()}},
        )

        if file_type == FileType.PDF:
            result = await process_pdf(document_id, file_path)
        else:
            result = await process_media(document_id, file_path, file_type.value)

        summary, key_topics = await generate_summary(result["extracted_text"])

        update = {
            "status": ProcessingStatus.COMPLETED,
            "extracted_text": result["extracted_text"],
            "chunk_count": result["chunk_count"],
            "summary": summary,
            "key_topics": key_topics,
            "updated_at": datetime.utcnow(),
        }
        if "duration_seconds" in result:
            update["duration_seconds"] = result["duration_seconds"]
        if "timestamps" in result:
            update["timestamps"] = result["timestamps"]

        await collection.update_one({"_id": document_id}, {"$set": update})

    except Exception as e:
        logger.error(f"Processing failed for {document_id}: {e}", exc_info=True)
        await collection.update_one(
            {"_id": document_id},
            {"$set": {"status": ProcessingStatus.FAILED, "error": str(e), "updated_at": datetime.utcnow()}},
        )


@router.post("/upload", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
):
    """Upload a PDF, audio, or video file for processing."""
    file_type = get_file_type(file.filename)

    # Size check
    content = await file.read()
    size_mb = len(content) / (1024 * 1024)
    if size_mb > settings.MAX_FILE_SIZE_MB:
        raise HTTPException(status_code=413, detail=f"File too large. Max size: {settings.MAX_FILE_SIZE_MB}MB")

    # Save file
    document_id = str(uuid.uuid4())
    ext = file.filename.rsplit(".", 1)[-1].lower()
    storage_filename = f"{document_id}.{ext}"
    storage_path = os.path.join(settings.UPLOAD_DIR, storage_filename)

    with open(storage_path, "wb") as f:
        f.write(content)

    # Create DB record
    doc = {
        "_id": document_id,
        "filename": storage_filename,
        "original_filename": file.filename,
        "file_type": file_type.value,
        "file_size": len(content),
        "storage_path": storage_path,
        "owner_id": str(current_user["_id"]),
        "status": ProcessingStatus.PENDING.value,
        "chunk_count": 0,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }

    collection = await get_collection("documents")
    await collection.insert_one(doc)

    background_tasks.add_task(process_document_background, document_id, storage_path, file_type)

    return _to_response(doc)


@router.get("/", response_model=List[DocumentResponse])
async def list_documents(current_user: dict = Depends(get_current_user)):
    """List all documents for the current user."""
    collection = await get_collection("documents")
    cursor = collection.find({"owner_id": str(current_user["_id"])}).sort("created_at", -1)
    docs = await cursor.to_list(length=100)
    return [_to_response(d) for d in docs]


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(document_id: str, current_user: dict = Depends(get_current_user)):
    """Get document details."""
    collection = await get_collection("documents")
    doc = await collection.find_one({"_id": document_id, "owner_id": str(current_user["_id"])})
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return _to_response(doc)


@router.get("/{document_id}/summary", response_model=DocumentSummaryResponse)
async def get_summary(document_id: str, current_user: dict = Depends(get_current_user)):
    """Get AI-generated summary of a document."""
    collection = await get_collection("documents")
    doc = await collection.find_one({"_id": document_id, "owner_id": str(current_user["_id"])})
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    if doc.get("status") != ProcessingStatus.COMPLETED.value:
        raise HTTPException(status_code=400, detail="Document not yet processed")
    return {
        "document_id": document_id,
        "summary": doc.get("summary", ""),
        "key_topics": doc.get("key_topics", []),
        "word_count": len(doc.get("extracted_text", "").split()),
    }


@router.get("/{document_id}/timestamps", response_model=TimestampResponse)
async def get_timestamps(document_id: str, current_user: dict = Depends(get_current_user)):
    """Get topic timestamps for audio/video documents."""
    collection = await get_collection("documents")
    doc = await collection.find_one({"_id": document_id, "owner_id": str(current_user["_id"])})
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    if doc.get("file_type") not in ("audio", "video"):
        raise HTTPException(status_code=400, detail="Timestamps only available for audio/video")
    return {"document_id": document_id, "timestamps": doc.get("timestamps", [])}


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(document_id: str, current_user: dict = Depends(get_current_user)):
    """Delete a document and its associated data."""
    collection = await get_collection("documents")
    doc = await collection.find_one({"_id": document_id, "owner_id": str(current_user["_id"])})
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    # Delete file from disk
    if os.path.exists(doc.get("storage_path", "")):
        os.remove(doc["storage_path"])

    # Clean up DB
    await collection.delete_one({"_id": document_id})
    chunks_col = await get_collection("chunks")
    await chunks_col.delete_many({"document_id": document_id})
    segments_col = await get_collection("segments")
    await segments_col.delete_many({"document_id": document_id})


def _to_response(doc: dict) -> dict:
    return {
        "id": doc["_id"],
        "filename": doc["filename"],
        "original_filename": doc.get("original_filename", doc["filename"]),
        "file_type": doc["file_type"],
        "file_size": doc["file_size"],
        "owner_id": doc["owner_id"],
        "storage_path": doc.get("storage_path", ""),
        "status": doc.get("status", ProcessingStatus.PENDING.value),
        "extracted_text": doc.get("extracted_text"),
        "summary": doc.get("summary"),
        "duration_seconds": doc.get("duration_seconds"),
        "timestamps": doc.get("timestamps"),
        "chunk_count": doc.get("chunk_count", 0),
        "created_at": doc.get("created_at", datetime.utcnow()),
        "updated_at": doc.get("updated_at", datetime.utcnow()),
    }
