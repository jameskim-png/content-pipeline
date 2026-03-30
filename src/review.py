"""Pre-generation reviewer for talking-head pipeline.

Validates and auto-fixes script chunks BEFORE TTS/video generation.
Catches issues that would otherwise waste API credits.
"""

import re
import math
from pathlib import Path

from .config import EMOTION_CATEGORIES, estimate_job_cost
from .motion_refs import _build_persona_emotion_map


# --- Constants ---

GROK_MAX_DURATION = 14  # Grok max 15s, 1s buffer
KLING26_MAX_DURATION = 10  # Kling 2.6 motion control max ~10s
MIN_CHUNK_DURATION = 3
KO_CHARS_PER_SECOND = 6  # Korean speaking rate: ~6 chars/sec


# --- Public API ---

def review_chunks(
    chunks: list[dict],
    persona_spec: dict | None = None,
    model: str = "grok",
) -> dict:
    """Pre-generation review: validate and auto-fix chunks before TTS.

    Auto-fix order:
    1. Recalculate durations from text length
    2. Split chunks exceeding model max duration
    3. Merge chunks below minimum duration
    4. Remap emotions based on persona
    5. Renumber chunk IDs
    6. Build prompt previews
    7. Estimate cost

    Returns dict with:
        chunks: list of reviewed/fixed chunks
        report: list of changes made
        prompts: list of prompt previews per chunk
        cost_estimate: estimated cost dict
        warnings: list of remaining issues
    """
    report = []
    warnings = []

    max_dur = GROK_MAX_DURATION if model == "grok" else KLING26_MAX_DURATION

    # 1. Recalculate durations
    chunks, duration_changes = _recalculate_durations(chunks)
    report.extend(duration_changes)

    # 2. Split long chunks
    chunks, split_changes = _split_long_chunks(chunks, max_dur)
    report.extend(split_changes)

    # 3. Merge short chunks
    chunks, merge_changes = _merge_short_chunks(chunks, MIN_CHUNK_DURATION)
    report.extend(merge_changes)

    # 4. Remap emotions
    chunks, emotion_changes = _remap_emotions(chunks, persona_spec)
    report.extend(emotion_changes)

    # 5. Renumber
    chunks, renumber_changes = _renumber_chunks(chunks)
    report.extend(renumber_changes)

    # 6. Build prompt previews
    prompts = _build_prompt_previews(chunks, persona_spec, model)

    # 7. Estimate cost
    total_duration = sum(c.get("estimated_duration", 0) for c in chunks)
    total_chars = sum(len(c.get("text", "")) for c in chunks)
    cost_estimate = estimate_job_cost(
        model=model,
        n_chunks=len(chunks),
        total_duration=total_duration,
        tts_engine="google",
        total_chars=total_chars,
        original_content=True,
    )

    # Validate remaining issues
    for chunk in chunks:
        dur = chunk.get("estimated_duration", 0)
        if dur > max_dur:
            warnings.append(
                f"{chunk['chunk_id']}: {dur:.1f}s exceeds {max_dur}s limit "
                f"(text too long to split at sentence boundary)"
            )
        emotion = chunk.get("emotion", "")
        if emotion and emotion not in EMOTION_CATEGORIES:
            warnings.append(
                f"{chunk['chunk_id']}: unknown emotion '{emotion}'"
            )

    return {
        "chunks": chunks,
        "report": report,
        "prompts": prompts,
        "cost_estimate": cost_estimate,
        "warnings": warnings,
    }


# --- Auto-fix helpers ---

def _recalculate_durations(chunks: list[dict]) -> tuple[list[dict], list[str]]:
    """Recalculate estimated_duration from text length using KO_CHARS_PER_SECOND."""
    changes = []
    for chunk in chunks:
        text = chunk.get("text", "")
        old_dur = chunk.get("estimated_duration", 0)
        new_dur = round(len(text) / KO_CHARS_PER_SECOND, 1)
        if new_dur < 1:
            new_dur = 1.0

        if abs(old_dur - new_dur) >= 1.0:
            changes.append(
                f"{chunk.get('chunk_id', '?')}: duration {old_dur}s -> {new_dur}s "
                f"(recalculated from {len(text)} chars)"
            )
        chunk["estimated_duration"] = new_dur
    return chunks, changes


