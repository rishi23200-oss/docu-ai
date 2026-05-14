from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


# --- Chat Models ---
class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class ChatMessage(BaseModel):
    role: MessageRole
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    sources: Optional[List[dict]] = None  # [{chunk_text, score, document_id}]
    timestamp_refs: Optional[List[dict]] = None  # for audio/video answers


class ChatRequest(BaseModel):
    document_ids: List[str]
    message: str
    conversation_id: Optional[str] = None
    stream: bool = False


class ChatResponse(BaseModel):
    conversation_id: str
    message: ChatMessage
    relevant_timestamps: Optional[List[dict]] = None


class ConversationHistory(BaseModel):
    id: str
    document_ids: List[str]
    messages: List[ChatMessage]
    created_at: datetime
    updated_at: datetime


# --- User Models ---
class UserCreate(BaseModel):
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=8)


class UserResponse(BaseModel):
    id: str
    email: str
    username: str
    created_at: datetime

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class TokenData(BaseModel):
    user_id: Optional[str] = None
