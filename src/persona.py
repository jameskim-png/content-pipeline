"""Persona management: character sheet + background generation via fal.ai (FLUX.2 Pro)."""

import json
from pathlib import Path

import fal_client

from .config import PERSONAS_DIR, get_api_key, ensure_dirs
from .utils import save_json, load_json


# --- Prompt Templates for Claude (persona parsing) ---

PERSONA_PARSE_PROMPT = """사용자가 캐릭터를 자유롭게 설명했어. 이걸 구조화해줘.

사용자 입력: "{user_input}"

다음 JSON 형식으로 파싱해. 모르는 필드는 null로:
{{
  "name": "<캐릭터 이름 또는 별명>",
  "original_description": "<사용자가 입력한 원본 설명 그대로>",
  "gender": "<male/female/neutral>",
  "age_range": "<예: 20대 후반>",
  "ethnicity": "<예: Korean>",
  "visual_traits": "<외모 특징>",
  "clothing": "<의상 설명>",
  "hair": "<머리 스타일>",
  "makeup": "<화장 수준>",
  "voice_tone": "<목소리 톤 설명>",
  "speech_level": "<존댓말/반말>",
  "vibe": "<전반적 분위기>",
  "reference_url": "<참고 URL이 있으면>"
}}

null인 필드가 있으면, 사용자에게 물어볼 추가 질문도 함께 제시해.
추가 질문은 "missing_questions" 배열로 반환해."""


PERSONA_FOLLOWUP_PROMPT = """캐릭터 설정에서 빠진 부분을 물어봐야 해.

현재 persona spec:
{spec_json}

null인 필드: {missing_fields}

각 null 필드에 대해 자연스러운 한국어로 질문을 만들어줘.
합리적인 기본값도 함께 추천해. JSON으로:
{{
  "questions": [
    {{
      "field": "<field_name>",
      "question": "<한국어 질문>",
      "suggestion": "<추천 기본값>"
    }}
  ]
}}"""


def build_persona_parse_prompt(user_input: str) -> str:
    """Build prompt for Claude to parse free-text persona description."""
    return PERSONA_PARSE_PROMPT.format(user_input=user_input)


def build_persona_followup_prompt(spec: dict) -> str:
    """Build prompt for Claude to generate follow-up questions."""
    missing = [k for k, v in spec.items() if v is None and k not in ("reference_url", "original_description")]
    return PERSONA_FOLLOWUP_PROMPT.format(
        spec_json=json.dumps(spec, ensure_ascii=False, indent=2),
        missing_fields=", ".join(missing),
    )


def build_reference_prompt(
    persona_spec: dict,
    background_desc: str,
    style: str = "real",
) -> str:
    """Build prompt for generating character directly on background.

    This avoids background removal (which causes white fringe artifacts).
    Style: "real" (photorealistic), "anime", "3d".
    """
    # Character description
    desc_parts = []
    if persona_spec.get("gender"):
        desc_parts.append(persona_spec["gender"])
    if persona_spec.get("age_range"):
        desc_parts.append(persona_spec["age_range"])
    if persona_spec.get("ethnicity"):
        desc_parts.append(persona_spec["ethnicity"])
    if persona_spec.get("visual_traits"):
        desc_parts.append(persona_spec["visual_traits"])
    if persona_spec.get("hair"):
        desc_parts.append(f"Hair: {persona_spec['hair']}")
    if persona_spec.get("clothing"):
        desc_parts.append(f"Wearing: {persona_spec['clothing']}")
    if persona_spec.get("makeup"):
        desc_parts.append(f"Makeup: {persona_spec['makeup']}")

    character_desc = ", ".join(desc_parts)

    style_map = {
        "real": "Photorealistic, high quality photograph",
        "anime": "Anime style illustration, high quality",
        "3d": "3D cartoon character, Pixar Disney style render, stylized smooth skin, big expressive eyes, vibrant colors, CGI animation look",
    }
    style_prefix = style_map.get(style, style_map["real"])

    return (
        f"{style_prefix}. "
        f"Close-up upper body portrait from waist up, facing camera, centered in frame. "
        f"Character: {character_desc}. "
        f"Background: {background_desc}. "
        f"Vertical composition, single person, natural lighting."
    )


