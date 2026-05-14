# DocuAI — AI-Powered Document & Multimedia Q&A

> Upload PDFs, audio, and video files, then chat with an AI that answers questions from your content — with timestamp-aware playback for audio and video.

![CI/CD](https://github.com/your-username/docuai/actions/workflows/ci.yml/badge.svg)
[![Coverage](https://codecov.io/gh/your-username/docuai/branch/main/graph/badge.svg)](https://codecov.io/gh/your-username/docuai)

---

## Features

| Feature | Details |
|---|---|
| **File Upload** | PDF, MP3, WAV, M4A, MP4, MOV, AVI, MKV (up to 100 MB) |
| **AI Chat** | GPT-4o answers questions grounded in your documents |
| **Streaming Responses** | Real-time token-by-token streaming via SSE |
| **Semantic Search** | FAISS vector search across all uploaded documents |
| **Audio/Video Transcription** | OpenAI Whisper with word-level timestamps |
| **Topic Timestamps** | LLM-detected topics with start/end times |
| **Media Player** | In-app player with seek-to-timestamp from chat answers |
| **Document Summary** | Auto-generated summaries and key topics |
| **Multi-user Auth** | JWT-based authentication with bcrypt passwords |
| **Caching** | Redis for rate limiting and response caching |
| **CI/CD** | GitHub Actions with 95%+ test coverage gate |
| **Docker** | Full multi-container setup via Docker Compose |

---

## Architecture

```
┌────────────────┐    HTTP/SSE    ┌──────────────────────┐
│  React Frontend│ ◄────────────► │  FastAPI Backend      │
│  (Vite + TS)   │                │  Port 8000            │
└────────────────┘                └──────────┬───────────┘
                                             │
                          ┌──────────────────┼──────────────────┐
                          │                  │                  │
                   ┌──────▼──────┐  ┌────────▼───────┐  ┌──────▼──────┐
                   │  MongoDB    │  │  FAISS Index   │  │  Redis      │
                   │  (docs,     │  │  (embeddings   │  │  (cache +   │
                   │  chunks,    │  │  per document) │  │  rate limit)│
                   │  users)     │  └────────────────┘  └─────────────┘
                   └─────────────┘
                          │
             ┌────────────┼────────────┐
             │            │            │
      ┌──────▼───┐  ┌─────▼────┐  ┌───▼─────┐
      │ OpenAI   │  │ Whisper  │  │ ffmpeg  │
      │ GPT-4o   │  │ ASR API  │  │ (audio  │
      │ Embeddings│  │          │  │ extract)│
      └──────────┘  └──────────┘  └─────────┘
```

---

## Quick Start

### Prerequisites

- Docker & Docker Compose
- An OpenAI API key ([get one here](https://platform.openai.com/api-keys))

### 1. Clone & Configure

```bash
git clone https://github.com/your-username/docuai.git
cd docuai

# Backend environment
cp backend/.env.example backend/.env
# Edit backend/.env and set OPENAI_API_KEY and SECRET_KEY

# Frontend environment
cp frontend/.env.example frontend/.env
```

### 2. Start with Docker Compose

```bash
OPENAI_API_KEY=sk-your-key docker compose up --build
```

Or with an `.env` file in the project root:

```bash
# .env (project root)
OPENAI_API_KEY=sk-your-key
SECRET_KEY=your-strong-random-secret

docker compose up --build
```

App is available at:
- **Frontend:** http://localhost:3000
- **Backend API:** http://localhost:8000
- **API Docs:** http://localhost:8000/docs

---

## Local Development (without Docker)

### Backend

```bash
cd backend

# Create virtual environment
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate

# Install dependencies (requires ffmpeg system package)
# macOS:  brew install ffmpeg
# Ubuntu: sudo apt-get install ffmpeg
pip install -r requirements.txt

# Configure
cp .env.example .env            # Edit with your OPENAI_API_KEY

# Start MongoDB and Redis (or use Docker for just these)
docker run -d -p 27017:27017 mongo:7.0
docker run -d -p 6379:6379 redis:7.2-alpine

# Run
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend

npm install

# Configure
cp .env.example .env            # VITE_API_URL=http://localhost:8000/api/v1

npm run dev                     # http://localhost:3000
```

---

## API Documentation

Full interactive docs: **http://localhost:8000/docs**

### Authentication

```http
POST /api/v1/auth/register
Content-Type: application/json

{
  "email": "user@example.com",
  "username": "myuser",
  "password": "securepassword"
}
```

```http
POST /api/v1/auth/token
Content-Type: application/x-www-form-urlencoded

username=myuser&password=securepassword
```

All subsequent requests require: `Authorization: Bearer <token>`

---

### Documents

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/documents/upload` | Upload a file (multipart/form-data) |
| `GET` | `/api/v1/documents/` | List all user documents |
| `GET` | `/api/v1/documents/{id}` | Get document details + status |
| `GET` | `/api/v1/documents/{id}/summary` | Get AI-generated summary |
| `GET` | `/api/v1/documents/{id}/timestamps` | Get topic timestamps (audio/video) |
| `DELETE` | `/api/v1/documents/{id}` | Delete document and all data |

**Upload example:**
```bash
curl -X POST http://localhost:8000/api/v1/documents/upload \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@report.pdf"
```

**Response:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "filename": "550e8400.pdf",
  "original_filename": "report.pdf",
  "file_type": "pdf",
  "status": "pending",
  "chunk_count": 0,
  "created_at": "2025-01-15T10:00:00Z"
}
```

---

### Chat

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/chat/` | Send message (supports streaming) |
| `GET` | `/api/v1/chat/conversations` | List conversations |
| `GET` | `/api/v1/chat/conversations/{id}` | Get conversation history |
| `DELETE` | `/api/v1/chat/conversations/{id}` | Delete conversation |

**Chat request:**
```bash
curl -X POST http://localhost:8000/api/v1/chat/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "document_ids": ["doc-id-1", "doc-id-2"],
    "message": "What are the key findings?",
    "stream": false
  }'
```

**Streaming chat (SSE):**
```bash
curl -X POST http://localhost:8000/api/v1/chat/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"document_ids": ["doc-id"], "message": "Summarize", "stream": true}'
```
Response: `text/event-stream` — each line is `data: <token>`, ending with `data: [DONE]`

**Response:**
```json
{
  "conversation_id": "conv-uuid",
  "message": {
    "role": "assistant",
    "content": "The key findings are...",
    "sources": [
      { "document_id": "doc-id", "chunk_text": "...", "score": 0.12 }
    ],
    "timestamp_refs": [
      { "document_id": "doc-id", "start_time": 42.5, "end_time": 68.0, "text": "..." }
    ]
  }
}
```

---

### Media Streaming

```http
GET /api/v1/media/{document_id}/stream
Authorization: Bearer <token>
Range: bytes=0-                    # Optional: seek support
```

Returns the audio/video file with HTTP 206 range support (enables seeking in the browser player).

---

## Testing

```bash
cd backend

# Run all tests
pytest tests/ -v

# Run with coverage report
pytest tests/ --cov=app --cov-report=term-missing --cov-report=html

# Open HTML coverage report
open htmlcov/index.html           # macOS
xdg-open htmlcov/index.html      # Linux
```

Coverage target: **≥ 95%** (enforced in CI).

Test categories:
- `TestConfig` — Settings and environment
- `TestSecurity` — JWT, password hashing
- `TestDocumentService` — PDF extraction, chunking, FAISS indexing, embeddings
- `TestMediaService` — ffmpeg, Whisper transcription, timestamp extraction
- `TestChatService` — Conversation management, LLM calls, streaming
- `TestAuthRoutes` — Register, login, token validation
- `TestDocumentRoutes` — Upload, list, get, delete, summary, timestamps
- `TestChatRoutes` — Chat, conversation CRUD
- `TestModels` — Pydantic schema validation

---

## Project Structure

```
docuai/
├── backend/
│   ├── app/
│   │   ├── api/routes/
│   │   │   ├── auth.py          # Register, login, /me
│   │   │   ├── chat.py          # Chat + conversation history
│   │   │   ├── documents.py     # Upload, list, summary, timestamps
│   │   │   └── media.py         # Audio/video streaming
│   │   ├── core/
│   │   │   ├── config.py        # Pydantic settings
│   │   │   └── security.py      # JWT, bcrypt
│   │   ├── db/
│   │   │   └── mongodb.py       # Motor async client
│   │   ├── models/
│   │   │   ├── document.py      # Document schemas
│   │   │   └── chat.py          # Chat/user schemas
│   │   ├── services/
│   │   │   ├── document_service.py  # PDF extract, FAISS index
│   │   │   ├── media_service.py     # ffmpeg, Whisper, timestamps
│   │   │   └── chat_service.py      # LLM chat, streaming
│   │   ├── utils/
│   │   │   └── cache.py         # Redis helpers
│   │   └── main.py              # FastAPI app + lifespan
│   ├── tests/
│   │   └── test_main.py         # 95%+ coverage test suite
│   ├── .env.example
│   ├── Dockerfile
│   ├── pytest.ini
│   └── requirements.txt
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── chat/
│   │   │   │   └── ChatPanel.tsx    # Streaming chat UI + sources
│   │   │   ├── layout/
│   │   │   │   ├── Dashboard.tsx    # Main layout
│   │   │   │   └── LoginPage.tsx    # Auth page
│   │   │   ├── media/
│   │   │   │   └── MediaPlayer.tsx  # Audio/video player + seek
│   │   │   └── upload/
│   │   │       └── DocumentPanel.tsx # Dropzone + document list
│   │   ├── services/
│   │   │   └── api.ts           # Axios + streaming fetch
│   │   ├── store/
│   │   │   └── index.ts         # Zustand auth/docs/chat stores
│   │   ├── styles/
│   │   │   └── globals.css      # Design tokens + animations
│   │   ├── App.tsx
│   │   └── main.tsx
│   ├── .env.example
│   ├── Dockerfile
│   ├── nginx.conf
│   ├── package.json
│   ├── tsconfig.json
│   └── vite.config.ts
│
├── .github/
│   └── workflows/
│       └── ci.yml               # Test → Build → Deploy pipeline
│
└── docker-compose.yml
```

---

## Deployment (AWS/GCP/Azure)

### AWS EC2 Example

```bash
# 1. Launch EC2 instance (Ubuntu 22.04, t3.medium recommended)
# 2. Install Docker
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker ubuntu

# 3. Clone repo
git clone https://github.com/your-username/docuai.git
cd docuai

# 4. Set secrets
echo "OPENAI_API_KEY=sk-your-key" > .env
echo "SECRET_KEY=$(openssl rand -hex 32)" >> .env

# 5. Start
docker compose up -d

# 6. (Optional) Point a domain + add SSL with Certbot/Nginx
```

### CI/CD Secrets Required

Set these in **GitHub → Settings → Secrets and variables → Actions**:

| Secret | Description |
|--------|-------------|
| `DEPLOY_HOST` | Server IP or hostname |
| `DEPLOY_USER` | SSH username (e.g. `ubuntu`) |
| `DEPLOY_SSH_KEY` | Private SSH key for server access |

---

## Bonus Features Implemented

- ✅ **FAISS vector search** — semantic similarity search across all document chunks
- ✅ **Real-time streaming** — SSE-based token streaming from GPT-4o
- ✅ **JWT authentication** — secure login/register with bcrypt
- ✅ **Redis caching** — graceful fallback if Redis is unavailable
- ✅ **HTTP range requests** — full seek support for audio/video playback
- ✅ **Background processing** — document indexing runs async after upload
- ✅ **Multi-document chat** — query across multiple files simultaneously

---

## Walkthrough Video

🎥 [Watch the demo on YouTube](https://youtube.com/your-link-here)

---

## License

MIT
