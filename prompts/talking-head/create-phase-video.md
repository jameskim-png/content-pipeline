# Phase: Video — Kling 2.6 Motion Control + Sync Lipsync v2

## 영상 생성

각 청크에 대해 모션 레퍼런스 기반 영상 생성:

```bash
source .venv/bin/activate
python -c "
from src.video_gen import generate_chunk_video
from pathlib import Path
import json

ref_image = Path('{PERSONA_DIR}/reference_{STYLE}.png')
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
    )
    chunk_videos.append({'chunk_id': chunk_id, 'video_path': str(output)})
    print(f'  {chunk_id} done')

print(json.dumps(chunk_videos, indent=2))
"
```

## Rules
- 모델 고정: Kling 2.6 Motion Control + Sync Lipsync v2
- 모션 레퍼런스가 모션 소스 역할
- 에러 시 해당 청크만 재시도

## Output
- {OUTPUT_DIR}/chunks/*_video.mp4
