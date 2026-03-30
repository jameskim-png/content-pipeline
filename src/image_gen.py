"""Scene image generation using Flux 1.1 Pro via fal.ai."""

from pathlib import Path

import fal_client

from .config import get_api_key, ensure_dirs


def flux_generate_image(
    prompt: str,
    output_path: Path,
    width: int = 720,
    height: int = 1280,
    seed: int | None = None,
) -> Path:
    """Generate a single image using Flux 1.1 Pro via fal.ai.

    Args:
        prompt: Image generation prompt (English recommended for best results).
        output_path: Where to save the generated image.
        width: Image width (default 720 for 9:16 vertical).
        height: Image height (default 1280 for 9:16 vertical).
        seed: Optional seed for reproducibility.

    Returns:
        Path to the generated image.
    """
    get_api_key("FAL_KEY")
    ensure_dirs(output_path.parent)

    arguments = {
        "prompt": prompt,
        "image_size": {"width": width, "height": height},
        "num_images": 1,
        "safety_tolerance": "5",
    }
    if seed is not None:
        arguments["seed"] = seed

    result = fal_client.subscribe(
        "fal-ai/flux-pro/v1.1",
        arguments=arguments,
    )

    images = result.get("images", [])
    if not images:
        raise RuntimeError(
            f"Flux returned no images (safety filter or API error). Prompt: {prompt[:100]}"
        )

    image_url = images[0].get("url", "")
    if not image_url:
        raise RuntimeError("Flux returned an image entry with no URL.")

    _download_file(image_url, output_path)
    return output_path


def generate_scene_images(
    script: dict,
    output_dir: Path,
    width: int = 720,
    height: int = 1280,
) -> list[dict]:
    """Generate images for all scenes in a narration reel script.

    Combines style_prompt with each chunk's scene_description.
    Skips chunks whose image already exists (idempotent).

    Args:
        script: Narration reel script dict with style_prompt and chunks.
        output_dir: Directory to save images.

    Returns:
        List of dicts with chunk_id, image_path, and cost.
    """
    ensure_dirs(output_dir)
    style_prompt = script.get("style_prompt", "")
    results = []

    for chunk in script.get("chunks", []):
        chunk_id = chunk["chunk_id"]
        scene_desc = chunk.get("scene_description", "")

        output_path = output_dir / f"{chunk_id}_scene.png"

        # Skip if already generated
        if output_path.exists() and output_path.stat().st_size > 0:
            print(f"  {chunk_id}: image already exists, skipping")
            results.append({
                "chunk_id": chunk_id,
                "image_path": str(output_path),
                "cost": 0.0,
            })
            continue

        # Combine style + scene description
        if style_prompt and scene_desc:
            prompt = f"{style_prompt}. {scene_desc}"
        else:
            prompt = scene_desc or style_prompt

        if not prompt:
            print(f"  {chunk_id}: no scene_description, skipping")
            continue

        print(f"  {chunk_id}: generating image...")
        flux_generate_image(prompt, output_path, width=width, height=height)

        results.append({
            "chunk_id": chunk_id,
            "image_path": str(output_path),
            "cost": 0.06,  # Flux 1.1 Pro ~$0.06/image
        })
        print(f"  {chunk_id}: done")

    return results


def _download_file(url: str, path: Path) -> None:
    """Download file from URL."""
    import requests

    response = requests.get(url, timeout=120)
    response.raise_for_status()
    with open(path, "wb") as f:
        f.write(response.content)
