# Phase: Video — 영상 생성

## Grok (기본)

Grok Imagine Video → Sync Lipsync v2. 모션 라이브러리 불필요.

```bash
source .venv/bin/activate
python -c "
from src.video_gen import generate_chunk_video
from src.script_gen import load_script
from pathlib import Path
import json

ref_image = Path('{PERSONA_DIR}/reference_{STYLE}.png')
persona_spec = {PERSONA_SPEC_JSON}
script = load_script(Path('{OUTPUT_DIR}'))

chunk_videos = []
for chunk in script['chunks']:
    chunk_id = chunk['chunk_id']
    audio_path = Path('{OUTPUT_DIR}/audio/{cid}_voice.wav'.format(cid=chunk_id))
    output = Path('{OUTPUT_DIR}/chunks/{cid}_video.mp4'.format(cid=chunk_id))

    print(f'Generating {chunk_id}...')
    generate_chunk_video(
        model='grok',
        face_image_path=ref_image,
        audio_path=audio_path,
        output_path=output,
        persona_spec=persona_spec,
        chunk_text=chunk.get('text', ''),
        emotion=chunk.get('emotion', ''),
    )
    chunk_videos.append({'chunk_id': chunk_id, 'video_path': str(output)})
    print(f'  {chunk_id} done')

print(json.dumps(chunk_videos, indent=2))
"
```

## Kling 2.6 (대안 — 사용자가 선택한 경우만)

Kling 2.6 Motion Control → Sync Lipsync v2. 모션 라이브러리 필수.

```bash
source .venv/bin/activate
python -c "
from src.video_gen import generate_chunk_video
from src.script_gen import load_script
from pathlib import Path
import json

ref_image = Path('{PERSONA_DIR}/reference_{STYLE}.png')
persona_spec = {PERSONA_SPEC_JSON}
script = load_script(Path('{OUTPUT_DIR}'))
chunk_text_map = {c['chunk_id']: c.get('text', '') for c in script['chunks']}

chunk_videos = []
motion_matches = {MOTION_MATCHES_JSON}

for match in motion_matches:
    chunk_id = match['chunk_id']
    motion_ref = Path(match['motion_ref_path'])
    audio_path = Path('{OUTPUT_DIR}/audio/{chunk_id}_voice.wav'.format(chunk_id=chunk_id))
    output = Path('{OUTPUT_DIR}/chunks/{chunk_id}_video.mp4'.format(chunk_id=chunk_id))

    print(f'Generating {chunk_id}...')
    generate_chunk_video(
        model='kling26',
        face_image_path=ref_image,
        audio_path=audio_path,
        output_path=output,
        prompt='Person talking to camera, upper body, natural movement',
        source_video_path=motion_ref,
        persona_spec=persona_spec,
        chunk_text=chunk_text_map.get(chunk_id, ''),
        emotion=match.get('emotion', ''),
    )
    chunk_videos.append({'chunk_id': chunk_id, 'video_path': str(output)})
    print(f'  {chunk_id} done')

print(json.dumps(chunk_videos, indent=2))
"
```

## Rules
- 기본 모델: Grok Imagine Video + Sync Lipsync v2
- Grok: 모션 라이브러리 불필요, script chunks에서 직접 순회
- Kling26: 모션 라이브러리 필수, motion_matches에서 순회
- 에러 시 해당 청크만 재시도

## Output
- {OUTPUT_DIR}/chunks/*_video.mp4
