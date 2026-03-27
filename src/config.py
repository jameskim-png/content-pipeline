"""Configuration and API key management."""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import requests

PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
OUTPUT_DIR = PROJECT_ROOT / "output"
PERSONAS_DIR = PROJECT_ROOT / "personas"
MOTION_REFS_DIR = DATA_DIR / "motion-references"

load_dotenv(PROJECT_ROOT / ".env")

EMOTION_CATEGORIES = [
    "neutral", "calm", "excited", "thinking", "happy",
    "sad", "surprised", "explaining", "emphatic", "playful",
]


def get_api_key(name: str, required: bool = True) -> str | None:
    """Get an API key from environment variables."""
    value = os.getenv(name)
    if required and not value:
        print(f"ERROR: {name} not found in .env file.", file=sys.stderr)
        print(f"Add it to {PROJECT_ROOT / '.env'} (see .env.template)", file=sys.stderr)
        sys.exit(1)
    return value


def validate_keys(model_choice: str = "heygen", tts_engine: str = "fal") -> dict[str, str]:
    """Validate all required API keys based on model choice. Returns key dict."""
    keys = {}

    # kling26 only needs FAL_KEY; heygen needs both FAL + HEYGEN
    if model_choice.lower() in ("kling26", "kling_avatar", "kling3", "veo3"):
        keys["FAL_KEY"] = get_api_key("FAL_KEY")
    elif model_choice.lower() == "heygen":
        keys["FAL_KEY"] = get_api_key("FAL_KEY")
        keys["HEYGEN_API_KEY"] = get_api_key("HEYGEN_API_KEY")
    else:
        keys["FAL_KEY"] = get_api_key("FAL_KEY")

    # TTS engine keys
    if tts_engine == "elevenlabs":
        keys["ELEVENLABS_API_KEY"] = get_api_key("ELEVENLABS_API_KEY")
    elif tts_engine == "google":
        pass  # Uses gcloud Application Default Credentials, no env key needed
    else:
        # fal — already covered above
        elevenlabs = get_api_key("ELEVENLABS_API_KEY", required=False)
        if elevenlabs:
            keys["ELEVENLABS_API_KEY"] = elevenlabs

    return keys


def ensure_dirs(*dirs: Path) -> None:
    """Create directories if they don't exist."""
    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)


def check_fal_balance() -> dict:
    """Check fal.ai account balance."""
    try:
        api_key = os.getenv("FAL_KEY")
        if not api_key:
            return {"error": "FAL_KEY not set"}
        resp = requests.get(
            "https://api.fal.ai/v1/account/billing?expand=credits",
            headers={"Authorization": f"Key {api_key}"},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        balance = data.get("credits", {}).get("balance", data.get("balance", 0))
        return {"balance": float(balance), "currency": "USD"}
    except Exception as e:
        return {"error": str(e)}


def check_heygen_balance() -> dict:
    """Check HeyGen remaining quota."""
    try:
        api_key = os.getenv("HEYGEN_API_KEY")
        if not api_key:
            return {"error": "HEYGEN_API_KEY not set"}
        resp = requests.get(
            "https://api.heygen.com/v2/user/remaining_quota",
            headers={"X-Api-Key": api_key},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json().get("data", {})
        return {"remaining_quota": float(data.get("remaining_quota", 0))}
    except Exception as e:
        return {"error": str(e)}


def check_elevenlabs_balance() -> dict:
    """Check ElevenLabs character usage."""
    try:
        api_key = os.getenv("ELEVENLABS_API_KEY")
        if not api_key:
            return {"error": "ELEVENLABS_API_KEY not set"}
        resp = requests.get(
            "https://api.elevenlabs.io/v1/user/subscription",
            headers={"xi-api-key": api_key},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        used = data.get("character_count", 0)
        limit = data.get("character_limit", 0)
        return {"used": used, "limit": limit, "remaining": limit - used}
    except Exception as e:
        return {"error": str(e)}


def estimate_job_cost(
    model: str,
    n_chunks: int,
    total_duration: float,
    tts_engine: str = "fal",
    total_chars: int = 0,
    original_content: bool = False,
) -> dict:
    """Estimate pipeline cost based on model and chunk count.

    Rough per-unit costs (USD):
      STT (Whisper via fal): ~$0.003/min (skipped for original_content)
      TTS: fal F5-TTS ~$0.01/chunk, ElevenLabs ~$0.03/chunk,
           Google Cloud TTS ~$0.000016/char
      Video: heygen ~$0.50/min, kling_avatar ~$0.10/chunk,
             kling3 ~$0.15/chunk (+musetalk $0.05),
             kling26 ~$0.35/chunk (Kling 2.6) + $0.10/chunk (Sync Lipsync),
             veo3 ~$0.25/chunk
      Image gen: ~$0.04/image (1-2 images)

    original_content: if True, skips STT cost (no source video to transcribe).
    """
    duration_min = total_duration / 60.0

    stt_cost = 0.0 if original_content else round(duration_min * 0.003, 4)

    # TTS cost by engine
    tts_rates = {
        "fal": lambda: round(n_chunks * 0.01, 4),
        "elevenlabs": lambda: round(n_chunks * 0.03, 4),
        "google": lambda: round(total_chars * 0.000016, 4) if total_chars else round(n_chunks * 0.005, 4),
    }
    tts_cost = tts_rates.get(tts_engine, tts_rates["fal"])()

    # kling26 only needs 1 reference image; others need character sheet + background
    image_cost = 0.04 if model.lower() == "kling26" else 0.08

    video_rates = {
        "heygen": 0.50,
        "kling_avatar": 0.10,
        "kling3": 0.20,
        "kling26": 0.45,  # $0.35 Kling 2.6 + $0.10 Sync Lipsync
        "veo3": 0.25,
    }
    per_chunk_video = video_rates.get(model.lower(), 0.15)
    video_cost = round(n_chunks * per_chunk_video, 4)

    total = round(stt_cost + tts_cost + image_cost + video_cost, 4)

    return {
        "stt": stt_cost,
        "tts": tts_cost,
        "tts_engine": tts_engine,
        "image": image_cost,
        "video": video_cost,
        "total": total,
        "model": model,
        "n_chunks": n_chunks,
        "total_duration_s": total_duration,
    }
