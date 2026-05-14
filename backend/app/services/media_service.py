import os
import json
import logging
import subprocess
from typing import List, Optional, Tuple
from datetime import datetime

from openai import AsyncOpenAI

from app.core.config import settings
from app.db.mongodb import get_collection
from app.services.document_service import chunk_text, build_faiss_index

logger = logging.getLogger(__name__)
client = AsyncOpenAI(
    api_key=settings.OPENAI_API_KEY,
    base_url=settings.OPENAI_BASE_URL
)


def extract_audio_from_video(video_path: str) -> str:
    """Extract audio track from video using ffmpeg."""
    audio_path = video_path.rsplit(".", 1)[0] + "_audio.mp3"
    cmd = [
        "ffmpeg", "-i", video_path,
        "-vn", "-acodec", "mp3",
        "-ar", "16000", "-ac", "1",
        "-y", audio_path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg failed: {result.stderr}")
    return audio_path


def get_media_duration(file_path: str) -> float:
    """Get duration of audio/video file in seconds."""
    cmd = [
        "ffprobe", "-v", "quiet",
        "-print_format", "json",
        "-show_format", file_path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode == 0:
        data = json.loads(result.stdout)
        return float(data.get("format", {}).get("duration", 0))
    return 0.0


async def transcribe_audio(file_path: str) -> dict:
    """
    Transcribe audio using OpenAI Whisper API.
    Returns transcript with word-level timestamps.
    """
    with open(file_path, "rb") as audio_file:
        response = await client.audio.transcriptions.create(
            model="whisper-large-v3",
            file=audio_file,
            response_format="verbose_json",
            timestamp_granularities=["segment"],
        )

    segments = []
    if hasattr(response, "segments") and response.segments:
        for seg in response.segments:
            if isinstance(seg, dict):
                segments.append({
                    "text": seg.get("text", ""),
                    "start": seg.get("start", 0),
                    "end": seg.get("end", 0),
                })
            else:
                segments.append({
                    "text": seg.text,
                    "start": seg.start,
                    "end": seg.end,
                })

    return {
        "text": response.text,
        "segments": segments,
        "language": getattr(response, "language", "en"),
    }


async def extract_topic_timestamps(transcript_segments: List[dict], full_text: str) -> List[dict]:
    """Use LLM to identify key topics and their timestamps in the transcript."""
    segments_json = json.dumps(transcript_segments[:100])  # limit for token safety

    response = await client.chat.completions.create(
        model=settings.OPENAI_MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are an expert at analyzing transcripts. "
                    "Given transcript segments with timestamps, identify the main topics discussed "
                    "and return a JSON array. Each item should have: "
                    "'topic' (short title), 'start_time' (seconds), 'end_time' (seconds), 'text' (brief description). "
                    "Return ONLY the JSON array, no other text."
                ),
            },
            {
                "role": "user",
                "content": f"Analyze these transcript segments and identify key topics:\n{segments_json}",
            },
        ],
    )

    content = response.choices[0].message.content.strip()
    # Strip markdown fences if present
    if content.startswith("```"):
        content = content.split("```")[1]
        if content.startswith("json"):
            content = content[4:]
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        logger.error(f"Failed to parse topic timestamps: {content}")
        return []


async def process_media(document_id: str, file_path: str, file_type: str) -> dict:
    """Full pipeline: extract audio (if video), transcribe, chunk, and index."""
    audio_path = file_path
    if file_type == "video":
        audio_path = extract_audio_from_video(file_path)

    duration = get_media_duration(file_path)
    transcript_data = await transcribe_audio(audio_path)

    full_text = transcript_data["text"]
    segments = transcript_data.get("segments", [])

    # Store segments for timestamp lookup
    segments_collection = await get_collection("segments")
    if segments:
        await segments_collection.insert_one({
            "document_id": document_id,
            "segments": segments,
            "created_at": datetime.utcnow(),
        })

    # Extract topic-level timestamps
    timestamps = []
    if segments:
        timestamps = await extract_topic_timestamps(segments, full_text)

    # Chunk and index transcript
    chunks = chunk_text(full_text)
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
        "extracted_text": full_text,
        "chunk_count": len(chunks),
        "duration_seconds": duration,
        "timestamps": timestamps,
        "segments": segments,
    }


async def find_relevant_timestamps(document_id: str, answer_text: str) -> List[dict]:
    """Find segments in a transcript that are relevant to a given answer."""
    segments_collection = await get_collection("segments")
    doc = await segments_collection.find_one({"document_id": document_id})
    if not doc or not doc.get("segments"):
        return []

    segments = doc["segments"]
    answer_lower = answer_text.lower()
    relevant = []

    for seg in segments:
        seg_text = seg.get("text", "").lower()
        # Simple keyword overlap check
        words = set(answer_lower.split())
        seg_words = set(seg_text.split())
        overlap = len(words & seg_words) / max(len(words), 1)
        if overlap > 0.15:
            relevant.append({
                "start_time": seg["start"],
                "end_time": seg["end"],
                "text": seg["text"],
            })

    relevant.sort(key=lambda x: x["start_time"])
    return relevant[:3]
