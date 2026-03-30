"""Video generation using HeyGen, Kling, or VEO via fal.ai."""

import json
import subprocess
import time
from pathlib import Path

import requests
import fal_client

from .config import get_api_key, ensure_dirs
from .utils import save_json, get_audio_duration
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


# --- Grok Imagine Video (fal.ai) ---

def grok_image_to_video(
    reference_image_path: Path,
    prompt: str,
    output_path: Path,
    duration: int = 6,
    resolution: str = "720p",
) -> Path:
    """Generate video using Grok Imagine Video (image-to-video) via fal.ai.

    duration: 1-15 seconds.
    resolution: "720p" or "1080p".
    """
    get_api_key("FAL_KEY")
    ensure_dirs(output_path.parent)

    image_url = fal_client.upload_file(reference_image_path)

    result = fal_client.subscribe(
        "xai/grok-imagine-video/image-to-video",
        arguments={
            "image_url": image_url,
            "prompt": prompt,
            "duration": duration,
            "resolution": resolution,
        },
    )

    video_url = result.get("video", {}).get("url", "")
    if not video_url:
        raise RuntimeError(
            f"Grok returned no video URL. Prompt: {prompt[:100]}"
        )

    _download_file(video_url, output_path)
    return output_path


def _build_grok_prompt(
    chunk_text: str,
    persona_spec: dict | None = None,
    emotion: str = "neutral",
    chunk_index: int = 0,
) -> str:
    """Build video generation prompt for Grok Imagine Video.

    Korean prompt: character appearance + framing + mood + emotion cue + speech text.
    Stays within Grok's 4096-char prompt limit.

    chunk_index: alternates framing between close-up (even) and medium shot (odd)
    for natural "punch-in cut" transitions between chunks.
    """
    parts = []

    # Character appearance from persona_spec
    if persona_spec:
        appearance = []
        if persona_spec.get("gender"):
            appearance.append(persona_spec["gender"])
        if persona_spec.get("age_range"):
            appearance.append(persona_spec["age_range"])
        if persona_spec.get("ethnicity"):
            appearance.append(persona_spec["ethnicity"])
        if persona_spec.get("visual_traits"):
            appearance.append(persona_spec["visual_traits"])
        if persona_spec.get("hair"):
            appearance.append(f"Hair: {persona_spec['hair']}")
        if persona_spec.get("clothing"):
            appearance.append(f"Wearing: {persona_spec['clothing']}")
        if appearance:
            parts.append(f"Character: {', '.join(appearance)}")

    # Alternating framing: close-up (even chunks) vs medium shot (odd chunks)
    if chunk_index % 2 == 0:
        framing = "Close-up upper body shot, shoulders and head visible, talking to camera"
    else:
        framing = "Medium shot, waist-up framing, talking to camera, more background visible"
    parts.append(f"{framing}, 9:16 vertical framing, static camera, fixed framing, no zoom, no pan, no camera movement")

    # Mood from vibe
    if persona_spec:
        vibe = persona_spec.get("vibe", "")
        if vibe:
            vibe_en = _vibe_to_english(vibe)
            if vibe_en:
                parts.append(f"Mood: {vibe_en}")

    # Emotion cue — use shared delivery inference (respects persona vibe)
    vibe = persona_spec.get("vibe", "") if persona_spec else ""
    cue = _infer_delivery_from_text(chunk_text, emotion, vibe)
    parts.append(cue)

    # Speech content as context
    if chunk_text:
        # Truncate to keep within prompt limit
        text_hint = chunk_text[:200]
        parts.append(f'Speaking: "{text_hint}"')

    prompt = ", ".join(parts)
    # Enforce Grok 4096-char limit
    if len(prompt) > 4000:
        prompt = prompt[:4000]
    return prompt


# --- Helpers ---

def _is_valid_video(path: Path) -> bool:
    """Check if a video file exists, has size > 0, and has duration > 0."""
    if not path.exists() or path.stat().st_size == 0:
        return False
    try:
        return _get_video_duration(path) > 0
    except Exception:
        return False


