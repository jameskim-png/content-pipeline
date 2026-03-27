"""Video chunking using VAD + scene detection."""

import json
from pathlib import Path

import torch
import numpy as np

from .utils import save_json, load_json, cut_video, cut_audio, get_video_info
from .config import ensure_dirs


MAX_CHUNK_DURATION = 5.0  # seconds
MIN_CHUNK_DURATION = 0.5  # seconds
PAUSE_THRESHOLD_MS = 300  # milliseconds


def detect_speech_pauses(vocals_path: Path, threshold_ms: int = PAUSE_THRESHOLD_MS) -> list[float]:
    """Detect speech pauses in vocals using Silero VAD.

    Returns list of pause timestamps (seconds) where speech stops.
    """
    import torchaudio

    # Load Silero VAD model
    model, utils = torch.hub.load(
        repo_or_dir="snakers4/silero-vad",
        model="silero_vad",
        force_reload=False,
    )
    (get_speech_timestamps, _, read_audio, *_) = utils

    # Read audio (Silero expects 16kHz mono)
    wav = read_audio(str(vocals_path), sampling_rate=16000)

    # Get speech timestamps
    speech_timestamps = get_speech_timestamps(
        wav, model,
        sampling_rate=16000,
        threshold=0.5,
        min_silence_duration_ms=threshold_ms,
        min_speech_duration_ms=100,
    )

    # Convert to pause boundaries (gaps between speech segments)
    pauses = []
    for i in range(len(speech_timestamps) - 1):
        end_of_speech = speech_timestamps[i]["end"] / 16000.0
        start_of_next = speech_timestamps[i + 1]["start"] / 16000.0
        gap = start_of_next - end_of_speech

        if gap >= threshold_ms / 1000.0:
            # Pause midpoint
            pauses.append(round((end_of_speech + start_of_next) / 2, 3))

    return pauses


def detect_scene_changes(video_path: Path) -> list[float]:
    """Detect visual scene changes using PySceneDetect.

    Returns list of scene boundary timestamps (seconds).
    """
    from scenedetect import open_video, SceneManager
    from scenedetect.detectors import AdaptiveDetector

    video = open_video(str(video_path))
    scene_manager = SceneManager()
    scene_manager.add_detector(AdaptiveDetector())
    scene_manager.detect_scenes(video)

    scene_list = scene_manager.get_scene_list()
    boundaries = []
    for scene in scene_list:
        # scene is (start_timecode, end_timecode)
        boundaries.append(scene[1].get_seconds())

    return boundaries


def merge_boundaries(
    speech_pauses: list[float],
    scene_changes: list[float],
    duration: float,
    max_chunk: float = MAX_CHUNK_DURATION,
    snap_window: float = 0.5,
) -> list[float]:
    """Merge speech pauses and scene changes into unified cut points.

    Prioritizes speech pauses. If a scene change is within snap_window of a
    speech pause, they merge. Otherwise, scene changes are added only if
    a chunk would exceed max_chunk without them.
    """
    # Start with speech pauses as primary
    cuts = sorted(set(speech_pauses))

    # Add scene changes that aren't near existing cuts
    for sc in scene_changes:
        if not any(abs(sc - c) < snap_window for c in cuts):
            cuts.append(sc)
    cuts = sorted(set(cuts))

    # Enforce max_chunk: if any segment > max_chunk, add midpoint cuts
    final_cuts = []
    prev = 0.0
    for cut in cuts:
        if cut - prev > max_chunk:
            # Add intermediate cuts
            n_splits = int((cut - prev) / max_chunk) + 1
            step = (cut - prev) / n_splits
            for i in range(1, n_splits):
                final_cuts.append(round(prev + step * i, 3))
        final_cuts.append(cut)
        prev = cut

    # Handle tail
    if duration - prev > max_chunk:
        n_splits = int((duration - prev) / max_chunk) + 1
        step = (duration - prev) / n_splits
        for i in range(1, n_splits):
            final_cuts.append(round(prev + step * i, 3))

    # Remove cuts too close to start/end
    final_cuts = [c for c in final_cuts if c > MIN_CHUNK_DURATION and c < duration - MIN_CHUNK_DURATION]
    return sorted(set(final_cuts))


