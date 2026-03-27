"""Analysis helpers: title extraction, BGM analysis, per-chunk analysis.

These functions generate prompts/instructions for Claude to execute.
Actual Claude calls happen in the skill layer (the .md commands).
This module provides structured prompt templates and result parsers.
"""

import json
from pathlib import Path

from .utils import save_json, load_json


# --- Prompt Templates ---

TITLE_EXTRACTION_PROMPT = """Analyze this Instagram video and extract the title/topic.

Video caption: {caption}
First segment transcript: {first_segment}

Return JSON:
{{
  "title_original": "<original language title>",
  "title_english": "<english translation if not english>",
  "topic_summary": "<1-2 sentence summary of the video topic>"
}}"""


BGM_ANALYSIS_PROMPT = """Analyze the background music from these separated audio stems.

I have isolated the non-vocal audio (drums, bass, other instruments).
Listen to the audio characteristics and describe:

Return JSON:
{{
  "has_bgm": true/false,
  "genre": "<genre if applicable>",
  "tempo_bpm": <estimated BPM or null>,
  "mood": "<mood description>",
  "energy_level": "<low/medium/high>",
  "instruments": ["<detected instruments>"],
  "description": "<brief overall description>"
}}"""


CHUNK_ANALYSIS_PROMPT = """Analyze this video chunk for recreation purposes.

Chunk {chunk_id} ({start}s - {end}s):
Transcript: "{transcript}"

Analyze and return JSON:
{{
  "facial_expressions": ["<key expressions observed>"],
  "body_movements": ["<key movements/gestures>"],
  "camera_movement": "<static/pan/zoom/etc>",
  "overlays": {{
    "text_overlays": ["<any text shown on screen>"],
    "graphics": ["<stickers, emojis, graphics>"],
    "effects": ["<filters, transitions, effects>"]
  }},
  "sound_effects": ["<non-speech sounds>"],
  "speaking_style": "<tone, pace, emphasis notes>",
  "recreation_notes": "<special notes for recreating this chunk>"
}}"""


def build_title_prompt(caption: str, first_segment: str) -> str:
    """Build prompt for title extraction."""
    return TITLE_EXTRACTION_PROMPT.format(
        caption=caption,
        first_segment=first_segment,
    )


def build_bgm_prompt() -> str:
    """Build prompt for BGM analysis."""
    return BGM_ANALYSIS_PROMPT


def build_chunk_analysis_prompt(
    chunk_id: str,
    start: float,
    end: float,
    transcript: str,
) -> str:
    """Build prompt for per-chunk analysis."""
    return CHUNK_ANALYSIS_PROMPT.format(
        chunk_id=chunk_id,
        start=start,
        end=end,
        transcript=transcript,
    )


def save_analysis(video_dir: Path, analysis_data: dict) -> Path:
    """Save video-level analysis (title, BGM) to analysis.json."""
    path = video_dir / "analysis.json"
    save_json(analysis_data, path)
    return path


def save_chunk_analysis(chunk_dir: Path, analysis_data: dict) -> Path:
    """Save per-chunk analysis to chunk's analysis.json."""
    path = chunk_dir / "analysis.json"
    save_json(analysis_data, path)
    return path


def build_index(
    video_dir: Path,
    account_url: str,
    video_url: str,
    video_info: dict,
    transcript: dict,
    analysis: dict,
    chunks: list[dict],
) -> dict:
    """Build and save the master index.json for an analyzed video."""
    from datetime import datetime

    index = {
        "account_url": account_url,
        "video_url": video_url,
        "download_date": datetime.now().isoformat(),
        "video_metadata": video_info,
        "transcript": transcript,
        "bgm_analysis": analysis.get("bgm", {}),
        "title": analysis.get("title", {}),
        "chunks": chunks,
        "status": "analyzed",
    }

    save_json(index, video_dir / "index.json")
    return index


def load_index(video_dir: Path) -> dict:
    """Load index.json from a video directory."""
    return load_json(video_dir / "index.json")
