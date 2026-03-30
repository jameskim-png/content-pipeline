"""Motion reference library management.

Pre-generated or imported video clips organized by emotion, used as motion sources
for Kling 2.6 Motion Control video generation.

Supports two sourcing methods:
1. Stock video import (recommended) — curated clips from Pixabay/Pexels/Coverr
2. AI generation (fallback) — Kling image-to-video
"""

import re
import random
import shutil
import subprocess
from pathlib import Path

import fal_client

from .config import MOTION_REFS_DIR, EMOTION_CATEGORIES, get_api_key, ensure_dirs
from .utils import save_json, load_json


EMOTION_PROMPTS = {
    "neutral": {
        "description": "Calm, composed default state with minimal movement",
        "prompt": "Person sitting still, looking at camera, neutral expression, slight natural breathing movement, calm and composed, chest-up close shot",
    },
    "calm": {
        "description": "Relaxed, peaceful, slow gentle movements",
        "prompt": "Person speaking calmly, relaxed posture, slow gentle head movements, peaceful expression, soft gestures, chest-up close shot",
    },
    "excited": {
        "description": "Energetic, animated, larger movements",
        "prompt": "Person speaking excitedly, animated gestures, energetic head movements, wide eyes, expressive body language, enthusiastic, chest-up close shot",
    },
    "thinking": {
        "description": "Contemplative, looking up/away, touching chin",
        "prompt": "Person thinking deeply, looking slightly up, contemplative expression, subtle head tilt, hand near chin, thoughtful, chest-up close shot",
    },
    "happy": {
        "description": "Smiling, bright, cheerful movements",
        "prompt": "Person smiling brightly, cheerful expression, gentle nodding, warm and friendly body language, happy mood, chest-up close shot",
    },
    "sad": {
        "description": "Downcast, slower movements, sighing",
        "prompt": "Person looking slightly down, melancholy expression, slow movements, subtle shoulder drop, reflective mood, chest-up close shot",
    },
    "surprised": {
        "description": "Eyes wide, head back slightly, quick reaction",
        "prompt": "Person looking surprised, eyes widening, slight backward head movement, raised eyebrows, quick expressive reaction, chest-up close shot",
    },
    "explaining": {
        "description": "Gesturing while talking, steady eye contact",
        "prompt": "Person explaining something, hand gestures while talking, steady eye contact, confident posture, clear articulation movements, chest-up close shot",
    },
    "emphatic": {
        "description": "Strong emphasis, nodding, decisive gestures",
        "prompt": "Person speaking emphatically, strong nodding, decisive hand gestures, firm expression, passionate delivery, chest-up close shot",
    },
    "playful": {
        "description": "Mischievous, head tilts, light bounce",
        "prompt": "Person being playful, mischievous smile, playful head tilts, light bouncy movements, teasing expression, fun energy, chest-up close shot",
    },
}


def load_motion_index() -> dict:
    """Load motion reference library index from disk."""
    index_path = MOTION_REFS_DIR / "metadata.json"
    if not index_path.exists():
        return {"emotions": {}, "total_clips": 0}
    return load_json(index_path)


def save_motion_index(index: dict) -> Path:
    """Save motion reference library index."""
    ensure_dirs(MOTION_REFS_DIR)
    path = MOTION_REFS_DIR / "metadata.json"
    save_json(index, path)
    return path


def select_motion_reference(emotion: str, index: dict | None = None) -> Path | None:
    """Select a motion reference clip for a given emotion.

    Fallback chain: emotion -> neutral -> any available clip.
    Returns None if library is empty.
    """
    if index is None:
        index = load_motion_index()

    emotions = index.get("emotions", {})

    # Try exact emotion match
    if emotion in emotions and emotions[emotion]:
        clips = emotions[emotion]
        clip = random.choice(clips)
        path = MOTION_REFS_DIR / emotion / clip
        if path.exists():
            return path

    # Fallback: neutral
    if emotion != "neutral" and "neutral" in emotions and emotions["neutral"]:
        clips = emotions["neutral"]
        clip = random.choice(clips)
        path = MOTION_REFS_DIR / "neutral" / clip
        if path.exists():
            return path

    # Fallback: any available clip
    for emo, clips in emotions.items():
        for clip in clips:
            path = MOTION_REFS_DIR / emo / clip
            if path.exists():
                return path

    return None