def snap_to_sentence_boundaries(
    cuts: list[float],
    transcript_segments: list[dict],
    snap_window: float = 0.3,
) -> list[float]:
    """Adjust cut points to align with sentence boundaries from Whisper.

    transcript_segments: list of dicts with 'timestamp' (start, end) and 'text'.
    """
    sentence_ends = []
    for seg in transcript_segments:
        ts = seg.get("timestamp", [])
        if len(ts) >= 2 and ts[1] is not None:
            sentence_ends.append(ts[1])

    snapped = []
    for cut in cuts:
        # Find nearest sentence end within snap_window
        nearest = min(sentence_ends, key=lambda s: abs(s - cut), default=cut)
        if abs(nearest - cut) <= snap_window:
            snapped.append(round(nearest, 3))
        else:
            snapped.append(cut)

    return sorted(set(snapped))


def create_chunks(
    video_path: Path,
    vocals_path: Path,
    transcript: dict,
    output_dir: Path,
) -> list[dict]:
    """Run full chunking pipeline and cut video/audio files.

    Returns list of chunk metadata dicts.
    """
    ensure_dirs(output_dir)

    video_info = get_video_info(video_path)
    duration = video_info["duration"]

    # Step 1: Detect speech pauses
    speech_pauses = detect_speech_pauses(vocals_path)

    # Step 2: Detect scene changes
    scene_changes = detect_scene_changes(video_path)

    # Step 3: Merge boundaries
    cuts = merge_boundaries(speech_pauses, scene_changes, duration)

    # Step 4: Snap to sentence boundaries
    segments = transcript.get("segments", [])
    if segments:
        cuts = snap_to_sentence_boundaries(cuts, segments)

    # Build chunk list
    boundaries = [0.0] + cuts + [duration]
    chunks = []

    for i in range(len(boundaries) - 1):
        start = boundaries[i]
        end = boundaries[i + 1]

        if end - start < MIN_CHUNK_DURATION:
            continue

        chunk_id = f"chunk_{i + 1:03d}"
        chunk_dir = output_dir / chunk_id
        ensure_dirs(chunk_dir)

        # Cut video
        video_out = chunk_dir / "video.mp4"
        cut_video(video_path, video_out, start, end)

        # Cut audio (vocals)
        audio_out = chunk_dir / "audio.wav"
        cut_audio(vocals_path, audio_out, start, end)

        # Extract transcript segment
        chunk_text = _extract_transcript_segment(segments, start, end)

        chunk_meta = {
            "chunk_id": chunk_id,
            "index": i,
            "start_time": round(start, 3),
            "end_time": round(end, 3),
            "duration": round(end - start, 3),
            "transcript": chunk_text,
            "video_path": str(video_out),
            "audio_path": str(audio_out),
        }
        chunks.append(chunk_meta)

    # Save chunks.json
    save_json(chunks, output_dir / "chunks.json")

    return chunks


def _extract_transcript_segment(
    segments: list[dict],
    start: float,
    end: float,
) -> str:
    """Extract transcript text that falls within a time range."""
    texts = []
    for seg in segments:
        ts = seg.get("timestamp", [])
        if len(ts) < 2:
            continue
        seg_start = ts[0] or 0
        seg_end = ts[1] or seg_start
        # Segment overlaps with chunk
        if seg_start < end and seg_end > start:
            texts.append(seg.get("text", "").strip())
    return " ".join(texts)


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 5:
        print("Usage: python -m src.chunking <video_path> <vocals_path> <transcript_json> <output_dir>")
        sys.exit(1)

    video = Path(sys.argv[1])
    vocals = Path(sys.argv[2])
    transcript = load_json(Path(sys.argv[3]))
    out = Path(sys.argv[4])

    chunks = create_chunks(video, vocals, transcript, out)
    print(f"Created {len(chunks)} chunks")
    print(json.dumps(chunks, indent=2, ensure_ascii=False))
