"""Video generation using HeyGen, Kling, or VEO via fal.ai."""

import json
import subprocess
import time
from pathlib import Path

import requests
import fal_client

from .config import get_api_key, ensure_dirs
from .utils import save_json
from .persona import composite_face_on_background


# --- HeyGen ---

HEYGEN_BASE_URL = "https://api.heygen.com"


def heygen_create_avatar(image_path: Path) -> str:
    """Create a HeyGen photo avatar from a face image.

    Returns the avatar_id.
    """
    api_key = get_api_key("HEYGEN_API_KEY")
    headers = {"X-Api-Key": api_key}

    with open(image_path, "rb") as f:
        response = requests.post(
            f"{HEYGEN_BASE_URL}/v2/photo_avatar",
            headers=headers,
            files={"image": f},
        )
    response.raise_for_status()
    data = response.json()
    return data["data"]["photo_avatar_id"]


def heygen_generate_video(
    avatar_id: str,
    audio_path: Path,
    output_path: Path,
    background_path: Path | None = None,
) -> Path:
    """Generate a talking head video with HeyGen.

    Uses photo avatar + audio for lip-synced video.
    """
    api_key = get_api_key("HEYGEN_API_KEY")
    headers = {
        "X-Api-Key": api_key,
        "Content-Type": "application/json",
    }

    # Upload audio
    with open(audio_path, "rb") as f:
        upload_resp = requests.post(
            f"{HEYGEN_BASE_URL}/v1/asset",
            headers={"X-Api-Key": api_key},
            files={"file": f},
        )
    upload_resp.raise_for_status()
    audio_asset_id = upload_resp.json()["data"]["asset_id"]

    # Build video request
    video_input = {
        "video_inputs": [{
            "character": {
                "type": "photo_avatar",
                "photo_avatar_id": avatar_id,
            },
            "voice": {
                "type": "audio",
                "audio_asset_id": audio_asset_id,
            },
        }],
        "dimension": {"width": 1080, "height": 1920},
    }

    if background_path:
        with open(background_path, "rb") as f:
            bg_resp = requests.post(
                f"{HEYGEN_BASE_URL}/v1/asset",
                headers={"X-Api-Key": api_key},
                files={"file": f},
            )
        bg_resp.raise_for_status()
        bg_asset_id = bg_resp.json()["data"]["asset_id"]
        video_input["video_inputs"][0]["background"] = {
            "type": "image",
            "image_asset_id": bg_asset_id,
        }

    # Create video
    create_resp = requests.post(
        f"{HEYGEN_BASE_URL}/v2/video/generate",
        headers=headers,
        json=video_input,
    )
    create_resp.raise_for_status()
    video_id = create_resp.json()["data"]["video_id"]

    # Poll for completion
    video_url = _heygen_poll_video(api_key, video_id)
    _download_file(video_url, output_path)

    return output_path


def _heygen_poll_video(api_key: str, video_id: str, timeout: int = 600) -> str:
    """Poll HeyGen for video completion. Returns video URL."""
    headers = {"X-Api-Key": api_key}
    start = time.time()

    while time.time() - start < timeout:
        resp = requests.get(
            f"{HEYGEN_BASE_URL}/v1/video_status.get",
            headers=headers,
            params={"video_id": video_id},
        )
        resp.raise_for_status()
        data = resp.json()["data"]

        if data["status"] == "completed":
            return data["video_url"]
        elif data["status"] == "failed":
            raise RuntimeError(f"HeyGen video generation failed: {data.get('error', 'unknown')}")

        time.sleep(10)

    raise TimeoutError(f"HeyGen video generation timed out after {timeout}s")


# --- Kling Avatar v2 (fal.ai) ---