def _split_long_chunks(
    chunks: list[dict], max_dur: float
) -> tuple[list[dict], list[str]]:
    """Split chunks exceeding max_dur at sentence boundaries."""
    result = []
    changes = []

    for chunk in chunks:
        dur = chunk.get("estimated_duration", 0)
        if dur <= max_dur:
            result.append(chunk)
            continue

        # Try splitting at sentence boundaries
        parts = _split_text_at_sentences(chunk["text"], max_dur)
        if len(parts) <= 1:
            # Cannot split further, keep as-is (warning will be raised)
            result.append(chunk)
            continue

        chunk_id = chunk.get("chunk_id", "chunk_000")
        changes.append(
            f"{chunk_id}: split into {len(parts)} parts "
            f"({dur:.1f}s -> {', '.join(f'{_text_duration(p):.1f}s' for p in parts)})"
        )

        for i, part_text in enumerate(parts):
            new_chunk = {
                **chunk,
                "chunk_id": f"{chunk_id}_p{i+1}",
                "text": part_text,
                "estimated_duration": _text_duration(part_text),
            }
            result.append(new_chunk)

    return result, changes


def _merge_short_chunks(
    chunks: list[dict], min_dur: float
) -> tuple[list[dict], list[str]]:
    """Merge chunks below min_dur into the shorter adjacent neighbor."""
    if len(chunks) <= 1:
        return chunks, []

    changes = []
    result = list(chunks)
    merged = True

    while merged:
        merged = False
        new_result = []
        skip_next = False

        for i, chunk in enumerate(result):
            if skip_next:
                skip_next = False
                continue

            dur = chunk.get("estimated_duration", 0)
            if dur >= min_dur or len(new_result) == 0 and i == len(result) - 1:
                new_result.append(chunk)
                continue

            # Find shorter neighbor to merge into
            prev_dur = new_result[-1].get("estimated_duration", float("inf")) if new_result else float("inf")
            next_dur = result[i + 1].get("estimated_duration", float("inf")) if i + 1 < len(result) else float("inf")

            if prev_dur <= next_dur and new_result:
                # Merge into previous
                target = new_result[-1]
                changes.append(
                    f"{chunk.get('chunk_id', '?')}: merged into {target.get('chunk_id', '?')} "
                    f"({dur:.1f}s < {min_dur}s min)"
                )
                target["text"] = target["text"].rstrip() + " " + chunk["text"].lstrip()
                target["estimated_duration"] = _text_duration(target["text"])
                merged = True
            elif i + 1 < len(result):
                # Merge into next
                target = result[i + 1]
                changes.append(
                    f"{chunk.get('chunk_id', '?')}: merged into {target.get('chunk_id', '?')} "
                    f"({dur:.1f}s < {min_dur}s min)"
                )
                target["text"] = chunk["text"].rstrip() + " " + target["text"].lstrip()
                target["estimated_duration"] = _text_duration(target["text"])
                merged = True
            else:
                new_result.append(chunk)

        result = new_result

    return result, changes


def _remap_emotions(
    chunks: list[dict], persona_spec: dict | None
) -> tuple[list[dict], list[str]]:
    """Remap emotions based on persona vibe using motion_refs logic."""
    if not persona_spec:
        return chunks, []

    emotion_map = _build_persona_emotion_map(persona_spec)
    if not emotion_map:
        return chunks, []

    changes = []
    for chunk in chunks:
        original = chunk.get("emotion", "neutral")
        remapped = emotion_map.get(original)
        if remapped and remapped != original:
            changes.append(
                f"{chunk.get('chunk_id', '?')}: emotion {original} -> {remapped} "
                f"(persona remap)"
            )
            chunk["original_emotion"] = original
            chunk["emotion"] = remapped

    return chunks, changes


def _renumber_chunks(chunks: list[dict]) -> tuple[list[dict], list[str]]:
    """Renumber chunk IDs sequentially from chunk_001."""
    changes = []
    for i, chunk in enumerate(chunks):
        new_id = f"chunk_{i + 1:03d}"
        old_id = chunk.get("chunk_id", "")
        if old_id != new_id:
            changes.append(f"{old_id} -> {new_id}")
            chunk["chunk_id"] = new_id
    return chunks, changes


