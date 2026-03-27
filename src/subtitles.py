"""Subtitle generation and burn-in."""

import subprocess
from pathlib import Path

from .config import ensure_dirs


def generate_srt(
    chunks: list[dict],
    output_path: Path,
) -> Path:
    """Generate SRT subtitle file from translated chunks.

    chunks: list of dicts with 'chunk_id', 'translated', 'start_time', 'end_time'.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    lines = []
    for i, chunk in enumerate(chunks, 1):
        start = _format_srt_time(chunk["start_time"])
        end = _format_srt_time(chunk["end_time"])
        text = chunk.get("translated", chunk.get("transcript", ""))

        lines.append(str(i))
        lines.append(f"{start} --> {end}")
        lines.append(text)
        lines.append("")

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    return output_path


def generate_ass(
    chunks: list[dict],
    output_path: Path,
    font_name: str = "Arial",
    font_size: int = 20,
    primary_color: str = "&H00FFFFFF",  # White
    outline_color: str = "&H00000000",  # Black
    margin_v: int = 40,
) -> Path:
    """Generate ASS subtitle file with styling.

    chunks: list of dicts with 'chunk_id', 'translated', 'start_time', 'end_time'.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    header = f"""[Script Info]
Title: ContentTalkingHeads Subtitles
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{font_name},{font_size},{primary_color},&H000000FF,{outline_color},&H80000000,-1,0,0,0,100,100,0,0,1,2,1,2,20,20,{margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

    events = []
    for chunk in chunks:
        start = _format_ass_time(chunk["start_time"])
        end = _format_ass_time(chunk["end_time"])
        text = chunk.get("translated", chunk.get("transcript", ""))
        # Escape ASS special chars
        text = text.replace("\\", "\\\\").replace("{", "\\{").replace("}", "\\}")

        events.append(f"Dialogue: 0,{start},{end},Default,,0,0,0,,{text}")

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(header)
        f.write("\n".join(events))
        f.write("\n")

    return output_path


def burn_subtitles(
    video_path: Path,
    subtitle_path: Path,
    output_path: Path,
) -> Path:
    """Burn subtitles into video using FFmpeg.

    Supports both .srt and .ass files.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    ext = subtitle_path.suffix.lower()

    if ext == ".ass":
        filter_str = f"ass='{subtitle_path}'"
    else:
        # SRT with styling
        filter_str = (
            f"subtitles='{subtitle_path}':"
            f"force_style='FontSize=20,PrimaryColour=&H00FFFFFF,"
            f"OutlineColour=&H00000000,BorderStyle=1,Outline=2,"
            f"Shadow=1,MarginV=40'"
        )

    cmd = [
        "ffmpeg", "-y",
        "-i", str(video_path),
        "-vf", filter_str,
        "-c:v", "libx264", "-preset", "fast", "-crf", "18",
        "-c:a", "copy",
        str(output_path),
    ]

    subprocess.run(cmd, capture_output=True, check=True)
    return output_path


def recalculate_subtitle_timings(
    voice_manifest: list[dict],
    translation_chunks: list[dict],
    gap: float = 0.05,
) -> list[dict]:
    """Recalculate subtitle timings based on actual TTS durations.

    Uses voice_manifest's actual_duration to compute cumulative start/end times.
    Adds a small gap between chunks for natural transitions.
    Merges text from translation_chunks.

    Returns list of dicts with chunk_id, translated, start_time, end_time.
    """
    # Build lookup from voice manifest
    duration_map = {}
    for entry in voice_manifest:
        duration_map[entry["chunk_id"]] = entry.get("actual_duration", 0)

    # Build text lookup from translation
    text_map = {}
    for chunk in translation_chunks:
        text_map[chunk["chunk_id"]] = chunk.get("translated", chunk.get("text", ""))

    result = []
    cursor = 0.0

    for entry in voice_manifest:
        chunk_id = entry["chunk_id"]
        duration = duration_map.get(chunk_id, 0)
        text = text_map.get(chunk_id, entry.get("text", ""))

        # Skip empty text chunks (silent segments)
        if not text.strip():
            cursor += duration + gap
            continue

        start_time = round(cursor, 3)
        end_time = round(cursor + duration, 3)

        result.append({
            "chunk_id": chunk_id,
            "translated": text,
            "start_time": start_time,
            "end_time": end_time,
        })

        cursor = end_time + gap

    return result


def _format_srt_time(seconds: float) -> str:
    """Format seconds to SRT timestamp: HH:MM:SS,mmm"""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds % 1) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def _format_ass_time(seconds: float) -> str:
    """Format seconds to ASS timestamp: H:MM:SS.cc"""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    cs = int((seconds % 1) * 100)
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"