def kling_avatar_generate(
    face_image_path: Path,
    audio_path: Path,
    output_path: Path,
) -> Path:
    """Generate talking head video using Kling Avatar v2 via fal.ai."""
    get_api_key("FAL_KEY")
    ensure_dirs(output_path.parent)

    face_url = fal_client.upload_file(face_image_path)
    audio_url = fal_client.upload_file(audio_path)

    result = fal_client.subscribe(
        "fal-ai/kling-video/ai-avatar/v2/standard",
        arguments={
            "face_image_url": face_url,
            "audio_url": audio_url,
        },
    )

    video_url = result.get("video", {}).get("url", "")
    if video_url:
        _download_file(video_url, output_path)

    return output_path


# --- Kling 3.0 + MuseTalk (fal.ai) ---

def kling_video_generate(
    reference_image_path: Path,
    prompt: str,
    output_path: Path,
    duration: str = "5",
) -> Path:
    """Generate video using Kling 3.0 via fal.ai (no lip sync)."""
    get_api_key("FAL_KEY")
    ensure_dirs(output_path.parent)

    image_url = fal_client.upload_file(reference_image_path)

    result = fal_client.subscribe(
        "fal-ai/kling-video/v2/master/image-to-video",
        arguments={
            "prompt": prompt,
            "image_url": image_url,
            "duration": duration,
            "aspect_ratio": "9:16",
        },
    )

    video_url = result.get("video", {}).get("url", "")
    if video_url:
        _download_file(video_url, output_path)

    return output_path


def musetalk_lip_sync(
    video_path: Path,
    audio_path: Path,
    output_path: Path,
) -> Path:
    """Apply lip sync to video using MuseTalk via fal.ai."""
    get_api_key("FAL_KEY")
    ensure_dirs(output_path.parent)

    video_url = fal_client.upload_file(video_path)
    audio_url = fal_client.upload_file(audio_path)

    result = fal_client.subscribe(
        "fal-ai/musetalk",
        arguments={
            "video_url": video_url,
            "audio_url": audio_url,
        },
    )

    result_url = result.get("video", {}).get("url", "")
    if result_url:
        _download_file(result_url, output_path)

    return output_path


# --- Kling 2.6 Motion Control (fal.ai) ---

def kling26_motion_control(
    reference_image_path: Path,
    source_video_path: Path,
    prompt: str,
    output_path: Path,
) -> Path:
    """Generate video using Kling 2.6 Motion Control via fal.ai.

    Transfers motion from source_video to a new character defined by reference_image.
    character_orientation="image" uses the image's aspect ratio (use 9:16 reference).
    """
    get_api_key("FAL_KEY")
    ensure_dirs(output_path.parent)

    image_url = fal_client.upload_file(reference_image_path)
    video_url = fal_client.upload_file(source_video_path)

    result = fal_client.subscribe(
        "fal-ai/kling-video/v2.6/standard/motion-control",
        arguments={
            "prompt": prompt,
            "image_url": image_url,
            "video_url": video_url,
            "character_orientation": "image",
        },
    )

    result_url = result.get("video", {}).get("url", "")
    if result_url:
        _download_file(result_url, output_path)

    return output_path


# --- Sync Lipsync v2 (fal.ai) ---

def sync_lipsync(
    video_path: Path,
    audio_path: Path,
    output_path: Path,
) -> Path:
    """Apply lip sync using Sync Lipsync v2 via fal.ai.

    Best quality across all character styles (photorealistic, anime, 3D).
    """
    get_api_key("FAL_KEY")
    ensure_dirs(output_path.parent)

    video_url = fal_client.upload_file(video_path)
    audio_url = fal_client.upload_file(audio_path)

    result = fal_client.subscribe(
        "fal-ai/sync-lipsync/v2",
        arguments={
            "video_url": video_url,
            "audio_url": audio_url,
        },
    )

    result_url = result.get("video", {}).get("url", "")
    if result_url:
        _download_file(result_url, output_path)

    return output_path


# --- VEO 3 (fal.ai) ---

def veo3_generate(
    reference_image_path: Path,
    prompt: str,
    output_path: Path,
) -> Path:
    """Generate video using VEO 3 via fal.ai."""
    get_api_key("FAL_KEY")
    ensure_dirs(output_path.parent)

    image_url = fal_client.upload_file(reference_image_path)

    result = fal_client.subscribe(
        "fal-ai/veo3",
        arguments={
            "prompt": prompt,
            "image_url": image_url,
            "aspect_ratio": "9:16",
        },
    )

    video_url = result.get("video", {}).get("url", "")
    if video_url:
        _download_file(video_url, output_path)

    return output_path


