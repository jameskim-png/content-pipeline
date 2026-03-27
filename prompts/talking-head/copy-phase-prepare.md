# Phase: Prepare — 캐릭터 이미지 + 번역 + TTS

## 1. Character Sheet + Background 생성 (새 캐릭터만)

기존 캐릭터 선택 시 스킵.

```bash
source .venv/bin/activate
python -c "
from src.persona import generate_character_sheet, generate_background, crop_front_face, save_persona_metadata
from pathlib import Path

persona_spec = {PERSONA_SPEC_JSON}
persona_name = '{PERSONA_NAME}'
background_desc = '{BACKGROUND_DESC}'

sheet_path = generate_character_sheet(persona_spec, persona_name, seed=42)
bg_path = generate_background(background_desc, persona_name, seed=42)
face_path = sheet_path.parent / 'front_face.png'
crop_front_face(sheet_path, face_path)
save_persona_metadata(persona_name, persona_spec, background_desc, {
    'character_sheet_prompt': 'auto',
    'background_prompt': 'auto',
})
print(f'Sheet: {sheet_path}')
print(f'Background: {bg_path}')
print(f'Face: {face_path}')
"
```

미리보기 + 사용자 승인 필수:
```bash
open ./personas/{PERSONA_NAME}/character_sheet.png
open ./personas/{PERSONA_NAME}/background.png
```

## 2. 번역

`build_translation_prompt()` → 직접 번역 수행. 사용자에게 결과 보여주고 확인.

## 3. 음성 생성 (Google TTS)

```bash
source .venv/bin/activate
python -c "
from src.voice import generate_chunk_voices
from src.utils import load_json
from pathlib import Path

translation = load_json(Path('{OUTPUT_DIR}/translated_script.json'))
results = generate_chunk_voices(
    translation=translation,
    output_dir=Path('{OUTPUT_DIR}/audio'),
    tts_engine='google',
    voice_name='ko-KR-Chirp3-HD-Leda',
)
for r in results:
    print(f\"  {r['chunk_id']}: {r['actual_duration']:.2f}s\")
print(f'Generated {len(results)} voice files')
"
```

## Output
- personas/{name}/ (images + metadata)
- translated_script.json
- audio/*.wav + voice_manifest.json
