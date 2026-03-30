# Phase: Prepare -- 번역 + TTS

## 1. 번역 (필요시)

원본 언어와 대상 언어가 다른 경우 번역 수행.

```bash
source .venv/bin/activate
python -c "
from src.translation import build_translation_prompt
from src.languages import get_language_config
import json

config = get_language_config('{LANG_CODE}')
transcript = {'text': '''{FULL_SCRIPT}'''}
chunks = {CHUNKS_FOR_TRANSLATION_JSON}
prompt = build_translation_prompt(transcript, chunks, {}, target_language=config['label'])
print(prompt)
"
```

이 프롬프트로 **직접** 번역 수행.

번역 시 주의:
- `scene_description`과 `animation_prompt`는 영어 그대로 유지 (Flux/Grok 프롬프트)
- 나레이션 `text`만 대상 언어로 번역

**사용자에게 번역 결과 보여주고 수정 여부 확인:**
```
번역 결과:

chunk_001 ({duration}s):
  원본: "{original_text}"
  번역: "{translated_text}"

chunk_002 ({duration}s):
  ...

수정할 부분이 있나요? (없으면 Enter)
```

번역 후 스크립트의 text 필드 업데이트 -> 저장.

## 2. TTS 생성

```bash
source .venv/bin/activate
python -c "
from src.voice import generate_chunk_voices
from src.utils import load_json
from pathlib import Path

script = load_json(Path('{OUTPUT_DIR}/script.json'))

translation = {
    'full_script': script.get('full_script', ''),
    'chunks': [
        {
            'chunk_id': c['chunk_id'],
            'translated': c['text'],
            'original_duration': c.get('estimated_duration', 0),
        }
        for c in script['chunks']
    ],
}

results = generate_chunk_voices(
    translation=translation,
    output_dir=Path('{OUTPUT_DIR}/audio'),
    tts_engine='google',
    voice_name='{VOICE_NAME}',
)
for r in results:
    print(f\"  {r['chunk_id']}: {r['actual_duration']:.2f}s\")
print(f'Generated {len(results)} voice files')
"
```

## Output
- Updated script.json (translated text)
- {OUTPUT_DIR}/audio/*.wav
- {OUTPUT_DIR}/audio/voice_manifest.json
