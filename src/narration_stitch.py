"""Narration reel assembly: concatenate silent clips + overlay narration audio.

Fundamentally different from talking-head stitching:
- TH: each chunk has synced video+audio, then concat
- NR: concat silent clips first, then overlay a single continuous narration track
"""

import subprocess
import json
from pathlib import Path

from .config import ensure_dirs
from .utils import get_audio_duration


def concatenate_voices(
    voice_manifest: list[dict],
    output_path: Path,
    gap: float = 0.05,
) -> Path:
    """Concatenate per-chunk voice WAVs into a single continuous narration track.

    Args:
        voice_manifest: List of dicts with 'chunk_id' and 'voice_path',
                        sorted by chunk_id.
        output_path: Where to save the combined narration WAV.
        gap: Silence gap between chunks in seconds.

    Returns:
        Path to the combined narration audio.
    """
    ensure_dirs(output_path.parent)

    # Sort by chunk_id
    manifest = sorted(voice_manifest, key=lambda x: x["chunk_id"])

    if len(manifest) == 1:
        # Single chunk — just copy
        import shutil
        shutil.copy2(manifest[0]["voice_path"], output_path)
        return output_path

    # Detect sample rate from first voice file
    sample_rate = _get_audio_sample_rate(Path(manifest[0]["voice_path"]))

    # Build ffmpeg filter for concatenation with gaps
    inputs = []
    for i, entry in enumerate(manifest):
        inputs.extend(["-i", entry["voice_path"]])

    n = len(manifest)
    gap_ms = int(gap * 1000)
    filter_chain = ""
    concat_inputs = []

    for i in range(n):
        concat_inputs.append(f"[{i}:a]")
        if i < n - 1 and gap_ms > 0:
            filter_chain += (
                f"anullsrc=r={sample_rate}:cl=mono:d={gap}[silence_{i}]; "
            )
            concat_inputs.append(f"[silence_{i}]")

    total_segments = len(concat_inputs)
    filter_chain += "".join(concat_inputs) + f"concat=n={total_segments}:v=0:a=1[out]"

    cmd = ["ffmpeg", "-y"]
    cmd.extend(inputs)
    cmd.extend([
        "-filter_complex", filter_chain,
        "-map", "[out]",
        "-c:a", "pcm_s16le",
        "-ar", str(sample_rate),
        str(output_path),
    ])

    subprocess.run(cmd, capture_output=True, check=True)
    return output_path


def stitch_narration(
    scene_clips: list[dict],
    narration_path: Path,
    output_path: Path,
    bgm_path: Path | None = None,
    bgm_volume: float = 0.15,
    crossfade_ms: int = 300,
    target_fps: int = 30,
    target_width: int = 720,
    target_height: int = 1280,
    normalize_lufs: float = -14.0,
    voice_manifest: list[dict] | None = None,
) -> Path:
    """Assemble narration reel: silent clips + narration audio overlay.

    Steps:
    1. Normalize and concat silent video clips (with optional crossfade)
    2. Build narration track synced to scene transitions (if voice_manifest given)
    3. Mix narration + BGM if provided
    4. Combine video + mixed audio

    Args:
        scene_clips: List of dicts with 'chunk_id' and 'video_path'.
        narration_path: Path to the continuous narration audio.
                        Overridden if voice_manifest is provided.
        output_path: Final output video path.
        bgm_path: Optional background music file.
        bgm_volume: BGM volume relative to narration (0.0 to 1.0).
        crossfade_ms: Crossfade duration between clips in milliseconds.
        target_fps: Target frame rate.
        target_width: Target video width.
        target_height: Target video height.
        normalize_lufs: Audio loudness normalization target.
        voice_manifest: Optional per-chunk voice data. When provided, builds
                        narration track with timing synced to scene transitions.

    Returns:
        Path to the final assembled video.
    """
    ensure_dirs(output_path.parent)

    # Sort clips by chunk_id
    clips = sorted(scene_clips, key=lambda x: x["chunk_id"])

    # Step 1: Normalize each clip to consistent format
    normalized = []
    for i, clip in enumerate(clips):
        norm_path = output_path.parent / f"_nr_norm_{i:03d}.mp4"
        _normalize_silent_clip(
            video_path=Path(clip["video_path"]),
            output_path=norm_path,
            target_fps=target_fps,
            target_width=target_width,
            target_height=target_height,
        )
        normalized.append(norm_path)

    # Step 1.5: If voice_manifest provided, build synced narration
    if voice_manifest:
        clip_durations = [_get_video_duration(p) for p in normalized]
        crossfade_s = crossfade_ms / 1000.0
        narration_path = _build_synced_narration(
            voice_manifest, clip_durations, crossfade_s, output_path.parent
        )

    # Step 2: Concat video clips
    concat_video = output_path.parent / "_nr_concat_video.mp4"
    if len(normalized) == 1:
        import shutil
        shutil.copy2(normalized[0], concat_video)
    elif crossfade_ms > 0:
        _concat_with_crossfade(normalized, concat_video, crossfade_ms, target_fps)
    else:
        _concat_simple(normalized, concat_video)

    # Step 3: Mix narration + BGM
    if bgm_path and bgm_path.exists():
        mixed_audio = output_path.parent / "_nr_mixed_audio.wav"
        _mix_narration_bgm(narration_path, bgm_path, mixed_audio, bgm_volume)
        audio_source = mixed_audio
    else:
        audio_source = narration_path

    # Step 4: Combine video + audio
    cmd = [
        "ffmpeg", "-y",
        "-i", str(concat_video),
        "-i", str(audio_source),
        "-map", "0:v:0",
        "-map", "1:a:0",
        "-c:v", "libx264", "-preset", "medium", "-crf", "18",
        "-c:a", "aac", "-b:a", "192k",
        "-af", f"loudnorm=I={normalize_lufs}:TP=-1.5:LRA=11",
        "-shortest",
        "-movflags", "+faststart",
        str(output_path),
    ]
    subprocess.run(cmd, capture_output=True, check=True)

    # Cleanup temp files
    for p in normalized:
        p.unlink(missing_ok=True)
    concat_video.unlink(missing_ok=True)
    for tmp_name in ["_nr_mixed_audio.wav", "_nr_synced_narration.wav"]:
        (output_path.parent / tmp_name).unlink(missing_ok=True)

    return output_path


