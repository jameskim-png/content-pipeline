"""Language configuration for multi-language content pipeline.

Maps language codes to locale, default voice name (Google Chirp3-HD),
and display labels. Chirp3-HD uses the same voice name across locales —
only the locale prefix changes.
"""

SUPPORTED_LANGUAGES = {
    "ko": {"label": "한국어", "locale": "ko-KR", "default_voice": "ko-KR-Chirp3-HD-Leda"},
    "ja": {"label": "日本語", "locale": "ja-JP", "default_voice": "ja-JP-Chirp3-HD-Leda"},
    "en": {"label": "English", "locale": "en-US", "default_voice": "en-US-Chirp3-HD-Leda"},
    "cmn": {"label": "中文", "locale": "cmn-CN", "default_voice": "cmn-CN-Chirp3-HD-Leda"},
    "es": {"label": "Español", "locale": "es-ES", "default_voice": "es-ES-Chirp3-HD-Leda"},
}

DEFAULT_LANGUAGE = "ko"


def get_language_config(lang_code: str = DEFAULT_LANGUAGE) -> dict:
    """Get full language config dict for a language code.

    Returns dict with keys: label, locale, default_voice.
    Falls back to Korean if code not found.
    """
    return SUPPORTED_LANGUAGES.get(lang_code, SUPPORTED_LANGUAGES[DEFAULT_LANGUAGE])


def get_voice_name(lang_code: str = DEFAULT_LANGUAGE) -> str:
    """Get the Google Chirp3-HD voice name for a language code.

    >>> get_voice_name('ja')
    'ja-JP-Chirp3-HD-Leda'
    """
    return get_language_config(lang_code)["default_voice"]


def list_languages_summary() -> str:
    """Return a numbered list of supported languages for display in prompts.

    Example output:
        1. 한국어 (기본)
        2. 日本語
        3. English
        4. 中文
        5. Español
    """
    lines = []
    for i, (code, cfg) in enumerate(SUPPORTED_LANGUAGES.items(), 1):
        suffix = " (기본)" if code == DEFAULT_LANGUAGE else ""
        lines.append(f"{i}. {cfg['label']}{suffix}")
    return "\n".join(lines)


def language_code_from_index(index: int) -> str:
    """Convert 1-based menu index to language code.

    >>> language_code_from_index(2)
    'ja'
    """
    codes = list(SUPPORTED_LANGUAGES.keys())
    if 1 <= index <= len(codes):
        return codes[index - 1]
    return DEFAULT_LANGUAGE