def _get_video_duration(path: Path) -> float:
    """Get video duration in seconds via ffprobe."""
    cmd = [
        "ffprobe", "-v", "quiet", "-print_format", "json",
        "-show_format", str(path)
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    probe = json.loads(result.stdout)
    return float(probe.get("format", {}).get("duration", 0))


def _is_video_fresh(video_path: Path, audio_path: Path, tolerance: float = 0.5) -> bool:
    """Check if cached video is valid AND matches the current audio.

    Detects stale videos from previous runs by checking:
    1. Video is valid (exists, has duration)
    2. Video was created after the audio (mtime)
    3. Video duration roughly matches audio duration
    """
    if not _is_valid_video(video_path):
        return False
    if not audio_path.exists():
        return False
    try:
        # mtime check: video should be newer than audio
        if video_path.stat().st_mtime < audio_path.stat().st_mtime:
            return False
        # Duration match check
        video_dur = _get_video_duration(video_path)
        audio_dur = get_audio_duration(audio_path)
        return abs(video_dur - audio_dur) <= tolerance
    except Exception:
        return False


def _is_raw_video_fresh(raw_video_path: Path, audio_path: Path) -> bool:
    """Check if a raw (pre-lipsync) video is valid and newer than audio.

    Raw videos don't need duration matching (lipsync adjusts timing),
    but must be newer than the audio to avoid stale reuse.
    """
    if not _is_valid_video(raw_video_path):
        return False
    if not audio_path.exists():
        return False
    return raw_video_path.stat().st_mtime >= audio_path.stat().st_mtime


def _build_enhanced_prompt(
    base_prompt: str,
    chunk_analysis: dict | None = None,
    persona_spec: dict | None = None,
    chunk_text: str | None = None,
    emotion: str | None = None,
) -> str:
    """Enhance video generation prompt with persona traits, script content, and chunk analysis.

    Priority: persona_spec + chunk_text > chunk_analysis > base_prompt fallback.
    """
    # If persona_spec is provided, build a character-aware prompt
    if persona_spec:
        parts = []

        # Character description — always in English for best Kling results
        parts.append("Person talking to camera, chest-up close shot, 9:16 vertical framing")

        # Mood from vibe (translated to English-friendly descriptors)
        vibe = persona_spec.get("vibe", "")
        if vibe:
            vibe_en = _vibe_to_english(vibe)
            if vibe_en:
                parts.append(vibe_en)

        # Script content → action/delivery cue
        if chunk_text:
            delivery = _infer_delivery_from_text(chunk_text, emotion or "neutral", vibe)
            parts.append(delivery)

        return ", ".join(parts)

    # Fallback: original chunk_analysis logic
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


def _vibe_to_english(vibe: str) -> str:
    """Convert Korean vibe keywords to English descriptors for Kling prompts."""
    # Ordered longest-first to avoid substring conflicts (미니멀리즘 before 미니멀)
    translations = [
        ("미니멀리즘", "minimalist"),
        ("무표정", "expressionless"),
        ("차가운 블루 톤", "cold blue-toned lighting"),
        ("차가운", "cold"),
        ("블루 톤", "blue-toned lighting"),
        ("냉정", "stoic"),
        ("감성", "emotional"),
        ("귀여운", "cute"),
        ("현실적", "realistic"),
        ("지나친 진지함", "overly serious"),
        ("광기", "manic intensity"),
        ("기발함", "quirky"),
        ("기괴한", "bizarre"),
        ("비비드", "vivid"),
        ("Y2K", "Y2K retro"),
    ]
    parts = []
    remaining = vibe
    for ko, en in translations:
        if ko in remaining:
            parts.append(en)
            remaining = remaining.replace(ko, "", 1)
    return ", ".join(parts) if parts else ""


def _infer_delivery_from_text(text: str, emotion: str, vibe: str) -> str:
    """Infer a short video delivery cue from script text + emotion + character vibe.

    Returns a concise English phrase describing how the character should deliver.
    """
    vibe_lower = vibe.lower() if vibe else ""

    # Detect restrained character
    is_restrained = any(kw in vibe_lower for kw in [
        "무표정", "미니멀", "차가운", "냉정", "로봇", "ai", "감정 없",
    ])

    # Text content analysis (Korean) — prioritize most specific cue
    ends_with_question = text.rstrip().endswith("?")
    has_hesitation = "어..." in text or "..." in text or "음..." in text
    has_strong_command = any(kw in text for kw in ["켜", "뒤집어", "하면 안 돼", "절대"])
    is_listing = ("분." in text or "초." in text) and text.count(".") >= 3
    has_reaction = any(kw in text for kw in ["무섭다", "화나네", "맞는 말", "너무한"])
    is_short = len(text) < 30
    is_cta = any(kw in text for kw in ["댓글", "링크", "구독", "좋아요"])

    if is_restrained:
        # Restrained character: always controlled, but with subtle variations per content
        if has_hesitation:
            return "brief composed pause, slight eye shift, controlled stillness"
        elif has_strong_command:
            return "controlled intensity, slight lean forward, unwavering gaze"
        elif is_listing:
            return "methodical pacing, minimal gestures, steady measured composure"
        elif has_reaction and is_short:
            return "micro-expression shift, brief eye contact break, quick recovery to neutral"
        elif is_cta:
            return "direct steady gaze, slight forward lean, purposeful delivery"
        elif ends_with_question:
            return "subtle head tilt, piercing gaze, deliberate pause"
        else:
            return "calm measured delivery, minimal expression, slight natural movement"
    else:
        # Expressive character: emotion-driven delivery
        delivery_map = {
            "excited": "animated gestures, wide eyes, energetic movement",
            "emphatic": "strong nodding, decisive gestures, firm expression",
            "surprised": "eyes widening, slight backward movement, raised eyebrows",
            "thinking": "looking slightly up, contemplative pause, hand near face",
            "happy": "warm smile, gentle nodding, bright expression",
            "calm": "relaxed posture, slow gentle movements, steady gaze",
            "neutral": "composed, minimal movement, steady eye contact",
            "sad": "looking slightly down, slow movements, reflective mood",
            "playful": "mischievous expression, head tilts, light movement",
            "explaining": "hand gestures while talking, steady eye contact",
        }
        return delivery_map.get(emotion, "natural movement, talking to camera")


# --- Narration Reel: Scene Video ---

def generate_scene_video(
    image_path: Path,
    prompt: str,
    output_path: Path,
    duration: int = 5,
    resolution: str = "720p",
) -> Path:
    """Generate an animated video clip from a scene image.

    Uses Grok Imagine Video directly (no lip sync).
    For Narration Reel pipeline where each scene is a separate image.

    Args:
        image_path: Path to the scene image (from Flux).
        prompt: Animation prompt (camera movement, motion description).
        output_path: Where to save the generated clip.
        duration: Clip duration in seconds (1-15).
        resolution: "720p" or "1080p".

    Returns:
        Path to the generated video clip (silent).
    """
    if _is_valid_video(output_path):
        print(f"  {output_path.name}: already exists, skipping")
        return output_path

    return grok_image_to_video(
        reference_image_path=image_path,
        prompt=prompt,
        output_path=output_path,
        duration=duration,
        resolution=resolution,
    )


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
    persona_spec: dict | None = None,
    chunk_text: str | None = None,
    emotion: str | None = None,
    chunk_index: int = 0,
) -> Path:
    """Dispatch video generation to the selected model.

    model: "heygen", "kling_avatar", "kling3", "kling26", "grok", "veo3"
    Skips generation if output already exists and is valid.
    chunk_index: used for alternating framing (close-up/medium shot).
    For kling26: uses reference image (already has background baked in) + source video for motion.
    For other non-heygen models: composites face onto background if provided.
    persona_spec: character traits for dynamic prompt generation.
    chunk_text: script text for context-aware motion prompts.
    emotion: emotion tag for the chunk.
    """
    # Skip if already generated and fresh (matches current audio)
    if _is_video_fresh(output_path, audio_path):
        print(f"  {output_path.name}: already exists and fresh, skipping")
        return output_path
    elif _is_valid_video(output_path):
        print(f"  {output_path.name}: stale (duration/mtime mismatch), regenerating")
        output_path.unlink(missing_ok=True)

    # kling26/grok use reference image directly (background already baked in)
    # Other non-heygen models need face composited onto background
    if model not in ("heygen", "kling26", "grok") and background_path and background_path.exists():
        composited = composite_face_on_background(face_image_path, background_path)
        face_image_path = composited

    # Enhance prompt: persona_spec + chunk_text take priority over chunk_analysis
    if model in ("kling3", "kling26", "veo3"):
        prompt = _build_enhanced_prompt(
            prompt, chunk_analysis,
            persona_spec=persona_spec,
            chunk_text=chunk_text,
            emotion=emotion,
        )

    if model == "heygen":
        if not avatar_id:
            raise ValueError("HeyGen requires avatar_id. Create avatar first.")
        return heygen_generate_video(avatar_id, audio_path, output_path, background_path)

    elif model == "kling_avatar":
        return kling_avatar_generate(face_image_path, audio_path, output_path)

    elif model == "kling3":
        # Generate video then apply lip sync with MuseTalk
        raw_video = output_path.with_suffix(".raw.mp4")
        if not _is_raw_video_fresh(raw_video, audio_path):
            raw_video.unlink(missing_ok=True)
            kling_video_generate(face_image_path, prompt, raw_video)
        return musetalk_lip_sync(raw_video, audio_path, output_path)

    elif model == "kling26":
        # Kling 2.6 Motion Control → Sync Lipsync v2
        if not source_video_path:
            raise ValueError("kling26 requires source_video_path for motion transfer.")
        raw_video = output_path.with_suffix(".raw.mp4")
        if not _is_raw_video_fresh(raw_video, audio_path):
            raw_video.unlink(missing_ok=True)
            kling26_motion_control(face_image_path, source_video_path, prompt, raw_video)
        return sync_lipsync(raw_video, audio_path, output_path)

    elif model == "grok":
        # Grok Imagine Video → Sync Lipsync v2
        grok_prompt = _build_grok_prompt(chunk_text or "", persona_spec, emotion or "neutral", chunk_index=chunk_index)
        grok_duration = max(1, min(15, int(get_audio_duration(audio_path)) + 1))
        raw_video = output_path.with_suffix(".raw.mp4")
        if not _is_raw_video_fresh(raw_video, audio_path):
            raw_video.unlink(missing_ok=True)
            grok_image_to_video(face_image_path, grok_prompt, raw_video, duration=grok_duration)
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