def _build_synced_narration(
    voice_manifest: list[dict],
    clip_durations: list[float],
    crossfade_s: float,
    work_dir: Path,
) -> Path:
    """Build narration track with timing synced to scene transitions.

    Uses adelay to position each voice chunk at its scene's start time,
    then mixes into a single track. This eliminates audio-video drift
    that occurs when crossfade overlaps and voice gaps don't match.
    """
    manifest = sorted(voice_manifest, key=lambda x: x["chunk_id"])
    output_path = work_dir / "_nr_synced_narration.wav"

    if len(manifest) == 1:
        import shutil
        shutil.copy2(manifest[0]["voice_path"], output_path)
        return output_path

    # Calculate scene start times from clip durations + crossfade
    n = min(len(manifest), len(clip_durations))
    scene_starts = [0.0]
    for i in range(1, n):
        scene_starts.append(scene_starts[-1] + clip_durations[i - 1] - crossfade_s)

    # Build ffmpeg: adelay each voice to its scene start, then amix
    inputs = []
    filter_parts = []
    mix_labels = []

    for i, entry in enumerate(manifest[:n]):
        inputs.extend(["-i", entry["voice_path"]])
        delay_ms = max(0, int(scene_starts[i] * 1000))
        filter_parts.append(f"[{i}:a]adelay={delay_ms}|{delay_ms}[d{i}]")
        mix_labels.append(f"[d{i}]")

    filter_chain = "; ".join(filter_parts)
    filter_chain += (
        f"; {''.join(mix_labels)}"
        f"amix=inputs={n}:duration=longest:normalize=0[out]"
    )

    cmd = ["ffmpeg", "-y"]
    cmd.extend(inputs)
    cmd.extend([
        "-filter_complex", filter_chain,
        "-map", "[out]",
        "-c:a", "pcm_s16le",
        "-ar", "44100",
        str(output_path),
    ])
    subprocess.run(cmd, capture_output=True, check=True)
    return output_path


def _normalize_silent_clip(
    video_path: Path,
    output_path: Path,
    target_fps: int,
    target_width: int,
    target_height: int,
) -> Path:
    """Re-encode a clip to consistent format, stripping any audio."""
    cmd = [
        "ffmpeg", "-y",
        "-i", str(video_path),
        "-an",  # Strip audio
        "-vf", (
            f"scale={target_width}:{target_height}"
            f":force_original_aspect_ratio=decrease,"
            f"pad={target_width}:{target_height}:(ow-iw)/2:(oh-ih)/2,"
            f"fps={target_fps}"
        ),
        "-c:v", "libx264", "-preset", "fast", "-crf", "18",
        str(output_path),
    ]
    subprocess.run(cmd, capture_output=True, check=True)
    return output_path


