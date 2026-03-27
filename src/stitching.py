"""Final video stitching: combine chunks into final output."""

import subprocess
import json
from pathlib import Path

from .config import ensure_dirs
from .utils import save_json


def stitch_chunks(
    chunk_videos: list[dict],
    mixed_audios: list[dict],
    output_path: Path,
    crossfade_frames: int = 2,
    audio_crossfade_ms: int = 50,
    target_fps: int = 30,
    target_width: int = 1080,
    target_height: int = 1920,
    normalize_lufs: float = -14.0,
) -> Path:
    """Stitch all chunk videos + mixed audio into final video.

    Args:
        chunk_videos: list of dicts with 'chunk_id' and 'video_path'.
        mixed_audios: list of dicts with 'chunk_id' and 'mixed_audio_path'.
        output_path: Final output video path.
    """
    ensure_dirs(output_path.parent)

    # Create audio lookup
    audio_map = {a["chunk_id"]: a["mixed_audio_path"] for a in mixed_audios}

    # Sort by chunk_id
    chunk_videos = sorted(chunk_videos, key=lambda x: x["chunk_id"])

    if len(chunk_videos) == 1:
        # Single chunk — just combine video + audio
        return _combine_single(
            chunk_videos[0], audio_map, output_path,
            target_fps, target_width, target_height, normalize_lufs,
        )

    # Method: concat demuxer with re-encoding for consistency
    concat_file = output_path.parent / "concat_list.txt"

    # First, normalize each chunk video to same format
    normalized_chunks = []
    for i, chunk in enumerate(chunk_videos):
        norm_path = output_path.parent / f"_norm_{i:03d}.mp4"
        audio_path = audio_map.get(chunk["chunk_id"])

        _normalize_chunk(
            video_path=Path(chunk["video_path"]),
            audio_path=Path(audio_path) if audio_path else None,
            output_path=norm_path,
            target_fps=target_fps,
            target_width=target_width,
            target_height=target_height,
        )
        normalized_chunks.append(norm_path)

    # Write concat list
    with open(concat_file, "w") as f:
        for path in normalized_chunks:
            f.write(f"file '{path}'\n")

    # Concat with ffmpeg
    cmd = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0",
        "-i", str(concat_file),
        "-c:v", "libx264", "-preset", "medium", "-crf", "18",
        "-c:a", "aac", "-b:a", "192k",
        "-af", f"loudnorm=I={normalize_lufs}:TP=-1.5:LRA=11",
        "-r", str(target_fps),
        "-movflags", "+faststart",
        str(output_path),
    ]

    subprocess.run(cmd, capture_output=True, check=True)

    # Cleanup temp files
    for p in normalized_chunks:
        p.unlink(missing_ok=True)
    concat_file.unlink(missing_ok=True)

    return output_path


def _normalize_chunk(
    video_path: Path,
    audio_path: Path | None,
    output_path: Path,
    target_fps: int,
    target_width: int,
    target_height: int,
) -> Path:
    """Re-encode a chunk to consistent format."""
    cmd = ["ffmpeg", "-y", "-i", str(video_path)]

    if audio_path and audio_path.exists():
        cmd.extend(["-i", str(audio_path)])
        audio_map = ["-map", "0:v:0", "-map", "1:a:0"]
    else:
        audio_map = ["-map", "0:v:0"]
        if _has_audio(video_path):
            audio_map.extend(["-map", "0:a:0"])

    cmd.extend(audio_map)
    cmd.extend([
        "-vf", f"scale={target_width}:{target_height}:force_original_aspect_ratio=decrease,"
               f"pad={target_width}:{target_height}:(ow-iw)/2:(oh-ih)/2,fps={target_fps}",
        "-c:v", "libx264", "-preset", "fast", "-crf", "18",
        "-c:a", "aac", "-b:a", "192k", "-ar", "44100",
        "-shortest",
        str(output_path),
    ])

    subprocess.run(cmd, capture_output=True, check=True)
    return output_path


def _combine_single(
    chunk: dict,
    audio_map: dict,
    output_path: Path,
    target_fps: int,
    target_width: int,
    target_height: int,
    normalize_lufs: float,
) -> Path:
    """Handle single-chunk case."""
    video_path = Path(chunk["video_path"])
    audio_path = audio_map.get(chunk["chunk_id"])

    cmd = ["ffmpeg", "-y", "-i", str(video_path)]

    if audio_path:
        cmd.extend(["-i", str(audio_path)])
        map_args = ["-map", "0:v:0", "-map", "1:a:0"]
    else:
        map_args = []

    cmd.extend(map_args)
    cmd.extend([
        "-vf", f"scale={target_width}:{target_height}:force_original_aspect_ratio=decrease,"
               f"pad={target_width}:{target_height}:(ow-iw)/2:(oh-ih)/2,fps={target_fps}",
        "-c:v", "libx264", "-preset", "medium", "-crf", "18",
        "-c:a", "aac", "-b:a", "192k",
        "-af", f"loudnorm=I={normalize_lufs}:TP=-1.5:LRA=11",
        "-movflags", "+faststart",
        str(output_path),
    ])

    subprocess.run(cmd, capture_output=True, check=True)
    return output_path


def _has_audio(video_path: Path) -> bool:
    """Check if video file has an audio stream."""
    cmd = [
        "ffprobe", "-v", "quiet",
        "-select_streams", "a",
        "-show_entries", "stream=codec_type",
        "-of", "json", str(video_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    data = json.loads(result.stdout)
    return len(data.get("streams", [])) > 0


def generate_cost_report(
    video_id: str,
    output_dir: Path,
    api_calls: list[dict],
) -> Path:
    """Generate a cost breakdown report.

    api_calls: list of dicts with 'service', 'endpoint', 'estimated_cost'.
    """
    total = sum(c.get("estimated_cost", 0) for c in api_calls)

    report = {
        "video_id": video_id,
        "api_calls": api_calls,
        "total_estimated_cost_usd": round(total, 4),
    }

    path = output_dir / "cost_report.json"
    save_json(report, path)
    return path
