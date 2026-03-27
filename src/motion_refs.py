"""Motion reference library management.

Pre-generated video clips organized by emotion, used as motion sources
for Kling 2.6 Motion Control video generation.
"""

import random
from pathlib import Path

import fal_client

from .config import MOTION_REFS_DIR, EMOTION_CATEGORIES, get_api_key, ensure_dirs
from .utils import save_json, load_json


EMOTION_PROMPTS = {
    "neutral": {
        "description": "Calm, composed default state with minimal movement",
        "prompt": "Person sitting still, looking at camera, neutral expression, slight natural breathing movement, calm and composed, upper body portrait",
    },
    "calm": {
        "description": "Relaxed, peaceful, slow gentle movements",
        "prompt": "Person speaking calmly, relaxed posture, slow gentle head movements, peaceful expression, soft gestures, upper body portrait",
    },
    "excited": {
        "description": "Energetic, animated, larger movements",
        "prompt": "Person speaking excitedly, animated gestures, energetic head movements, wide eyes, expressive body language, enthusiastic, upper body portrait",
    },
    "thinking": {
        "description": "Contemplative, looking up/away, touching chin",
        "prompt": "Person thinking deeply, looking slightly up, contemplative expression, subtle head tilt, hand near chin, thoughtful, upper body portrait",
    },
    "happy": {
        "description": "Smiling, bright, cheerful movements",
        "prompt": "Person smiling brightly, cheerful expression, gentle nodding, warm and friendly body language, happy mood, upper body portrait",
    },
    "sad": {
        "description": "Downcast, slower movements, sighing",
        "prompt": "Person looking slightly down, melancholy expression, slow movements, subtle shoulder drop, reflective mood, upper body portrait",
    },
    "surprised": {
        "description": "Eyes wide, head back slightly, quick reaction",
        "prompt": "Person looking surprised, eyes widening, slight backward head movement, raised eyebrows, quick expressive reaction, upper body portrait",
    },
    "explaining": {
        "description": "Gesturing while talking, steady eye contact",
        "prompt": "Person explaining something, hand gestures while talking, steady eye contact, confident posture, clear articulation movements, upper body portrait",
    },
    "emphatic": {
        "description": "Strong emphasis, nodding, decisive gestures",
        "prompt": "Person speaking emphatically, strong nodding, decisive hand gestures, firm expression, passionate delivery, upper body portrait",
    },
    "playful": {
        "description": "Mischievous, head tilts, light bounce",
        "prompt": "Person being playful, mischievous smile, playful head tilts, light bouncy movements, teasing expression, fun energy, upper body portrait",
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
) -> list[dict]:
    """Select motion references for all script chunks.

    Avoids consecutive use of the same clip.
    Returns list of dicts with chunk_id, emotion, motion_ref_path.
    """
    if index is None:
        index = load_motion_index()

    emotions = index.get("emotions", {})
    results = []
    last_clip_path = None

    for chunk in script_chunks:
        emotion = chunk.get("emotion", "neutral")
        chunk_id = chunk.get("chunk_id", "")

        # Get candidates for this emotion
        candidates = _get_clip_paths(emotion, emotions)

        # Fallback to neutral
        if not candidates and emotion != "neutral":
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
                "emotion": emotion,
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
            "emotion": emotion,
            "motion_ref_path": str(selected),
        })

    return results


def _get_clip_paths(emotion: str, emotions: dict) -> list[Path]:
    """Get all existing clip paths for an emotion."""
    clips = emotions.get(emotion, [])
    paths = []
    for clip in clips:
        path = MOTION_REFS_DIR / emotion / clip
        if path.exists():
            paths.append(path)
    return paths


def generate_motion_reference(
    emotion: str,
    reference_image_path: Path,
    clip_index: int = 1,
) -> Path:
    """Generate a single motion reference clip using Kling 3.0 image-to-video.

    This creates the motion SOURCE clip (not the final video).
    Uses Kling 3.0 because we just need natural motion, not character transfer.
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
        "fal-ai/kling-video/v2/master/image-to-video",
        arguments={
            "prompt": prompt,
            "image_url": image_url,
            "duration": "5",
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
