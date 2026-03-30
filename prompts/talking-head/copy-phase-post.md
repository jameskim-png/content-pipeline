# Phase: Post — 오디오 믹싱 + 자막 + 스티칭 + 메타데이터

## 1. 오디오 믹싱

```bash
source .venv/bin/activate
python -c "
from src.audio_mixing import mix_all_chunks
from pathlib import Path
results = mix_all_chunks(
    voice_dir=Path('{OUTPUT_DIR}/audio'),
    output_dir=Path('{OUTPUT_DIR}/audio'),
    chunks={CHUNKS_JSON},
    bgm_path={BGM_PATH_OR_NONE},
)
print(f'Mixed {len(results)} files')
"
```

## 2. 자막 생성 (선택한 경우)

```bash
source .venv/bin/activate
python -c "
from src.subtitles import recalculate_subtitle_timings, generate_ass
from src.utils import load_json
from pathlib import Path
voice_manifest = load_json(Path('{OUTPUT_DIR}/audio/voice_manifest.json'))
translation = load_json(Path('{OUTPUT_DIR}/translated_script.json'))
subtitle_chunks = recalculate_subtitle_timings(voice_manifest, translation['chunks'])

from src.subtitle_styles import get_style, style_to_ass_params
style_params = style_to_ass_params(get_style('{SUBTITLE_STYLE}'))
generate_ass(subtitle_chunks, Path('{OUTPUT_DIR}/subtitles.ass'), **style_params)
print(f'Subtitles generated with {len(subtitle_chunks)} entries')
"
```

## 3. 최종 스티칭

```bash
source .venv/bin/activate
python -c "
from src.stitching import stitch_chunks
from pathlib import Path
stitch_chunks(
    chunk_videos={CHUNK_VIDEOS_JSON},
    mixed_audios={MIXED_AUDIOS_JSON},
    output_path=Path('{OUTPUT_DIR}/final.mp4'),
)
print('Stitching complete!')
"
```

## 4. 자막 번인 (선택한 경우)

```bash
source .venv/bin/activate
python -c "
from src.subtitles import burn_subtitles
from pathlib import Path
burn_subtitles(
    Path('{OUTPUT_DIR}/final.mp4'),
    Path('{OUTPUT_DIR}/subtitles.ass'),
    Path('{OUTPUT_DIR}/final_subtitled.mp4'),
)
"
```

## 5. 메타데이터 저장

```bash
source .venv/bin/activate
python -c "
from src.persona import save_persona_metadata
save_persona_metadata(
    '{PERSONA_NAME}',
    {PERSONA_SPEC_JSON},
    '{BACKGROUND_DESC}',
    {'character_sheet_prompt': 'auto', 'background_prompt': 'auto'},
    video_model='{MODEL}',
    tts_engine='google',
)
print('Metadata saved')
"
```

## 6. 미리보기 + 리포트

```bash
open {OUTPUT_DIR}/final.mp4
```

## Output
- {OUTPUT_DIR}/final.mp4
- {OUTPUT_DIR}/final_subtitled.mp4 (optional)
- Updated persona metadata
