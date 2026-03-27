"""Common utilities for the pipeline."""

import json
import subprocess
from pathlib import Path


def save_json(data: dict | list, path: Path) -> None:
    """Save data as JSON with Korean-safe encoding."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_json(path: Path) -> dict | list:
    """Load JSON file."""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def get_video_info(video_path: Path) -> dict:
    """Get video metadata using ffprobe."""
    cmd = [
        "ffprobe", "-v", "quiet", "-print_format", "json",
        "-show_format", "-show_streams", str(video_path)
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    probe = json.loads(result.stdout)

    video_stream = next(
        (s for s in probe.get("streams", []) if s["codec_type"] == "video"), {}
    )
    audio_stream = next(
        (s for s in probe.get("streams", []) if s["codec_type"] == "audio"), {}
    )

    return {
        "duration": float(probe.get("format", {}).get("duration", 0)),
        "width": int(video_stream.get("width", 0)),
        "height": int(video_stream.get("height", 0)),
        "fps": _parse_fps(video_stream.get("r_frame_rate", "30/1")),
        "aspect_ratio": f"{video_stream.get('width', 0)}:{video_stream.get('height', 0)}",
        "audio_sample_rate": int(audio_stream.get("sample_rate", 44100)),
    }


def _parse_fps(fps_str: str) -> float:
    """Parse ffprobe fps string like '30/1' or '29.97'."""
    if "/" in fps_str:
        num, den = fps_str.split("/")
        return round(float(num) / float(den), 2) if float(den) != 0 else 30.0
    return float(fps_str)


def extract_audio(video_path: Path, output_path: Path, sample_rate: int = 44100) -> Path:
    """Extract audio from video as WAV."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg", "-y", "-i", str(video_path),
        "-vn", "-acodec", "pcm_s16le",
        "-ar", str(sample_rate), "-ac", "1",
        str(output_path)
    ]
    subprocess.run(cmd, capture_output=True, check=True)
    return output_path


def cut_video(
    input_path: Path, output_path: Path,
    start: float, end: float, with_audio: bool = True
) -> Path:
    """Cut a segment from a video file."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg", "-y",
        "-ss", str(start), "-to", str(end),
        "-i", str(input_path),
        "-c:v", "libx264", "-preset", "fast", "-crf", "18",
    ]
    if with_audio:
        cmd.extend(["-c:a", "aac", "-b:a", "192k"])
    else:
        cmd.append("-an")
    cmd.append(str(output_path))
    subprocess.run(cmd, capture_output=True, check=True)
    return output_path


def get_audio_duration(audio_path: Path) -> float:
    """Get audio file duration in seconds using ffprobe."""
    cmd = [
        "ffprobe", "-v", "quiet", "-print_format", "json",
        "-show_format", str(audio_path)
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    probe = json.loads(result.stdout)
    return float(probe.get("format", {}).get("duration", 0))


def cut_audio(
    input_path: Path, output_path: Path,
    start: float, end: float
) -> Path:
    """Cut a segment from an audio file."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg", "-y",
        "-ss", str(start), "-to", str(end),
        "-i", str(input_path),
        "-c:a", "pcm_s16le",
        str(output_path)
    ]
    subprocess.run(cmd, capture_output=True, check=True)
    return output_path
