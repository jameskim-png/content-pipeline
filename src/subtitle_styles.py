"""Subtitle style library — builtin presets + user-defined styles.

Each style stores both ASS parameters (for generate_ass) and CSS preview
properties (for HTML preview), since ASS and CSS formatting differ.
"""

import json
from pathlib import Path

from .config import DATA_DIR

USER_STYLES_PATH = DATA_DIR / "subtitle_styles.json"

# --- Builtin Styles ---

BUILTIN_STYLES = {
    "default": {
        "label": "기본 — 흰색 아웃라인",
        "font_name": "Arial",
        "font_size": 48,
        "primary_color": "&H00FFFFFF",
        "outline_color": "&H00000000",
        "outline_width": 4,
        "shadow": 1,
        "bold": True,
        "alignment": 2,
        "margin_v": 480,
        "border_style": 1,
        "box_highlight": False,
        "box_color": "&H80000000",
        "preview_css": {
            "color": "#FFFFFF",
            "font_size": "48px",
            "font_weight": "700",
            "text_shadow": "-4px -4px 0 black, 4px -4px 0 black, -4px 4px 0 black, 4px 4px 0 black, -4px 0 0 black, 4px 0 0 black, 0 -4px 0 black, 0 4px 0 black",
            "background": "none",
        },
    },
    "yellow-bold": {
        "label": "강조 — 노란색 볼드",
        "font_name": "Arial",
        "font_size": 52,
        "primary_color": "&H0000D7FF",  # ASS: BGR order, #FFD700 = &H0000D7FF
        "outline_color": "&H00000000",
        "outline_width": 5,
        "shadow": 2,
        "bold": True,
        "alignment": 2,
        "margin_v": 480,
        "border_style": 1,
        "box_highlight": False,
        "box_color": "&H80000000",
        "preview_css": {
            "color": "#FFD700",
            "font_size": "52px",
            "font_weight": "700",
            "text_shadow": "-5px -5px 0 black, 5px -5px 0 black, -5px 5px 0 black, 5px 5px 0 black, -5px 0 0 black, 5px 0 0 black, 0 -5px 0 black, 0 5px 0 black, 3px 3px 6px rgba(0,0,0,0.6)",
            "background": "none",
        },
    },
    "box": {
        "label": "박스 — 반투명 배경",
        "font_name": "Arial",
        "font_size": 44,
        "primary_color": "&H00FFFFFF",
        "outline_color": "&H00000000",
        "outline_width": 0,
        "shadow": 0,
        "bold": True,
        "alignment": 2,
        "margin_v": 480,
        "border_style": 3,
        "box_highlight": True,
        "box_color": "&H80000000",
        "preview_css": {
            "color": "#FFFFFF",
            "font_size": "44px",
            "font_weight": "700",
            "text_shadow": "none",
            "background": "rgba(0,0,0,0.5)",
            "padding": "10px 28px",
            "border_radius": "8px",
        },
    },
}


def _load_user_styles() -> dict:
    """Load user-defined styles from disk."""
    if USER_STYLES_PATH.exists():
        with open(USER_STYLES_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def _save_user_styles(styles: dict) -> None:
    """Persist user-defined styles to disk."""
    USER_STYLES_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(USER_STYLES_PATH, "w", encoding="utf-8") as f:
        json.dump(styles, f, ensure_ascii=False, indent=2)


def load_style_library() -> dict:
    """Return merged dict of builtin + user styles."""
    merged = dict(BUILTIN_STYLES)
    merged.update(_load_user_styles())
    return merged


def get_style(name: str) -> dict:
    """Get a single style by name. Falls back to 'default'."""
    library = load_style_library()
    return library.get(name, library["default"])


def save_user_style(name: str, style: dict) -> Path:
    """Add or update a user-defined style and persist to disk.

    Returns path to the styles JSON file.
    """
    user_styles = _load_user_styles()
    user_styles[name] = style
    _save_user_styles(user_styles)
    return USER_STYLES_PATH


def delete_user_style(name: str) -> bool:
    """Delete a user style. Returns True if found and deleted."""
    user_styles = _load_user_styles()
    if name in user_styles:
        del user_styles[name]
        _save_user_styles(user_styles)
        return True
    return False


def list_styles_summary() -> str:
    """Return a numbered list of all styles for display in prompts.

    Example:
        1. 기본 — 흰색 아웃라인
        2. 강조 — 노란색 볼드
        3. 박스 — 반투명 배경
        4. my-custom (사용자)
    """
    library = load_style_library()
    builtin_names = set(BUILTIN_STYLES.keys())
    lines = []
    for i, (name, style) in enumerate(library.items(), 1):
        suffix = "" if name in builtin_names else " (사용자)"
        lines.append(f"{i}. {style.get('label', name)}{suffix}")
    return "\n".join(lines)


def style_to_ass_params(style: dict) -> dict:
    """Convert a style dict to kwargs for generate_ass().

    Returns only the keys that generate_ass() accepts.
    """
    return {
        "font_name": style.get("font_name", "Arial"),
        "font_size": style.get("font_size", 48),
        "primary_color": style.get("primary_color", "&H00FFFFFF"),
        "outline_color": style.get("outline_color", "&H00000000"),
        "margin_v": style.get("margin_v", 480),
        "outline_width": style.get("outline_width", 4),
        "shadow": style.get("shadow", 1),
        "bold": style.get("bold", True),
        "alignment": style.get("alignment", 2),
        "box_highlight": style.get("box_highlight", False),
        "box_color": style.get("box_color", "&H80000000"),
    }
