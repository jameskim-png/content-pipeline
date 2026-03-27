"""Audio source separation using Demucs."""

import subprocess
import shutil
from pathlib import Path

from .utils import extract_audio
from .config import ensure_dirs


DEMUCS_MODEL = "htdemucs"
STEM_NAMES = ["vocals", "drums", "bass", "other"]


def separate_audio(video_path: Path, output_dir: Path) -> dict[str, Path]:
    """Separate audio from video into vocals, drums, bass, other.

    Args:
        video_path: Path to the input video file.
        output_dir: Directory to save separated stems (e.g., ./data/account/video_id/audio/).

    Returns:
        Dict mapping stem name to output file path.
    """
    ensure_dirs(output_dir)

    # Extract audio from video first
    raw_audio = output_dir / "raw_audio.wav"
    extract_audio(video_path, raw_audio)

    # Run Demucs
    cmd = [
        "python", "-m", "demucs",
        "--name", DEMUCS_MODEL,
        "--out", str(output_dir / "_demucs_tmp"),
        "--two-stems", "vocals",  # Separate vocals vs rest first
        str(raw_audio),
    ]

    # Actually, htdemucs does 4-stem by default, let's use that
    cmd = [
        "python", "-m", "demucs",
        "--name", DEMUCS_MODEL,
        "--out", str(output_dir / "_demucs_tmp"),
        str(raw_audio),
    ]

    subprocess.run(cmd, check=True, capture_output=True)

    # Move stems to clean paths
    demucs_output = output_dir / "_demucs_tmp" / DEMUCS_MODEL / "raw_audio"
    stems = {}

    for stem_name in STEM_NAMES:
        src = demucs_output / f"{stem_name}.wav"
        dst = output_dir / f"{stem_name}.wav"
        if src.exists():
            shutil.move(str(src), str(dst))
            stems[stem_name] = dst

    # Cleanup temp files
    shutil.rmtree(output_dir / "_demucs_tmp", ignore_errors=True)
    raw_audio.unlink(missing_ok=True)

    return stems


def get_stems(audio_dir: Path) -> dict[str, Path]:
    """Load existing separated stems from directory."""
    stems = {}
    for stem_name in STEM_NAMES:
        path = audio_dir / f"{stem_name}.wav"
        if path.exists():
            stems[stem_name] = path
    return stems


if __name__ == "__main__":
    import sys
    import json

    if len(sys.argv) < 3:
        print("Usage: python -m src.audio_separation <video_path> <output_dir>")
        sys.exit(1)

    video = Path(sys.argv[1])
    out = Path(sys.argv[2])
    result = separate_audio(video, out)
    print(json.dumps({k: str(v) for k, v in result.items()}, indent=2))
