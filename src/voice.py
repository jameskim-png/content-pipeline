"""Voice generation (TTS) for translated chunks."""

import json
from pathlib import Path

import fal_client

from .config import get_api_key, ensure_dirs
from .utils import save_json, get_audio_duration


def generate_voice_elevenlabs(
    text: str,
    output_path: Path,
    voice_id: str = "21m00Tcm4TlvDq8ikWAM",  # Default: Rachel
    model_id: str = "eleven_multilingual_v2",
    stability: float = 0.5,
    similarity_boost: float = 0.75,
) -> Path:
    """Generate voice using ElevenLabs API.

    Returns path to generated audio file.
    """
    from elevenlabs import ElevenLabs

    api_key = get_api_key("ELEVENLABS_API_KEY")
    client = ElevenLabs(api_key=api_key)

    output_path.parent.mkdir(parents=True, exist_ok=True)

    audio = client.text_to_speech.convert(
        voice_id=voice_id,
        text=text,
        model_id=model_id,
        voice_settings={
            "stability": stability,
            "similarity_boost": similarity_boost,
        },
    )

    with open(output_path, "wb") as f:
        for chunk in audio:
            f.write(chunk)

    return output_path


def generate_voice_fal(
    text: str,
    output_path: Path,
    language: str = "ko",
    ref_audio_path: Path | None = None,
) -> Path:
    """Generate voice using fal.ai F5-TTS.

    Falls back to this when ElevenLabs key is not available.
    If ref_audio_path is provided, uploads it as reference audio for voice cloning.
    """
    get_api_key("FAL_KEY")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    arguments = {"gen_text": text}

    if ref_audio_path and ref_audio_path.exists():
        ref_url = fal_client.upload_file(ref_audio_path)
        arguments["ref_audio_url"] = ref_url

    result = fal_client.subscribe(
        "fal-ai/f5-tts",
        arguments=arguments,
    )

    audio_url = result.get("audio_url", {}).get("url", "")
    if audio_url:
        _download_file(audio_url, output_path)

    return output_path


def generate_voice_google(
    text: str,
    output_path: Path,
    voice_name: str = "ko-KR-Chirp3-HD-Leda",
    speaking_rate: float = 1.0,
) -> Path:
    """Generate voice using Google Cloud TTS.

    Requires gcloud auth (Application Default Credentials).
    Default voice: ko-KR-Chirp3-HD-Leda (natural Korean female).
    """
    from google.cloud import texttospeech

    client = texttospeech.TextToSpeechClient()

    synthesis_input = texttospeech.SynthesisInput(text=text)

    # Extract language_code (e.g. "ko-KR") from voice_name (e.g. "ko-KR-Chirp3-HD-Leda")
    parts = voice_name.split("-")
    language_code = "-".join(parts[:2]) if len(parts) >= 2 else "ko-KR"

    voice = texttospeech.VoiceSelectionParams(
        language_code=language_code,
        name=voice_name,
    )

    audio_config = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.LINEAR16,
        speaking_rate=speaking_rate,
    )

    response = client.synthesize_speech(
        input=synthesis_input,
        voice=voice,
        audio_config=audio_config,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "wb") as f:
        f.write(response.audio_content)

    return output_path


def generate_chunk_voices(
    translation: dict,
    output_dir: Path,
    tts_engine: str = "fal",
    use_elevenlabs: bool = False,
    voice_id: str | None = None,
    voice_name: str | None = None,
    ref_audio_path: Path | None = None,
    speaking_rate: float = 1.0,
) -> list[dict]:
    """Generate voice for all translated chunks.

    tts_engine: "google", "elevenlabs", "fal" (default).
    For backward compat, use_elevenlabs=True overrides tts_engine to "elevenlabs".
    speaking_rate: TTS speed multiplier (1.0=normal, 1.2=20% faster). Google TTS only.
    Returns list of dicts with chunk_id, voice_path, text, and actual_duration.
    Skips chunks whose output file already exists and has size > 0.
    """
    # Backward compatibility: use_elevenlabs flag overrides tts_engine
    if use_elevenlabs and voice_id:
        tts_engine = "elevenlabs"

    ensure_dirs(output_dir)
    results = []

    for chunk in translation.get("chunks", []):
        chunk_id = chunk["chunk_id"]
        text = chunk.get("translated", chunk.get("text", ""))
        output_path = output_dir / f"{chunk_id}_voice.wav"

        # Skip if already generated
        if output_path.exists() and output_path.stat().st_size > 0:
            print(f"  {chunk_id}: already exists, skipping generation")
        else:
            if tts_engine == "google":
                kwargs = {}
                if voice_name:
                    kwargs["voice_name"] = voice_name
                if speaking_rate != 1.0:
                    kwargs["speaking_rate"] = speaking_rate
                generate_voice_google(text, output_path, **kwargs)
            elif tts_engine == "elevenlabs" and voice_id:
                generate_voice_elevenlabs(text, output_path, voice_id=voice_id)
            else:
                generate_voice_fal(text, output_path, ref_audio_path=ref_audio_path)

        # Measure actual duration
        actual_duration = 0.0
        try:
            actual_duration = get_audio_duration(output_path)
        except Exception:
            pass

        # Warn if duration deviates >10% from original
        original_duration = chunk.get("original_duration", chunk.get("duration", 0))
        if original_duration and actual_duration:
            deviation = abs(actual_duration - original_duration) / original_duration
            if deviation > 0.10:
                print(
                    f"  WARNING: {chunk_id} duration mismatch — "
                    f"original={original_duration:.2f}s, actual={actual_duration:.2f}s "
                    f"({deviation:.0%} off)"
                )

        results.append({
            "chunk_id": chunk_id,
            "voice_path": str(output_path),
            "text": text,
            "actual_duration": round(actual_duration, 3),
        })

    save_json(results, output_dir / "voice_manifest.json")
    return results


def _download_file(url: str, path: Path) -> None:
    """Download file from URL."""
    import requests

    response = requests.get(url, timeout=120)
    response.raise_for_status()
    with open(path, "wb") as f:
        f.write(response.content)
