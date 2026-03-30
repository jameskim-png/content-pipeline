# Phase: Audio — TTS 음성 생성

## Google Cloud TTS

스크립트를 translation 포맷으로 변환 후 음성 생성:

```bash
source .venv/bin/activate
python -c "
from src.script_gen import script_to_translation_format, load_script
from src.voice import generate_chunk_voices
from pathlib import Path

script = load_script(Path('{OUTPUT_DIR}'))
translation = script_to_translation_format(script)

audio_dir = Path('{OUTPUT_DIR}/audio')
results = generate_chunk_voices(
    translation=translation,
    output_dir=audio_dir,
    tts_engine='google',
    voice_name='{VOICE_NAME}',
)
for r in results:
    print(f\"  {r['chunk_id']}: {r['actual_duration']:.2f}s\")
print(f'Generated {len(results)} voice files')
"
```

## Rules
- TTS 엔진 고정: Chirp3-HD. 음성은 언어에 따라 자동 결정 (`{VOICE_NAME}`)
- `script_to_translation_format()` 브릿지 필수
- 기존 파일은 자동 스킵

## Output
- {OUTPUT_DIR}/audio/*.wav
- {OUTPUT_DIR}/audio/voice_manifest.json