# --- Helpers ---

def _is_valid_video(path: Path) -> bool:
    """Check if a video file exists, has size > 0, and has duration > 0."""
    if not path.exists() or path.stat().st_size == 0:
        return False
    try:
        cmd = [
            "ffprobe", "-v", "quiet", "-print_format", "json",
            "-show_format", str(path)
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        probe = json.loads(result.stdout)
        duration = float(probe.get("format", {}).get("duration", 0))
        return duration > 0
    except Exception:
        return False


def _build_enhanced_prompt(base_prompt: str, chunk_analysis: dict | None = None) -> str:
    """Enhance video generation prompt with chunk analysis data."""
    if not chunk_analysis:
        return base_prompt

    parts = [base_prompt] if base_prompt else []

    expression = chunk_analysis.get("expression", "")
    if expression:
        parts.append(f"Expression: {expression}")

    gesture = chunk_analysis.get("gesture", "")
    if gesture:
        parts.append(f"Gesture: {gesture}")

    camera = chunk_analysis.get("camera_movement", "")
    if camera:
        parts.append(f"Camera: {camera}")

    return ". ".join(parts)


# --- Dispatcher ---

def generate_chunk_video(
    model: str,
    face_image_path: Path,
    audio_path: Path,
    output_path: Path,
    prompt: str = "",
    background_path: Path | None = None,
    avatar_id: str | None = None,
    chunk_analysis: dict | None = None,
    source_video_path: Path | None = None,
) -> Path:
    """Dispatch video generation to the selected model.

    model: "heygen", "kling_avatar", "kling3", "kling26", "veo3"
    Skips generation if output already exists and is valid.
    For kling26: uses reference image (already has background baked in) + source video for motion.
    For other non-heygen models: composites face onto background if provided.
    """
    # Skip if already generated
    if _is_valid_video(output_path):
        print(f"  {output_path.name}: already exists, skipping")
        return output_path

    # kling26 uses reference image directly (background already baked in)
    # Other non-heygen models need face composited onto background
    if model not in ("heygen", "kling26") and background_path and background_path.exists():
        composited = composite_face_on_background(face_image_path, background_path)
        face_image_path = composited

    # Enhance prompt with chunk analysis for models that use prompts
    if model in ("kling3", "kling26", "veo3"):
        prompt = _build_enhanced_prompt(prompt, chunk_analysis)

    if model == "heygen":
        if not avatar_id:
            raise ValueError("HeyGen requires avatar_id. Create avatar first.")
        return heygen_generate_video(avatar_id, audio_path, output_path, background_path)

    elif model == "kling_avatar":
        return kling_avatar_generate(face_image_path, audio_path, output_path)

    elif model == "kling3":
        # Generate video then apply lip sync with MuseTalk
        raw_video = output_path.with_suffix(".raw.mp4")
        if not _is_valid_video(raw_video):
            kling_video_generate(face_image_path, prompt, raw_video)
        return musetalk_lip_sync(raw_video, audio_path, output_path)

    elif model == "kling26":
        # Kling 2.6 Motion Control → Sync Lipsync v2
        if not source_video_path:
            raise ValueError("kling26 requires source_video_path for motion transfer.")
        raw_video = output_path.with_suffix(".raw.mp4")
        if not _is_valid_video(raw_video):
            kling26_motion_control(face_image_path, source_video_path, prompt, raw_video)
        return sync_lipsync(raw_video, audio_path, output_path)

    elif model == "veo3":
        return veo3_generate(face_image_path, prompt, output_path)

    else:
        raise ValueError(f"Unknown model: {model}")


def _download_file(url: str, path: Path) -> None:
    """Download file from URL."""
    response = requests.get(url, timeout=300)
    response.raise_for_status()
    with open(path, "wb") as f:
        f.write(response.content)