def generate_reference_image(
    persona_spec: dict,
    persona_name: str,
    background_desc: str,
    style: str = "real",
    seed: int = 42,
) -> Path:
    """Generate character directly on background using FLUX.2 Pro.

    No background removal needed — character is composited in the generation prompt.
    Returns path to saved reference image (720x1280, 9:16).
    """
    get_api_key("FAL_KEY")
    persona_dir = PERSONAS_DIR / persona_name
    ensure_dirs(persona_dir)

    prompt = build_reference_prompt(persona_spec, background_desc, style)

    result = fal_client.subscribe(
        "fal-ai/flux-2-pro",
        arguments={
            "prompt": prompt,
            "image_size": {"width": 720, "height": 1280},
            "seed": seed,
            "safety_tolerance": "5",
        },
    )

    image_url = result["images"][0]["url"]
    image_path = persona_dir / f"reference_{style}.png"
    _download_image(image_url, image_path)

    return image_path


def build_character_sheet_prompt(persona_spec: dict) -> str:
    """Build image generation prompt for character sheet from persona spec."""
    parts = []
    parts.append("Character reference sheet with 6 views:")
    parts.append("Top row: face front view, face 3/4 view, face side profile")
    parts.append("Bottom row: full body front view, full body 3/4 view, full body side profile")
    parts.append("Clean white background, consistent lighting, reference sheet layout.")
    parts.append("")

    # Build character description from spec
    desc_parts = []
    if persona_spec.get("gender"):
        desc_parts.append(persona_spec["gender"])
    if persona_spec.get("age_range"):
        desc_parts.append(persona_spec["age_range"])
    if persona_spec.get("ethnicity"):
        desc_parts.append(persona_spec["ethnicity"])
    if persona_spec.get("visual_traits"):
        desc_parts.append(persona_spec["visual_traits"])
    if persona_spec.get("hair"):
        desc_parts.append(f"Hair: {persona_spec['hair']}")
    if persona_spec.get("clothing"):
        desc_parts.append(f"Wearing: {persona_spec['clothing']}")
    if persona_spec.get("makeup"):
        desc_parts.append(f"Makeup: {persona_spec['makeup']}")
    if persona_spec.get("vibe"):
        desc_parts.append(f"Overall vibe: {persona_spec['vibe']}")

    parts.append("Character: " + ", ".join(desc_parts))

    return "\n".join(parts)


def build_background_prompt(background_desc: str) -> str:
    """Build image generation prompt for background image."""
    return (
        f"Empty room/environment for video background. No people. Vertical 9:16 ratio.\n\n"
        f"Scene: {background_desc}\n\n"
        f"Photorealistic, high quality, suitable as a video call or talking head background."
    )


def generate_character_sheet(
    persona_spec: dict,
    persona_name: str,
    seed: int = 42,
) -> Path:
    """Generate character sheet image using FLUX.2 Pro.

    Returns path to saved character_sheet.png.
    """
    get_api_key("FAL_KEY")
    persona_dir = PERSONAS_DIR / persona_name
    ensure_dirs(persona_dir)

    prompt = build_character_sheet_prompt(persona_spec)

    result = fal_client.subscribe(
        "fal-ai/flux-2-pro",
        arguments={
            "prompt": prompt,
            "image_size": "landscape_16_9",
            "seed": seed,
            "safety_tolerance": "5",
        },
    )

    # Download and save image
    image_url = result["images"][0]["url"]
    image_path = persona_dir / "character_sheet.png"
    _download_image(image_url, image_path)

    return image_path


def generate_background(
    background_desc: str,
    persona_name: str,
    seed: int = 42,
) -> Path:
    """Generate background image using FLUX.2 Pro.

    Returns path to saved background.png.
    """
    get_api_key("FAL_KEY")
    persona_dir = PERSONAS_DIR / persona_name
    ensure_dirs(persona_dir)

    prompt = build_background_prompt(background_desc)

    result = fal_client.subscribe(
        "fal-ai/flux-2-pro",
        arguments={
            "prompt": prompt,
            "image_size": {"width": 720, "height": 1280},
            "seed": seed,
            "safety_tolerance": "5",
        },
    )

    image_url = result["images"][0]["url"]
    image_path = persona_dir / "background.png"
    _download_image(image_url, image_path)

    return image_path


