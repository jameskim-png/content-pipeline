# Phase: Post -- 어셈블리 + 자막 + 타이틀

create-phase-post.md와 동일한 어셈블리 로직.

## 1. 나레이션 트랙 결합

```bash
source .venv/bin/activate
python -c "
from src.narration_stitch import concatenate_voices
from src.utils import load_json
from pathlib import Path

voice_manifest = load_json(Path('{OUTPUT_DIR}/audio/voice_manifest.json'))
narration_path = Path('{OUTPUT_DIR}/audio/narration.wav')

concatenate_voices(voice_manifest, narration_path)
print(f'Narration track: {narration_path}')

from src.utils import get_audio_duration
dur = get_audio_duration(narration_path)
print(f'Duration: {dur:.2f}s')
"
```

## 2. 씬 클립 + 나레이션 어셈블리

```bash
source .venv/bin/activate
python -c "
from src.narration_stitch import stitch_narration
from src.utils import load_json
from pathlib import Path

script = load_json(Path('{OUTPUT_DIR}/script.json'))
voice_manifest = load_json(Path('{OUTPUT_DIR}/audio/voice_manifest.json'))

scene_clips = []
for chunk in script['chunks']:
    cid = chunk['chunk_id']
    scene_clips.append({
        'chunk_id': cid,
        'video_path': str(Path('{OUTPUT_DIR}/clips/{cid}_clip.mp4'.format(cid=cid))),
    })

narration_path = Path('{OUTPUT_DIR}/audio/narration.wav')
bgm_path = Path('{BGM_PATH}') if '{BGM_PATH}' != '' else None
output_path = Path('{OUTPUT_DIR}/final.mp4')

stitch_narration(
    scene_clips=scene_clips,
    narration_path=narration_path,
    output_path=output_path,
    bgm_path=bgm_path,
    crossfade_ms=300,
    voice_manifest=voice_manifest,
)
print(f'Final video: {output_path}')
"
```

## 3. 자막 생성 (선택한 경우만)

```bash
source .venv/bin/activate
python -c "
from src.subtitles import recalculate_subtitle_timings, generate_ass
from src.subtitle_styles import get_style, style_to_ass_params
from src.utils import load_json
from pathlib import Path

voice_manifest = load_json(Path('{OUTPUT_DIR}/audio/voice_manifest.json'))
script = load_json(Path('{OUTPUT_DIR}/script.json'))

translation_chunks = [
    {
        'chunk_id': c['chunk_id'],
        'translated': c['text'],
        'original_duration': c.get('estimated_duration', 0),
    }
    for c in script['chunks']
]

subtitle_chunks = recalculate_subtitle_timings(voice_manifest, translation_chunks)

output = Path('{OUTPUT_DIR}/subtitles.ass')
style_params = style_to_ass_params(get_style('{SUBTITLE_STYLE}'))
generate_ass(subtitle_chunks, output, **style_params)
print(f'Subtitles saved: {output} ({len(subtitle_chunks)} entries)')
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
print('Subtitles burned')
"
```

## 5. 타이틀 번인 (선택한 경우)

```bash
source .venv/bin/activate
python -c "
from src.titles import burn_title
from pathlib import Path

video = Path('{OUTPUT_DIR}/final_subtitled.mp4') if Path('{OUTPUT_DIR}/final_subtitled.mp4').exists() else Path('{OUTPUT_DIR}/final.mp4')
output = Path('{OUTPUT_DIR}/final_titled.mp4')

burn_title(video, '{TITLE}', '{TITLE_PRESET}', output, duration='{TITLE_DURATION}')
print(f'Titled video: {output}')
"
```

## 6. 미리보기

```bash
open {OUTPUT_DIR}/final_titled.mp4 2>/dev/null || open {OUTPUT_DIR}/final_subtitled.mp4 2>/dev/null || open {OUTPUT_DIR}/final.mp4
```

## Output
- {OUTPUT_DIR}/audio/narration.wav
- {OUTPUT_DIR}/final.mp4
- {OUTPUT_DIR}/final_subtitled.mp4 (optional)
- {OUTPUT_DIR}/final_titled.mp4 (optional)