def select_motion_references_for_script(
    script_chunks: list[dict],
    index: dict | None = None,
    persona_spec: dict | None = None,
) -> list[dict]:
    """Select motion references for all script chunks.

    Avoids consecutive use of the same clip.
    When persona_spec is provided, adjusts emotion intensity based on character vibe.
    Returns list of dicts with chunk_id, emotion, effective_emotion, motion_ref_path.
    """
    if index is None:
        index = load_motion_index()

    emotions = index.get("emotions", {})
    emotion_map = _build_persona_emotion_map(persona_spec) if persona_spec else {}
    results = []
    last_clip_path = None

    for chunk in script_chunks:
        original_emotion = chunk.get("emotion", "neutral")
        chunk_id = chunk.get("chunk_id", "")

        # Apply persona-based emotion remapping
        effective_emotion = emotion_map.get(original_emotion, original_emotion)

        # Get candidates for effective emotion
        candidates = _get_clip_paths(effective_emotion, emotions)

        # Fallback to original emotion if remapped one has no clips
        if not candidates and effective_emotion != original_emotion:
            candidates = _get_clip_paths(original_emotion, emotions)

        # Fallback to neutral
        if not candidates and effective_emotion != "neutral":
            candidates = _get_clip_paths("neutral", emotions)

        # Fallback to any
        if not candidates:
            for emo in emotions:
                candidates = _get_clip_paths(emo, emotions)
                if candidates:
                    break

        if not candidates:
            results.append({
                "chunk_id": chunk_id,
                "emotion": original_emotion,
                "effective_emotion": effective_emotion,
                "motion_ref_path": None,
            })
            continue

        # Avoid consecutive same clip
        if len(candidates) > 1 and last_clip_path in candidates:
            candidates = [c for c in candidates if c != last_clip_path]

        selected = random.choice(candidates)
        last_clip_path = selected

        results.append({
            "chunk_id": chunk_id,
            "emotion": original_emotion,
            "effective_emotion": effective_emotion,
            "motion_ref_path": str(selected),
        })

    return results


# Emotion intensity tiers: high-energy → low-energy
_EMOTION_INTENSITY = {
    "excited": 5,
    "emphatic": 4,
    "surprised": 4,
    "playful": 3,
    "happy": 3,
    "explaining": 2,
    "thinking": 2,
    "calm": 1,
    "neutral": 0,
    "sad": 1,
}

# Downgrade map: high-energy emotion → softer alternative
_DOWNGRADE_MAP = {
    "excited": "happy",
    "emphatic": "explaining",
    "surprised": "thinking",
    "playful": "calm",
    "happy": "calm",
    "explaining": "calm",
}


def _build_persona_emotion_map(persona_spec: dict) -> dict:
    """Build emotion remapping based on persona's vibe and voice_tone.

    Characters with restrained/minimal vibes get their high-energy emotions
    downgraded to softer alternatives.
    Returns dict mapping original_emotion -> effective_emotion.
    """
    vibe = (persona_spec.get("vibe", "") or "").lower()
    voice_tone = (persona_spec.get("voice_tone", "") or "").lower()
    combined = f"{vibe} {voice_tone}"

    # Detect restrained personality keywords
    restrained_keywords = [
        "무표정", "미니멀", "차가운", "냉정", "감정 없",
        "로봇", "ai", "일정한", "절제", "담담",
        "minimal", "cold", "stoic", "robotic", "monotone",
    ]
    is_restrained = any(kw in combined for kw in restrained_keywords)

    if not is_restrained:
        return {}  # No remapping for expressive characters

    # Remap high-energy emotions down by one tier
    remap = {}
    for emotion, intensity in _EMOTION_INTENSITY.items():
        if intensity >= 3:  # Only downgrade high-energy emotions
            remap[emotion] = _DOWNGRADE_MAP.get(emotion, "calm")

    return remap


def _get_clip_paths(emotion: str, emotions: dict) -> list[Path]:
    """Get all existing clip paths for an emotion."""
    clips = emotions.get(emotion, [])
    paths = []
    for clip in clips:
        path = MOTION_REFS_DIR / emotion / clip
        if path.exists():
            paths.append(path)
    return paths


