"""Audio mixing: combine voice, BGM, and SFX."""

import subprocess
from pathlib import Path

from .config import ensure_dirs


def mix_audio(
    voice_path: Path,
    output_path: Path,
    bgm_path: Path | None = None,
    bgm_volume_db: float = -18.0,
    sfx_path: Path | None = None,
    sfx_volume_db: float = -6.0,
    normalize_lufs: float = -14.0,
) -> Path:
    """Mix voice with optional BGM and SFX using FFmpeg.

    Args:
        voice_path: Path to voice audio.
        output_path: Output path for mixed audio.
        bgm_path: Optional background music.
        bgm_volume_db: BGM volume relative to voice (default -18dB).
        sfx_path: Optional sound effects.
        sfx_volume_db: SFX volume (default -6dB).
        normalize_lufs: Target loudness in LUFS (default -14, Instagram standard).
    """
    ensure_dirs(output_path.parent)

    inputs = ["-i", str(voice_path)]
    filter_parts = []
    amix_inputs = ["[voice]"]

    # Voice at 0dB (reference)
    filter_parts.append("[0:a]volume=0dB[voice]")
    input_idx = 1

    if bgm_path and bgm_path.exists():
        inputs.extend(["-i", str(bgm_path)])
        filter_parts.append(f"[{input_idx}:a]volume={bgm_volume_db}dB[bgm]")
        amix_inputs.append("[bgm]")
        input_idx += 1

    if sfx_path and sfx_path.exists():
        inputs.extend(["-i", str(sfx_path)])
        filter_parts.append(f"[{input_idx}:a]volume={sfx_volume_db}dB[sfx]")
        amix_inputs.append("[sfx]")
        input_idx += 1

    if len(amix_inputs) > 1:
        # Mix multiple audio streams
        mix_label = "".join(amix_inputs)
        filter_parts.append(
            f"{mix_label}amix=inputs={len(amix_inputs)}:duration=first:dropout_transition=2[mixed]"
        )
        final_label = "[mixed]"
    else:
        final_label = "[voice]"

    # Loudness normalization
    filter_parts.append(
        f"{final_label}loudnorm=I={normalize_lufs}:TP=-1.5:LRA=11[out]"
    )

    filter_str = ";".join(filter_parts)

    cmd = [
        "ffmpeg", "-y",
        *inputs,
        "-filter_complex", filter_str,
        "-map", "[out]",
        "-c:a", "pcm_s16le",
        "-ar", "44100",
        str(output_path),
    ]

    subprocess.run(cmd, capture_output=True, check=True)
    return output_path


def mix_all_chunks(
    voice_dir: Path,
    output_dir: Path,
    chunks: list[dict],
    bgm_path: Path | None = None,
) -> list[dict]:
    """Mix audio for all chunks.

    Returns list of dicts with chunk_id and mixed_audio_path.
    """
    ensure_dirs(output_dir)
    results = []

    for chunk in chunks:
        chunk_id = chunk["chunk_id"]
        voice_path = Path(voice_dir) / f"{chunk_id}_voice.wav"
        output_path = output_dir / f"{chunk_id}_mixed.wav"

        if voice_path.exists():
            mix_audio(voice_path, output_path, bgm_path=bgm_path)
            results.append({
                "chunk_id": chunk_id,
                "mixed_audio_path": str(output_path),
            })

    return results
