"""Script generation helpers for original content.

Provides prompt templates and utilities for generating scripts from scratch.
Actual LLM calls happen in the skill layer (the .md commands).
"""

import json
from pathlib import Path

from .config import EMOTION_CATEGORIES
from .utils import save_json, load_json


SCRIPT_GENERATION_PROMPT = """다음 캐릭터로 쇼츠/릴스 스크립트를 작성해줘.

제목/주제: {title}
목표 길이: ~{target_duration}초

캐릭터 설정:
- 말투: {speech_level}
- 톤: {voice_tone}
- 분위기: {vibe}

스크립트 규칙:
1. {speech_level}로 일관성 유지
2. 목표 길이에 맞게 청크 분할 (1청크 = 3~8초 분량)
3. 각 청크에 감정 태그 부여 (아래 목록에서 선택)
4. 도입-전개-마무리 구조
5. 릴스/쇼츠에 맞게 강한 첫 문장 (hook)
6. {target_language} 자연스러운 구어체

감정 태그 목록: {emotions}

다음 JSON 형식으로:
{{
  "title": "<제목>",
  "full_script": "<전체 스크립트 (연결된 텍스트)>",
  "target_duration": {target_duration},
  "chunks": [
    {{
      "chunk_id": "chunk_001",
      "text": "<이 청크의 대사>",
      "estimated_duration": <예상 초>,
      "emotion": "<감정 태그>",
      "notes": "<연기/톤 참고>"
    }}
  ]
}}"""


SCRIPT_REVISION_PROMPT = """현재 스크립트를 수정해줘.

현재 스크립트:
{current_script}

수정 요청:
{revision_request}

감정 태그 목록: {emotions}

같은 JSON 형식으로 수정된 결과를 반환해:
{{
  "title": "<제목>",
  "full_script": "<전체 스크립트>",
  "target_duration": <목표 초>,
  "chunks": [
    {{
      "chunk_id": "chunk_001",
      "text": "<대사>",
      "estimated_duration": <예상 초>,
      "emotion": "<감정 태그>",
      "notes": "<참고>"
    }}
  ]
}}"""


def build_script_generation_prompt(
    persona_spec: dict,
    title: str,
    target_duration: int = 30,
    target_language: str = "한국어",
) -> str:
    """Build prompt for Claude to generate a script from scratch.

    Uses persona voice_tone/speech_level/vibe for consistent character voice.
    target_language: display name of the language (e.g. "한국어", "日本語", "English").
    """
    return SCRIPT_GENERATION_PROMPT.format(
        title=title,
        target_duration=target_duration,
        speech_level=persona_spec.get("speech_level", "반말"),
        voice_tone=persona_spec.get("voice_tone", "자연스러운"),
        vibe=persona_spec.get("vibe", "friendly"),
        emotions=", ".join(EMOTION_CATEGORIES),
        target_language=target_language,
    )


def build_script_revision_prompt(
    current_script: dict,
    revision_request: str,
) -> str:
    """Build prompt for Claude to revise an existing script."""
    return SCRIPT_REVISION_PROMPT.format(
        current_script=json.dumps(current_script, ensure_ascii=False, indent=2),
        revision_request=revision_request,
        emotions=", ".join(EMOTION_CATEGORIES),
    )


def validate_script(script: dict) -> list[str]:
    """Validate script structure. Returns list of errors (empty = valid)."""
    errors = []

    if not script.get("full_script"):
        errors.append("full_script is missing or empty")

    chunks = script.get("chunks", [])
    if not chunks:
        errors.append("chunks list is empty")

    for i, chunk in enumerate(chunks):
        chunk_id = chunk.get("chunk_id", f"chunk_{i}")

        if not chunk.get("text"):
            errors.append(f"{chunk_id}: text is missing or empty")

        if not chunk.get("estimated_duration"):
            errors.append(f"{chunk_id}: estimated_duration is missing")

        emotion = chunk.get("emotion", "")
        if emotion and emotion not in EMOTION_CATEGORIES:
            errors.append(f"{chunk_id}: unknown emotion '{emotion}' (valid: {', '.join(EMOTION_CATEGORIES)})")

    return errors


def save_script(output_dir: Path, script_data: dict) -> Path:
    """Save generated script."""
    path = output_dir / "script.json"
    save_json(script_data, path)
    return path


def load_script(output_dir: Path) -> dict:
    """Load script from disk."""
    return load_json(output_dir / "script.json")


def script_to_translation_format(script: dict) -> dict:
    """Convert script format to the format expected by generate_chunk_voices().

    Bridge: script chunk["text"] -> translation chunk["translated"]
    so that voice.generate_chunk_voices() can consume it directly.
    """
    translated_chunks = []
    for chunk in script.get("chunks", []):
        translated_chunks.append({
            "chunk_id": chunk["chunk_id"],
            "translated": chunk["text"],
            "original_duration": chunk.get("estimated_duration", 0),
            "emotion": chunk.get("emotion", "neutral"),
        })

    return {
        "full_script": script.get("full_script", ""),
        "chunks": translated_chunks,
    }
