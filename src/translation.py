"""Script translation helpers.

Actual translation is done by Claude in the skill layer.
This module provides prompt templates and utilities.
"""

import json
from pathlib import Path

from .utils import save_json, load_json


TRANSLATION_PROMPT = """다음 영상 스크립트를 {target_language}로 번역해줘.

원본 스크립트:
{original_script}

캐릭터 설정:
- 말투: {speech_level}
- 톤: {voice_tone}
- 분위기: {vibe}

번역 규칙:
1. {speech_level}로 통일
2. 관용어/문화적 레퍼런스는 {target_language} 관객에 맞게 로컬라이즈
3. 각 청크의 원본 길이를 고려해서 비슷한 발화 시간이 되도록 조절
4. 문장 경계를 명확히 표시

원본 청크 정보:
{chunks_info}

다음 JSON 형식으로:
{{
  "full_script": "<전체 번역 스크립트>",
  "chunks": [
    {{
      "chunk_id": "<chunk_id>",
      "original": "<원본 텍스트>",
      "translated": "<번역 텍스트>",
      "original_duration": <초>,
      "estimated_translated_duration": <예상 초>,
      "notes": "<번역 참고사항>"
    }}
  ]
}}"""


def build_translation_prompt(
    transcript: dict,
    chunks: list[dict],
    persona_spec: dict,
    target_language: str = "한국어",
) -> str:
    """Build translation prompt for Claude.

    target_language: display name of the target language (e.g. "한국어", "日本語").
    """
    original_script = transcript.get("text", "")

    chunks_info = []
    for chunk in chunks:
        chunks_info.append(
            f"- {chunk['chunk_id']}: \"{chunk['transcript']}\" ({chunk['duration']}s)"
        )

    return TRANSLATION_PROMPT.format(
        original_script=original_script,
        speech_level=persona_spec.get("speech_level", "반말"),
        voice_tone=persona_spec.get("voice_tone", "자연스러운"),
        vibe=persona_spec.get("vibe", "friendly"),
        chunks_info="\n".join(chunks_info),
        target_language=target_language,
    )


def save_translation(output_dir: Path, translation_data: dict) -> Path:
    """Save translation result."""
    path = output_dir / "translated_script.json"
    save_json(translation_data, path)
    return path


def load_translation(output_dir: Path) -> dict:
    """Load translation from disk."""
    return load_json(output_dir / "translated_script.json")
