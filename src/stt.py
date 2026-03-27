"""Speech-to-text using fal.ai Whisper API."""

import json
import base64
from pathlib import Path

import fal_client

from .config import get_api_key
from .utils import save_json


def transcribe(audio_path: Path, language: str | None = None) -> dict:
    """Transcribe audio using fal.ai Whisper.

    Args:
        audio_path: Path to audio file (WAV recommended).
        language: Optional language hint (e.g., "en", "ko").

    Returns:
        Whisper result dict with text, segments, and word-level timestamps.
    """
    get_api_key("FAL_KEY")  # Validate key exists

    # Upload audio file to fal
    audio_url = fal_client.upload_file(audio_path)

    # Run Whisper
    input_params = {
        "audio_url": audio_url,
        "task": "transcribe",
        "chunk_level": "segment",
        "version": "3",
    }

    if language:
        input_params["language"] = language

    result = fal_client.subscribe(
        "fal-ai/whisper",
        arguments=input_params,
    )

    return result


def transcribe_and_save(
    audio_path: Path,
    output_path: Path,
    language: str | None = None,
) -> dict:
    """Transcribe audio and save result to JSON.

    Returns the transcript dict.
    """
    result = transcribe(audio_path, language)

    transcript = {
        "text": result.get("text", ""),
        "language": result.get("language", language or "unknown"),
        "segments": result.get("chunks", []),
    }

    save_json(transcript, output_path)
    return transcript


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python -m src.stt <audio_path> [output_path] [language]")
        sys.exit(1)

    audio = Path(sys.argv[1])
    output = Path(sys.argv[2]) if len(sys.argv) > 2 else audio.parent / "transcript.json"
    lang = sys.argv[3] if len(sys.argv) > 3 else None

    result = transcribe_and_save(audio, output, lang)
    print(json.dumps(result, indent=2, ensure_ascii=False))