def validate_motion_clip(path: str | Path) -> dict:
    """Validate a video file for use as a motion reference clip.

    Checks duration (3-15s), video stream existence, codec, and resolution.
    Returns dict with valid status, metadata, and any issues found.
    """
    path = Path(path)
    issues = []

    if not path.exists():
        return {"valid": False, "duration": 0, "width": 0, "height": 0, "issues": [f"File not found: {path}"]}

    if path.suffix.lower() not in (".mp4", ".mov", ".webm", ".avi"):
        issues.append(f"Unsupported format: {path.suffix} (use .mp4, .mov, .webm, .avi)")

    try:
        import json as _json
        cmd = [
            "ffprobe", "-v", "quiet", "-print_format", "json",
            "-show_format", "-show_streams", str(path),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        probe = _json.loads(result.stdout)
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        return {"valid": False, "duration": 0, "width": 0, "height": 0, "issues": [f"ffprobe failed: {e}"]}

    # Find video stream
    video_stream = next(
        (s for s in probe.get("streams", []) if s.get("codec_type") == "video"), None
    )
    if not video_stream:
        issues.append("No video stream found")
        return {"valid": False, "duration": 0, "width": 0, "height": 0, "issues": issues}

    duration = float(probe.get("format", {}).get("duration", 0))
    width = int(video_stream.get("width", 0))
    height = int(video_stream.get("height", 0))

    if duration < 3:
        issues.append(f"Duration {duration:.1f}s < 3s minimum")
    if duration > 15:
        issues.append(f"Duration {duration:.1f}s > 15s maximum")
    if width < 240:
        issues.append(f"Width {width}px < 240px minimum")

    return {
        "valid": len(issues) == 0,
        "duration": round(duration, 2),
        "width": width,
        "height": height,
        "issues": issues,
    }


def import_motion_clip(
    emotion: str,
    source_path: str | Path,
    clip_index: int | None = None,
) -> Path:
    """Import a stock video clip as a motion reference for a given emotion.

    Validates the clip, copies it to the library, and updates metadata.
    Returns the destination path.
    """
    source_path = Path(source_path)

    if emotion not in EMOTION_CATEGORIES:
        raise ValueError(f"Unknown emotion: {emotion}. Valid: {', '.join(EMOTION_CATEGORIES)}")

    # Validate
    validation = validate_motion_clip(source_path)
    if not validation["valid"]:
        raise ValueError(f"Invalid clip: {'; '.join(validation['issues'])}")

    # Determine clip index
    emotion_dir = MOTION_REFS_DIR / emotion
    ensure_dirs(emotion_dir)

    if clip_index is None:
        existing = sorted(emotion_dir.glob(f"{emotion}_*.mp4"))
        if existing:
            # Parse highest existing index
            last = existing[-1].stem  # e.g. "happy_003"
            match = re.search(r"_(\d+)$", last)
            clip_index = int(match.group(1)) + 1 if match else len(existing) + 1
        else:
            clip_index = 1

    dest_path = emotion_dir / f"{emotion}_{clip_index:03d}.mp4"
    shutil.copy2(source_path, dest_path)

    # Update index
    index = load_motion_index()
    if emotion not in index["emotions"]:
        index["emotions"][emotion] = []
    filename = dest_path.name
    if filename not in index["emotions"][emotion]:
        index["emotions"][emotion].append(filename)
    index["total_clips"] = sum(len(v) for v in index["emotions"].values())
    save_motion_index(index)

    return dest_path


def import_from_folder(folder_path: str | Path) -> dict:
    """Batch-import motion clips from a folder.

    Recognizes filenames like:
    - {emotion}_001.mp4, {emotion}_002.mp4 (numbered)
    - {emotion}.mp4 (single clip)

    Returns report with imported, skipped, and errors lists.
    """
    folder = Path(folder_path)
    if not folder.is_dir():
        raise ValueError(f"Not a directory: {folder}")

    imported = []
    skipped = []
    errors = []

    video_files = sorted(
        f for f in folder.iterdir()
        if f.suffix.lower() in (".mp4", ".mov", ".webm", ".avi")
    )

    for vf in video_files:
        # Parse emotion from filename
        stem = vf.stem.lower()
        matched_emotion = None

        for emotion in EMOTION_CATEGORIES:
            if stem == emotion or stem.startswith(f"{emotion}_"):
                matched_emotion = emotion
                break

        if not matched_emotion:
            skipped.append({"file": vf.name, "reason": f"Cannot parse emotion from filename '{vf.stem}'"})
            continue

        # Validate
        validation = validate_motion_clip(vf)
        if not validation["valid"]:
            errors.append({"file": vf.name, "emotion": matched_emotion, "issues": validation["issues"]})
            continue

        # Import
        try:
            dest = import_motion_clip(matched_emotion, vf)
            imported.append({
                "file": vf.name,
                "emotion": matched_emotion,
                "dest": str(dest),
                "duration": validation["duration"],
            })
        except Exception as e:
            errors.append({"file": vf.name, "emotion": matched_emotion, "issues": [str(e)]})

    return {"imported": imported, "skipped": skipped, "errors": errors}


def preview_library_status() -> str:
    """Return a formatted table of the motion library status."""
    status = list_motion_library_status()
    emotions = status["emotions"]

    lines = [
        f"Motion Library: {status['library_path']}",
        f"Total clips: {status['total_clips']}",
        "",
        f"{'Emotion':<12} {'Clips':>5}  Files",
        f"{'-'*12} {'-'*5}  {'-'*30}",
    ]

    for emotion in EMOTION_CATEGORIES:
        info = emotions.get(emotion, {"count": 0, "clips": []})
        count = info["count"]
        clips_str = ", ".join(info["clips"]) if info["clips"] else "(empty)"
        marker = "  " if count > 0 else "X "
        lines.append(f"{marker}{emotion:<12} {count:>3}    {clips_str}")

    missing = [e for e in EMOTION_CATEGORIES if emotions.get(e, {}).get("count", 0) == 0]
    if missing:
        lines.append("")
        lines.append(f"Missing: {', '.join(missing)}")

    return "\n".join(lines)


def generate_motion_reference(
    emotion: str,
    reference_image_path: Path,
    clip_index: int = 1,
) -> Path:
    """Generate a single motion reference clip using Kling 2.6 image-to-video.

    This creates the motion SOURCE clip (not the final video).
    AI-generated fallback when stock clips are not available.
    """
    get_api_key("FAL_KEY")

    if emotion not in EMOTION_PROMPTS:
        raise ValueError(f"Unknown emotion: {emotion}. Valid: {', '.join(EMOTION_CATEGORIES)}")

    emotion_dir = MOTION_REFS_DIR / emotion
    ensure_dirs(emotion_dir)

    prompt = EMOTION_PROMPTS[emotion]["prompt"]
    output_path = emotion_dir / f"{emotion}_{clip_index:03d}.mp4"

    image_url = fal_client.upload_file(reference_image_path)

    result = fal_client.subscribe(
        "fal-ai/kling-video/v2.6/master/image-to-video",
        arguments={
            "prompt": prompt,
            "image_url": image_url,
            "duration": "10",
            "aspect_ratio": "9:16",
        },
    )

    video_url = result.get("video", {}).get("url", "")
    if video_url:
        _download_file(video_url, output_path)

    # Update index
    index = load_motion_index()
    if emotion not in index["emotions"]:
        index["emotions"][emotion] = []
    filename = output_path.name
    if filename not in index["emotions"][emotion]:
        index["emotions"][emotion].append(filename)
    index["total_clips"] = sum(len(v) for v in index["emotions"].values())
    save_motion_index(index)

    return output_path


def generate_full_motion_library(
    reference_image_path: Path,
    clips_per_emotion: int = 2,
    emotions: list[str] | None = None,
) -> dict:
    """Generate complete motion reference library.

    One-time setup: generates clips for each emotion.
    Default: 10 emotions x 2 clips = 20 clips, ~$3.

    Returns summary dict with generated clip paths.
    """
    if emotions is None:
        emotions = list(EMOTION_CATEGORIES)

    results = {}
    total = len(emotions) * clips_per_emotion
    generated = 0

    for emotion in emotions:
        results[emotion] = []
        for i in range(1, clips_per_emotion + 1):
            generated += 1
            print(f"  [{generated}/{total}] Generating {emotion} clip {i}...")
            try:
                path = generate_motion_reference(emotion, reference_image_path, clip_index=i)
                results[emotion].append(str(path))
                print(f"    -> {path.name}")
            except Exception as e:
                print(f"    ERROR: {e}")
                results[emotion].append(f"ERROR: {e}")

    return results


def list_motion_library_status() -> dict:
    """List current motion library status.

    Returns dict with per-emotion clip counts and total.
    """
    index = load_motion_index()
    emotions = index.get("emotions", {})

    status = {}
    total_existing = 0

    for emotion in EMOTION_CATEGORIES:
        clips = emotions.get(emotion, [])
        existing = [c for c in clips if (MOTION_REFS_DIR / emotion / c).exists()]
        status[emotion] = {
            "count": len(existing),
            "clips": existing,
        }
        total_existing += len(existing)

    return {
        "emotions": status,
        "total_clips": total_existing,
        "library_path": str(MOTION_REFS_DIR),
        "is_empty": total_existing == 0,
    }


def _download_file(url: str, path: Path) -> None:
    """Download file from URL."""
    import requests

    response = requests.get(url, timeout=300)
    response.raise_for_status()
    with open(path, "wb") as f:
        f.write(response.content)