def _concat_simple(clips: list[Path], output_path: Path) -> Path:
    """Simple concat without crossfade using concat demuxer."""
    concat_file = output_path.parent / "_nr_concat_list.txt"
    with open(concat_file, "w") as f:
        for p in clips:
            f.write(f"file '{p}'\n")

    cmd = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0",
        "-i", str(concat_file),
        "-c:v", "copy",
        "-an",
        str(output_path),
    ]
    subprocess.run(cmd, capture_output=True, check=True)
    concat_file.unlink(missing_ok=True)
    return output_path


def _concat_with_crossfade(
    clips: list[Path],
    output_path: Path,
    crossfade_ms: int,
    target_fps: int,
) -> Path:
    """Concat clips with video crossfade transitions.

    Uses xfade filter for smooth transitions between scenes.
    """
    if len(clips) < 2:
        import shutil
        shutil.copy2(clips[0], output_path)
        return output_path

    crossfade_s = crossfade_ms / 1000.0

    # Get durations for offset calculation
    durations = []
    for clip in clips:
        dur = _get_video_duration(clip)
        durations.append(dur)

    # Build xfade filter chain
    inputs = []
    for clip in clips:
        inputs.extend(["-i", str(clip)])

    # Chain xfade filters
    filter_parts = []
    offset = durations[0] - crossfade_s

    if len(clips) == 2:
        filter_parts.append(
            f"[0:v][1:v]xfade=transition=fade:duration={crossfade_s}:offset={offset}[out]"
        )
    else:
        # First pair
        filter_parts.append(
            f"[0:v][1:v]xfade=transition=fade:duration={crossfade_s}:offset={offset}[v1]"
        )

        for i in range(2, len(clips)):
            prev_label = f"[v{i-1}]"
            offset += durations[i-1] - crossfade_s

            if i == len(clips) - 1:
                filter_parts.append(
                    f"{prev_label}[{i}:v]xfade=transition=fade"
                    f":duration={crossfade_s}:offset={offset}[out]"
                )
            else:
                filter_parts.append(
                    f"{prev_label}[{i}:v]xfade=transition=fade"
                    f":duration={crossfade_s}:offset={offset}[v{i}]"
                )

    filter_complex = "; ".join(filter_parts)

    cmd = ["ffmpeg", "-y"]
    cmd.extend(inputs)
    cmd.extend([
        "-filter_complex", filter_complex,
        "-map", "[out]",
        "-c:v", "libx264", "-preset", "fast", "-crf", "18",
        "-an",
        str(output_path),
    ])
    subprocess.run(cmd, capture_output=True, check=True)
    return output_path


def _mix_narration_bgm(
    narration_path: Path,
    bgm_path: Path,
    output_path: Path,
    bgm_volume: float = 0.15,
) -> Path:
    """Mix narration voice with background music."""
    narration_dur = get_audio_duration(narration_path)

    fade_start = max(0, narration_dur - 2)
    fade_dur = min(2, narration_dur)

    cmd = [
        "ffmpeg", "-y",
        "-i", str(narration_path),
        "-i", str(bgm_path),
        "-filter_complex",
        (
            f"[1:a]volume={bgm_volume},"
            f"afade=t=out:st={fade_start}:d={fade_dur},"
            f"aloop=loop=-1:size=2e+09,atrim=0:{narration_dur}[bgm];"
            f"[0:a][bgm]amix=inputs=2:duration=first[out]"
        ),
        "-map", "[out]",
        "-c:a", "pcm_s16le",
        "-ar", "44100",
        str(output_path),
    ]
    subprocess.run(cmd, capture_output=True, check=True)
    return output_path


def _get_video_duration(video_path: Path) -> float:
    """Get video duration in seconds."""
    cmd = [
        "ffprobe", "-v", "quiet", "-print_format", "json",
        "-show_format", str(video_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    probe = json.loads(result.stdout)
    return float(probe.get("format", {}).get("duration", 0))


def _get_audio_sample_rate(audio_path: Path) -> int:
    """Get audio sample rate in Hz via ffprobe."""
    cmd = [
        "ffprobe", "-v", "quiet", "-print_format", "json",
        "-show_streams", str(audio_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    probe = json.loads(result.stdout)
    for stream in probe.get("streams", []):
        if stream.get("codec_type") == "audio":
            return int(stream.get("sample_rate", 24000))
    return 24000
