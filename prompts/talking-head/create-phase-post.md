# Phase: Post — 오디오 믹싱 + 자막 + 스티칭

## 1. 오디오 믹싱

```bash
source .venv/bin/activate
python -c "
from src.audio_mixing import mix_all_chunks
from src.script_gen import load_script
from pathlib import Path

script = load_script(Path('{OUTPUT_DIR}'))
voice_dir = Path('{OUTPUT_DIR}/audio')
audio_out = Path('{OUTPUT_DIR}/audio')
bgm_path = Path('{BGM_PATH}') if '{BGM_PATH}' != '' else None

results = mix_all_chunks(voice_dir, audio_out, script['chunks'], bgm_path)
print(f'Mixed {len(results)} audio files')
"
```

## 2. 자막 생성 (선택한 경우만)

```bash
source .venv/bin/activate
python -c "
from src.subtitles import recalculate_subtitle_timings, generate_ass
from src.utils import load_json
from src.script_gen import load_script, script_to_translation_format
from pathlib import Path

voice_manifest = load_json(Path('{OUTPUT_DIR}/audio/voice_manifest.json'))
script = load_script(Path('{OUTPUT_DIR}'))
translation = script_to_translation_format(script)
subtitle_chunks = recalculate_subtitle_timings(voice_manifest, translation['chunks'])
output = Path('{OUTPUT_DIR}/subtitles.ass')
generate_ass(subtitle_chunks, output)
print(f'Subtitles saved: {output} ({len(subtitle_chunks)} entries)')
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

## 5. 미리보기 + 리포트

```bash
open {OUTPUT_DIR}/final.mp4
```

## Output
- {OUTPUT_DIR}/final.mp4
- {OUTPUT_DIR}/final_subtitled.mp4 (optional)
