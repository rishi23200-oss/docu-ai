"""
Comprehensive test suite for DocuAI Backend
Coverage target: 95%+
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch, mock_open
from datetime import datetime
from httpx import AsyncClient, ASGITransport
import json
import os


# ============================================================
# Fixtures
# ============================================================

@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_db():
    """Mock MongoDB collection."""
    collection = AsyncMock()
    collection.find_one = AsyncMock(return_value=None)
    collection.insert_one = AsyncMock(return_value=MagicMock(inserted_id="test_id"))
    collection.insert_many = AsyncMock()
    collection.update_one = AsyncMock()
    collection.delete_one = AsyncMock(return_value=MagicMock(deleted_count=1))
    collection.delete_many = AsyncMock()
    cursor = AsyncMock()
    cursor.to_list = AsyncMock(return_value=[])
    cursor.sort = MagicMock(return_value=cursor)
    collection.find = MagicMock(return_value=cursor)
    return collection


@pytest.fixture
def sample_user():
    return {
        "_id": "user123",
        "email": "test@example.com",
        "username": "testuser",
        "hashed_password": "$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW",  # "secret"
        "created_at": datetime.utcnow(),
    }


@pytest.fixture
def sample_document():
    return {
        "_id": "doc123",
        "filename": "test.pdf",
        "original_filename": "test.pdf",
        "file_type": "pdf",
        "file_size": 1024,
        "storage_path": "/tmp/uploads/doc123.pdf",
        "owner_id": "user123",
        "status": "completed",
        "extracted_text": "This is sample document text about machine learning and AI.",
        "summary": "A document about AI and machine learning.",
        "key_topics": ["AI", "Machine Learning"],
        "chunk_count": 5,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }


@pytest.fixture
def sample_audio_document():
    return {
        "_id": "audio123",
        "filename": "podcast.mp3",
        "original_filename": "podcast.mp3",
        "file_type": "audio",
        "file_size": 5242880,
        "storage_path": "/tmp/uploads/audio123.mp3",
        "owner_id": "user123",
        "status": "completed",
        "extracted_text": "Welcome to the podcast. Today we discuss AI trends.",
        "summary": "A podcast about AI trends.",
        "duration_seconds": 300.5,
        "timestamps": [
            {"topic": "Introduction", "start_time": 0, "end_time": 30, "text": "Welcome"},
            {"topic": "AI Trends", "start_time": 30, "end_time": 120, "text": "Discussion of AI"},
        ],
        "chunk_count": 3,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }


# ============================================================
# Core Config Tests
# ============================================================

class TestConfig:
    def test_settings_defaults(self):
        from app.core.config import settings
        assert settings.MONGODB_DB_NAME == "docuai"
        assert settings.OPENAI_MODEL == "gpt-4o"
        assert settings.MAX_FILE_SIZE_MB == 100
        assert settings.ALGORITHM == "HS256"

    def test_upload_dir_created(self):
        from app.core.config import settings
        assert os.path.exists(settings.UPLOAD_DIR)

    def test_faiss_index_path_created(self):
        from app.core.config import settings
        assert os.path.exists(settings.FAISS_INDEX_PATH)


# ============================================================
# Security Tests
# ============================================================

class TestSecurity:
    def test_password_hashing(self):
        from app.core.security import get_password_hash, verify_password
        password = "mysecretpassword"
        hashed = get_password_hash(password)
        assert hashed != password
        assert verify_password(password, hashed)
        assert not verify_password("wrongpassword", hashed)

    def test_create_and_decode_token(self):
        from app.core.security import create_access_token, decode_token
        data = {"sub": "user123"}
        token = create_access_token(data)
        assert isinstance(token, str)
        decoded = decode_token(token)
        assert decoded["sub"] == "user123"

    def test_decode_invalid_token(self):
        from app.core.security import decode_token
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc:
            decode_token("invalid.token.here")
        assert exc.value.status_code == 401

    def test_token_with_custom_expiry(self):
        from app.core.security import create_access_token, decode_token
        from datetime import timedelta
        token = create_access_token({"sub": "user456"}, expires_delta=timedelta(hours=1))
        decoded = decode_token(token)
        assert decoded["sub"] == "user456"


# ============================================================
# Document Service Tests
# ============================================================

class TestDocumentService:
    def test_chunk_text_basic(self):
        from app.services.document_service import chunk_text
        text = " ".join([f"word{i}" for i in range(2000)])
        chunks = chunk_text(text, chunk_size=500, overlap=50)
        assert len(chunks) > 1
        assert all(isinstance(c, str) for c in chunks)

    def test_chunk_text_short_text(self):
        from app.services.document_service import chunk_text
        text = "This is a short text."
        chunks = chunk_text(text, chunk_size=500, overlap=50)
        assert len(chunks) == 1
        assert chunks[0] == text

    def test_chunk_text_overlap(self):
        from app.services.document_service import chunk_text
        words = [f"w{i}" for i in range(100)]
        text = " ".join(words)
        chunks = chunk_text(text, chunk_size=20, overlap=5)
        assert len(chunks) > 1
        # Check overlap: last 5 words of chunk 0 should appear at start of chunk 1
        chunk0_words = chunks[0].split()
        chunk1_words = chunks[1].split()
        assert chunk0_words[-5:] == chunk1_words[:5]

    def test_chunk_text_empty(self):
        from app.services.document_service import chunk_text
        chunks = chunk_text("", chunk_size=500, overlap=50)
        assert chunks == []

    @patch("builtins.open", mock_open(read_data=b"fake pdf content"))
    @patch("app.services.document_service.PyPDF2.PdfReader")
    def test_extract_pdf_text(self, mock_reader):
        from app.services.document_service import extract_pdf_text
        mock_page = MagicMock()
        mock_page.extract_text.return_value = "Sample text from PDF page."
        mock_reader.return_value.pages = [mock_page, mock_page]
        text = extract_pdf_text("/fake/path.pdf")
        assert "Sample text from PDF page." in text

    @pytest.mark.asyncio
    async def test_get_embeddings(self):
        from app.services.document_service import get_embeddings
        mock_embedding = [0.1] * 1536
        with patch("app.services.document_service.client") as mock_client:
            mock_client.embeddings.create = AsyncMock(return_value=MagicMock(
                data=[MagicMock(embedding=mock_embedding)]
            ))
            result = await get_embeddings(["test text"])
            assert len(result) == 1
            assert len(result[0]) == 1536

    @pytest.mark.asyncio
    async def test_generate_summary(self):
        from app.services.document_service import generate_summary
        mock_response = json.dumps({
            "summary": "This is a test summary.",
            "key_topics": ["AI", "Testing", "Python"]
        })
        with patch("app.services.document_service.client") as mock_client:
            mock_client.chat.completions.create = AsyncMock(return_value=MagicMock(
                choices=[MagicMock(message=MagicMock(content=mock_response))]
            ))
            summary, topics = await generate_summary("Some document text")
            assert summary == "This is a test summary."
            assert "AI" in topics


# ============================================================
# Media Service Tests
# ============================================================

class TestMediaService:
    @patch("subprocess.run")
    def test_extract_audio_from_video_success(self, mock_run):
        from app.services.media_service import extract_audio_from_video
        mock_run.return_value = MagicMock(returncode=0)
        result = extract_audio_from_video("/tmp/video.mp4")
        assert result.endswith("_audio.mp3")
        mock_run.assert_called_once()

    @patch("subprocess.run")
    def test_extract_audio_from_video_failure(self, mock_run):
        from app.services.media_service import extract_audio_from_video
        mock_run.return_value = MagicMock(returncode=1, stderr="Error")
        with pytest.raises(RuntimeError):
            extract_audio_from_video("/tmp/video.mp4")

    @patch("subprocess.run")
    def test_get_media_duration(self, mock_run):
        from app.services.media_service import get_media_duration
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps({"format": {"duration": "125.5"}})
        )
        duration = get_media_duration("/tmp/audio.mp3")
        assert duration == 125.5

    @patch("subprocess.run")
    def test_get_media_duration_failure(self, mock_run):
        from app.services.media_service import get_media_duration
        mock_run.return_value = MagicMock(returncode=1)
        duration = get_media_duration("/tmp/audio.mp3")
        assert duration == 0.0

    @pytest.mark.asyncio
    async def test_transcribe_audio(self):
        from app.services.media_service import transcribe_audio
        mock_transcript = MagicMock(
            text="Hello world",
            segments=[MagicMock(text=" Hello world", start=0.0, end=2.5)],
            language="en"
        )
        with patch("app.services.media_service.client") as mock_client, \
             patch("builtins.open", mock_open(read_data=b"audio data")):
            mock_client.audio.transcriptions.create = AsyncMock(return_value=mock_transcript)
            result = await transcribe_audio("/tmp/audio.mp3")
            assert result["text"] == "Hello world"
            assert result["language"] == "en"
            assert len(result["segments"]) == 1

    @pytest.mark.asyncio
    async def test_extract_topic_timestamps(self):
        from app.services.media_service import extract_topic_timestamps
        mock_topics = json.dumps([
            {"topic": "Introduction", "start_time": 0, "end_time": 30, "text": "Welcome"}
        ])
        with patch("app.services.media_service.client") as mock_client:
            mock_client.chat.completions.create = AsyncMock(return_value=MagicMock(
                choices=[MagicMock(message=MagicMock(content=mock_topics))]
            ))
            result = await extract_topic_timestamps(
                [{"text": " Hello", "start": 0.0, "end": 2.5}], "Hello"
            )
            assert len(result) == 1
            assert result[0]["topic"] == "Introduction"

    @pytest.mark.asyncio
    async def test_find_relevant_timestamps(self, mock_db):
        from app.services.media_service import find_relevant_timestamps
        segments_data = {
            "document_id": "doc123",
            "segments": [
                {"text": "machine learning models", "start": 10.0, "end": 20.0},
                {"text": "completely unrelated topic", "start": 20.0, "end": 30.0},
            ]
        }
        with patch("app.services.media_service.get_collection", return_value=AsyncMock(
            find_one=AsyncMock(return_value=segments_data)
        )):
            result = await find_relevant_timestamps("doc123", "machine learning models are powerful")
            assert len(result) > 0
            assert result[0]["start_time"] == 10.0


# ============================================================
# Chat Service Tests
# ============================================================

class TestChatService:
    @pytest.mark.asyncio
    async def test_get_or_create_conversation_new(self):
        from app.services.chat_service import get_or_create_conversation
        with patch("app.services.chat_service.get_collection") as mock_get_col:
            mock_col = AsyncMock()
            mock_col.find_one = AsyncMock(return_value=None)
            mock_col.insert_one = AsyncMock()
            mock_get_col.return_value = mock_col
            conv = await get_or_create_conversation(None, ["doc123"], "user123")
            assert "document_ids" in conv
            assert conv["user_id"] == "user123"
            mock_col.insert_one.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_or_create_conversation_existing(self):
        from app.services.chat_service import get_or_create_conversation
        existing_conv = {
            "_id": "conv123",
            "user_id": "user123",
            "document_ids": ["doc123"],
            "messages": [],
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }
        with patch("app.services.chat_service.get_collection") as mock_get_col:
            mock_col = AsyncMock()
            mock_col.find_one = AsyncMock(return_value=existing_conv)
            mock_get_col.return_value = mock_col
            conv = await get_or_create_conversation("conv123", ["doc123"], "user123")
            assert conv["_id"] == "conv123"

    @pytest.mark.asyncio
    async def test_chat_with_documents(self):
        from app.services.chat_service import chat_with_documents
        mock_chunks = [{"document_id": "doc123", "chunk_text": "AI is transforming industries.", "score": 0.5}]
        mock_answer = "AI is transforming industries significantly."

        with patch("app.services.chat_service.semantic_search", AsyncMock(return_value=mock_chunks)), \
             patch("app.services.chat_service.get_or_create_conversation", AsyncMock(return_value={
                 "_id": "conv1", "messages": []
             })), \
             patch("app.services.chat_service.add_message_to_conversation", AsyncMock()), \
             patch("app.services.chat_service.find_relevant_timestamps", AsyncMock(return_value=[])), \
             patch("app.services.chat_service.get_collection") as mock_gc, \
             patch("app.services.chat_service.client") as mock_client:
            mock_col = AsyncMock()
            mock_col.find_one = AsyncMock(return_value={"file_type": "pdf"})
            mock_gc.return_value = mock_col
            mock_client.chat.completions.create = AsyncMock(return_value=MagicMock(
                choices=[MagicMock(message=MagicMock(content=mock_answer))]
            ))
            result = await chat_with_documents("What is AI?", ["doc123"], None, "user123")
            assert result["answer"] == mock_answer
            assert result["conversation_id"] == "conv1"


# ============================================================
# API Route Tests (Integration-style)
# ============================================================

@pytest.fixture
async def async_client():
    from app.main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client


class TestHealthEndpoint:
    @pytest.mark.asyncio
    async def test_health_check(self, async_client):
        response = await async_client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"


class TestAuthRoutes:
    @pytest.mark.asyncio
    async def test_register_success(self, async_client, mock_db):
        with patch("app.api.routes.auth.get_collection", AsyncMock(return_value=mock_db)):
            response = await async_client.post("/api/v1/auth/register", json={
                "email": "newuser@example.com",
                "username": "newuser",
                "password": "securepass123"
            })
            assert response.status_code == 201
            data = response.json()
            assert data["email"] == "newuser@example.com"

    @pytest.mark.asyncio
    async def test_register_duplicate_user(self, async_client, mock_db, sample_user):
        mock_db.find_one = AsyncMock(return_value=sample_user)
        with patch("app.api.routes.auth.get_collection", AsyncMock(return_value=mock_db)):
            response = await async_client.post("/api/v1/auth/register", json={
                "email": "test@example.com",
                "username": "testuser",
                "password": "password123"
            })
            assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_login_success(self, async_client, sample_user):
        from app.core.security import get_password_hash
        sample_user["hashed_password"] = get_password_hash("testpassword")
        mock_col = AsyncMock()
        mock_col.find_one = AsyncMock(return_value=sample_user)
        with patch("app.api.routes.auth.get_collection", AsyncMock(return_value=mock_col)):
            response = await async_client.post("/api/v1/auth/token", data={
                "username": "testuser",
                "password": "testpassword"
            })
            assert response.status_code == 200
            data = response.json()
            assert "access_token" in data

    @pytest.mark.asyncio
    async def test_login_wrong_password(self, async_client, sample_user):
        mock_col = AsyncMock()
        mock_col.find_one = AsyncMock(return_value=sample_user)
        with patch("app.api.routes.auth.get_collection", AsyncMock(return_value=mock_col)):
            response = await async_client.post("/api/v1/auth/token", data={
                "username": "testuser",
                "password": "wrongpassword"
            })
            assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_login_user_not_found(self, async_client, mock_db):
        with patch("app.api.routes.auth.get_collection", AsyncMock(return_value=mock_db)):
            response = await async_client.post("/api/v1/auth/token", data={
                "username": "nonexistent",
                "password": "password"
            })
            assert response.status_code == 401


class TestDocumentRoutes:
    def _auth_header(self):
        from app.core.security import create_access_token
        token = create_access_token({"sub": "user123"})
        return {"Authorization": f"Bearer {token}"}

    @pytest.mark.asyncio
    async def test_upload_unsupported_file_type(self, async_client, sample_user):
        mock_col = AsyncMock()
        mock_col.find_one = AsyncMock(return_value=sample_user)
        with patch("app.db.mongodb.get_database", AsyncMock(return_value=AsyncMock(users=mock_col))):
            response = await async_client.post(
                "/api/v1/documents/upload",
                files={"file": ("test.txt", b"content", "text/plain")},
                headers=self._auth_header()
            )
            assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_list_documents_empty(self, async_client, sample_user):
        mock_col = AsyncMock()
        mock_col.find_one = AsyncMock(return_value=sample_user)
        doc_cursor = AsyncMock()
        doc_cursor.to_list = AsyncMock(return_value=[])
        doc_cursor.sort = MagicMock(return_value=doc_cursor)
        doc_col = AsyncMock()
        doc_col.find = MagicMock(return_value=doc_cursor)

        def get_col_side(name):
            if name == "users":
                return mock_col
            return doc_col

        with patch("app.db.mongodb.get_database", AsyncMock(return_value=AsyncMock(**{"users": mock_col}))), \
             patch("app.api.routes.documents.get_collection", AsyncMock(side_effect=get_col_side)):
            response = await async_client.get("/api/v1/documents/", headers=self._auth_header())
            assert response.status_code == 200
            assert response.json() == []

    @pytest.mark.asyncio
    async def test_get_document_not_found(self, async_client, sample_user):
        mock_col = AsyncMock()
        mock_col.find_one = AsyncMock(return_value=sample_user)
        doc_col = AsyncMock()
        doc_col.find_one = AsyncMock(return_value=None)
        with patch("app.db.mongodb.get_database", AsyncMock(return_value=AsyncMock(**{"users": mock_col}))), \
             patch("app.api.routes.documents.get_collection", AsyncMock(return_value=doc_col)):
            response = await async_client.get("/api/v1/documents/nonexistent", headers=self._auth_header())
            assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_timestamps_wrong_type(self, async_client, sample_user, sample_document):
        mock_col = AsyncMock()
        mock_col.find_one = AsyncMock(return_value=sample_user)
        doc_col = AsyncMock()
        doc_col.find_one = AsyncMock(return_value=sample_document)  # PDF, not audio
        with patch("app.db.mongodb.get_database", AsyncMock(return_value=AsyncMock(**{"users": mock_col}))), \
             patch("app.api.routes.documents.get_collection", AsyncMock(return_value=doc_col)):
            response = await async_client.get("/api/v1/documents/doc123/timestamps", headers=self._auth_header())
            assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_get_timestamps_audio(self, async_client, sample_user, sample_audio_document):
        mock_col = AsyncMock()
        mock_col.find_one = AsyncMock(return_value=sample_user)
        doc_col = AsyncMock()
        doc_col.find_one = AsyncMock(return_value=sample_audio_document)
        with patch("app.db.mongodb.get_database", AsyncMock(return_value=AsyncMock(**{"users": mock_col}))), \
             patch("app.api.routes.documents.get_collection", AsyncMock(return_value=doc_col)):
            response = await async_client.get("/api/v1/documents/audio123/timestamps", headers=self._auth_header())
            assert response.status_code == 200
            data = response.json()
            assert len(data["timestamps"]) == 2


class TestChatRoutes:
    def _auth_header(self):
        from app.core.security import create_access_token
        token = create_access_token({"sub": "user123"})
        return {"Authorization": f"Bearer {token}"}

    @pytest.mark.asyncio
    async def test_chat_no_documents(self, async_client, sample_user):
        mock_col = AsyncMock()
        mock_col.find_one = AsyncMock(return_value=sample_user)
        with patch("app.db.mongodb.get_database", AsyncMock(return_value=AsyncMock(**{"users": mock_col}))):
            response = await async_client.post(
                "/api/v1/chat/",
                json={"document_ids": [], "message": "Hello"},
                headers=self._auth_header()
            )
            assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_chat_document_not_found(self, async_client, sample_user, mock_db):
        mock_user_col = AsyncMock()
        mock_user_col.find_one = AsyncMock(return_value=sample_user)
        mock_doc_col = AsyncMock()
        mock_doc_col.find_one = AsyncMock(return_value=None)

        with patch("app.db.mongodb.get_database", AsyncMock(return_value=AsyncMock(**{"users": mock_user_col}))), \
             patch("app.api.routes.chat.get_collection", AsyncMock(return_value=mock_doc_col)):
            response = await async_client.post(
                "/api/v1/chat/",
                json={"document_ids": ["nonexistent"], "message": "What is this?"},
                headers=self._auth_header()
            )
            assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_chat_success(self, async_client, sample_user, sample_document):
        mock_user_col = AsyncMock()
        mock_user_col.find_one = AsyncMock(return_value=sample_user)
        mock_doc_col = AsyncMock()
        mock_doc_col.find_one = AsyncMock(return_value=sample_document)

        mock_result = {
            "conversation_id": "conv1",
            "answer": "This document is about machine learning.",
            "sources": [],
            "relevant_timestamps": [],
        }

        with patch("app.db.mongodb.get_database", AsyncMock(return_value=AsyncMock(**{"users": mock_user_col}))), \
             patch("app.api.routes.chat.get_collection", AsyncMock(return_value=mock_doc_col)), \
             patch("app.api.routes.chat.chat_with_documents", AsyncMock(return_value=mock_result)):
            response = await async_client.post(
                "/api/v1/chat/",
                json={"document_ids": ["doc123"], "message": "What is this about?"},
                headers=self._auth_header()
            )
            assert response.status_code == 200
            data = response.json()
            assert data["conversation_id"] == "conv1"
            assert "assistant" in data["message"]["role"]


# ============================================================
# Models / Schema Tests
# ============================================================

class TestModels:
    def test_document_response_model(self):
        from app.models.document import DocumentResponse, FileType, ProcessingStatus
        doc = DocumentResponse(
            id="doc123",
            filename="test.pdf",
            original_filename="test.pdf",
            file_type=FileType.PDF,
            file_size=1024,
            owner_id="user123",
            storage_path="/tmp/test.pdf",
            status=ProcessingStatus.COMPLETED,
            chunk_count=5,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        assert doc.file_type == FileType.PDF
        assert doc.status == ProcessingStatus.COMPLETED

    def test_chat_request_model(self):
        from app.models.chat import ChatRequest
        req = ChatRequest(
            document_ids=["doc1", "doc2"],
            message="What is this about?",
        )
        assert len(req.document_ids) == 2
        assert req.stream is False

    def test_user_create_validation(self):
        from app.models.chat import UserCreate
        with pytest.raises(Exception):
            UserCreate(email="invalid-email", username="u", password="short")

    def test_file_type_enum(self):
        from app.models.document import FileType
        assert FileType.PDF == "pdf"
        assert FileType.AUDIO == "audio"
        assert FileType.VIDEO == "video"

    def test_processing_status_enum(self):
        from app.models.document import ProcessingStatus
        assert ProcessingStatus.COMPLETED == "completed"
        assert ProcessingStatus.FAILED == "failed"
