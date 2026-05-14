import os
from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import StreamingResponse, FileResponse
from typing import Optional

from app.core.security import get_current_user
from app.db.mongodb import get_collection

router = APIRouter()

MIME_TYPES = {
    "mp3": "audio/mpeg",
    "wav": "audio/wav",
    "m4a": "audio/mp4",
    "mp4": "video/mp4",
    "mov": "video/quicktime",
    "avi": "video/x-msvideo",
    "mkv": "video/x-matroska",
    "pdf": "application/pdf",
}


@router.get("/{document_id}/stream")
async def stream_media(
    document_id: str,
    request: Request,
    current_user: dict = Depends(get_current_user),
):
    """Stream audio/video file with range request support for seek functionality."""
    collection = await get_collection("documents")
    doc = await collection.find_one({"_id": document_id, "owner_id": str(current_user["_id"])})
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    file_path = doc.get("storage_path", "")
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found on disk")

    ext = doc["filename"].rsplit(".", 1)[-1].lower()
    content_type = MIME_TYPES.get(ext, "application/octet-stream")
    file_size = os.path.getsize(file_path)

    # Handle range requests for seeking
    range_header = request.headers.get("range")
    if range_header:
        range_val = range_header.replace("bytes=", "").split("-")
        start = int(range_val[0])
        end = int(range_val[1]) if range_val[1] else file_size - 1
        chunk_size = end - start + 1

        def iter_file():
            with open(file_path, "rb") as f:
                f.seek(start)
                remaining = chunk_size
                while remaining > 0:
                    data = f.read(min(65536, remaining))
                    if not data:
                        break
                    remaining -= len(data)
                    yield data

        return StreamingResponse(
            iter_file(),
            status_code=206,
            media_type=content_type,
            headers={
                "Content-Range": f"bytes {start}-{end}/{file_size}",
                "Accept-Ranges": "bytes",
                "Content-Length": str(chunk_size),
            },
        )

    return FileResponse(file_path, media_type=content_type, filename=doc["original_filename"])
