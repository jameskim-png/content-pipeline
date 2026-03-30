# Phase: Audio -- TTS 나레이션 생성

## Google Cloud TTS

스크립트의 나레이션 텍스트로 음성 생성. 기존 voice 모듈을 그대로 재사용.

나레이션 릴스 스크립트를 translation 포맷으로 변환 후 음성 생성:

```bash
source .venv/bin/activate
python -c "
from src.voice import generate_chunk_voices
from src.utils import load_json
from pathlib import Path

script = load_json(Path('{OUTPUT_DIR}/script.json'))

# Narration reel script -> translation format bridge
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
- TTS 엔진 고정: Chirp3-HD. 음성은 언어에 따라 자동 결정
- 기존 파일은 자동 스킵
- voice_manifest.json이 audio 디렉토리에 저장됨

## Output
- {OUTPUT_DIR}/audio/*.wav
- {OUTPUT_DIR}/audio/voice_manifest.json