def crop_front_face(character_sheet_path: Path, output_path: Path) -> Path:
    """Crop front-facing face from character sheet.

    Assumes top-left section of the 16:9 sheet is the front face view.
    """
    from PIL import Image

    img = Image.open(character_sheet_path)
    w, h = img.size

    # Character sheet layout: 3 columns x 2 rows
    # Top-left = front face
    col_w = w // 3
    row_h = h // 2

    # Crop top-left cell (front face)
    face_crop = img.crop((0, 0, col_w, row_h))
    face_crop.save(output_path, "PNG")

    return output_path


def composite_face_on_background(
    face_image_path: Path,
    background_path: Path,
    output_path: Path | None = None,
) -> Path:
    """Composite front face image onto background (9:16, 1080x1920).

    Places face centered horizontally, in the upper third of the background.
    Used for non-HeyGen models (kling, veo3) where background isn't handled natively.
    """
    from PIL import Image

    bg = Image.open(background_path).convert("RGBA")
    bg = bg.resize((1080, 1920), Image.LANCZOS)

    face = Image.open(face_image_path).convert("RGBA")

    # Scale face to fit ~60% of background width
    target_w = int(1080 * 0.6)
    scale = target_w / face.width
    target_h = int(face.height * scale)
    face = face.resize((target_w, target_h), Image.LANCZOS)

    # Center horizontally, place in upper third
    x = (1080 - target_w) // 2
    y = int(1920 * 0.15)

    bg.paste(face, (x, y), face)

    if output_path is None:
        output_path = face_image_path.parent / "face_on_bg.png"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    bg.convert("RGB").save(output_path, "PNG")

    return output_path


def save_persona_metadata(
    persona_name: str,
    persona_spec: dict,
    background_desc: str,
    prompts_used: dict,
    **kwargs,
) -> Path:
    """Save all persona metadata to metadata.json.

    Core fields: name, persona_spec, background_description, prompts_used.
    Extended kwargs (saved if not None): video_model, heygen_avatar_id,
    tts_engine, elevenlabs_voice_id, elevenlabs_settings, subtitle_style.
    """
    persona_dir = PERSONAS_DIR / persona_name
    ensure_dirs(persona_dir)

    # Load existing metadata if present (merge, don't overwrite)
    path = persona_dir / "metadata.json"
    if path.exists():
        metadata = load_json(path)
    else:
        metadata = {}

    metadata.update({
        "name": persona_name,
        "persona_spec": persona_spec,
        "background_description": background_desc,
        "prompts_used": prompts_used,
    })

    # Save extended fields (only non-None values)
    for key, value in kwargs.items():
        if value is not None:
            metadata[key] = value

    save_json(metadata, path)
    return path


def _download_image(url: str, path: Path) -> None:
    """Download image from URL and save to path."""
    import requests

    response = requests.get(url, timeout=60)
    response.raise_for_status()
    with open(path, "wb") as f:
        f.write(response.content)


def load_persona(persona_name: str) -> dict:
    """Load persona metadata from disk."""
    return load_json(PERSONAS_DIR / persona_name / "metadata.json")


def list_personas() -> list[dict]:
    """Scan PERSONAS_DIR for all saved personas with metadata.json.

    Returns list of summary dicts with name, gender, age_range, vibe,
    and flags for which assets exist (character_sheet, background, front_face).
    """
    if not PERSONAS_DIR.exists():
        return []

    personas = []
    for d in sorted(PERSONAS_DIR.iterdir()):
        if not d.is_dir():
            continue
        meta_path = d / "metadata.json"
        if not meta_path.exists():
            continue

        meta = load_json(meta_path)
        spec = meta.get("persona_spec", {})

        personas.append({
            "name": meta.get("name", d.name),
            "gender": spec.get("gender"),
            "age_range": spec.get("age_range"),
            "vibe": spec.get("vibe"),
            "style": meta.get("style"),
            "has_character_sheet": (d / "character_sheet.png").exists(),
            "has_background": (d / "background.png").exists(),
            "has_front_face": (d / "front_face.png").exists(),
            "has_reference_real": (d / "reference_real.png").exists(),
            "has_reference_anime": (d / "reference_anime.png").exists(),
            "has_reference_3d": (d / "reference_3d.png").exists(),
            "video_model": meta.get("video_model"),
            "heygen_avatar_id": meta.get("heygen_avatar_id"),
            "tts_engine": meta.get("tts_engine"),
            "elevenlabs_voice_id": meta.get("elevenlabs_voice_id"),
            "dir": str(d),
        })

    return personas