def _build_prompt_previews(
    chunks: list[dict],
    persona_spec: dict | None,
    model: str,
) -> list[dict]:
    """Build preview of the prompts that will be sent to the video model."""
    previews = []
    for chunk in chunks:
        if model == "grok":
            prompt = _build_grok_prompt_preview(
                chunk.get("text", ""),
                persona_spec,
                chunk.get("emotion", "neutral"),
            )
        else:
            prompt = _build_kling26_prompt_preview(
                persona_spec,
                chunk.get("text", ""),
                chunk.get("emotion", "neutral"),
            )

        previews.append({
            "chunk_id": chunk.get("chunk_id", ""),
            "model": model,
            "prompt_preview": prompt[:200] + "..." if len(prompt) > 200 else prompt,
            "full_prompt_length": len(prompt),
        })

    return previews


# --- Text utilities ---

def _text_duration(text: str) -> float:
    """Estimate duration of Korean text in seconds."""
    dur = round(len(text) / KO_CHARS_PER_SECOND, 1)
    return max(1.0, dur)


def _split_text_at_sentences(text: str, max_dur: float) -> list[str]:
    """Split text at sentence boundaries to fit within max_dur.

    Sentence boundaries: '. ', '? ', '! ', '.\n', '?\n', '!\n'
    """
    # Find all sentence boundary positions
    boundary_pattern = re.compile(r'(?<=[.?!])\s+')
    sentences = boundary_pattern.split(text)

    if len(sentences) <= 1:
        return [text]

    parts = []
    current = ""

    for sentence in sentences:
        test = (current + " " + sentence).strip() if current else sentence
        if _text_duration(test) <= max_dur:
            current = test
        else:
            if current:
                parts.append(current)
            current = sentence

    if current:
        parts.append(current)

    return parts if len(parts) > 1 else [text]


# --- Prompt preview builders ---

def _build_grok_prompt_preview(
    chunk_text: str,
    persona_spec: dict | None,
    emotion: str,
) -> str:
    """Preview of the Grok video generation prompt."""
    parts = []

    if persona_spec:
        # Character appearance
        appearance = []
        if persona_spec.get("gender"):
            appearance.append(persona_spec["gender"])
        if persona_spec.get("age_range"):
            appearance.append(persona_spec["age_range"])
        if persona_spec.get("ethnicity"):
            appearance.append(persona_spec["ethnicity"])
        if persona_spec.get("hair"):
            appearance.append(persona_spec["hair"])
        if persona_spec.get("clothing"):
            appearance.append(persona_spec["clothing"])
        if appearance:
            parts.append(f"Character: {', '.join(appearance)}")

    parts.append("Close-up upper body, talking to camera, 9:16 vertical")

    # Emotion cue
    emotion_cues = {
        "neutral": "calm composed expression",
        "excited": "animated energetic gestures",
        "happy": "warm smile, bright expression",
        "sad": "reflective, downcast gaze",
        "surprised": "eyes widening, raised eyebrows",
        "thinking": "contemplative, looking slightly up",
        "explaining": "hand gestures while talking",
        "emphatic": "decisive nodding, firm expression",
        "calm": "relaxed posture, gentle movements",
        "playful": "mischievous smile, head tilts",
    }
    cue = emotion_cues.get(emotion, "natural expression")
    parts.append(cue)

    # Speech content hint
    if chunk_text:
        hint = chunk_text[:60] + "..." if len(chunk_text) > 60 else chunk_text
        parts.append(f'Speaking: "{hint}"')

    return ", ".join(parts)


def _build_kling26_prompt_preview(
    persona_spec: dict | None,
    chunk_text: str,
    emotion: str,
) -> str:
    """Preview of the Kling 2.6 enhanced prompt."""
    parts = ["Person talking to camera, chest-up close shot, 9:16 vertical framing"]

    if persona_spec:
        vibe = persona_spec.get("vibe", "")
        if vibe:
            parts.append(f"Vibe: {vibe}")

    if emotion:
        parts.append(f"Emotion: {emotion}")

    return ", ".join(parts)
