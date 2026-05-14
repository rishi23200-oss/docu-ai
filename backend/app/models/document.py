from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


class FileType(str, Enum):
    PDF = "pdf"
    AUDIO = "audio"
    VIDEO = "video"


class ProcessingStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class DocumentBase(BaseModel):
    filename: str
    file_type: FileType
    file_size: int
    owner_id: str


class DocumentCreate(DocumentBase):
    storage_path: str
    original_filename: str


class DocumentResponse(DocumentBase):
    id: str
    storage_path: str
    original_filename: str
    status: ProcessingStatus
    extracted_text: Optional[str] = None
    summary: Optional[str] = None
    duration_seconds: Optional[float] = None  # for audio/video
    timestamps: Optional[List[dict]] = None   # [{topic, start, end}]
    chunk_count: int = 0
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DocumentSummaryResponse(BaseModel):
    document_id: str
    summary: str
    key_topics: List[str]
    word_count: int


class TimestampItem(BaseModel):
    topic: str
    start_time: float
    end_time: float
    text: str


class TimestampResponse(BaseModel):
    document_id: str
    timestamps: List[TimestampItem]
