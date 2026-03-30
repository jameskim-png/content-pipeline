# Phase: Generate — 영상 생성

## Grok (기본)

Grok Imagine Video → Sync Lipsync v2:

```bash
source .venv/bin/activate
python -c "
from src.video_gen import generate_chunk_video
from pathlib import Path
import json

ref_image = Path('./personas/{PERSONA_NAME}/reference_{STYLE}.png')
persona_spec = {PERSONA_SPEC_JSON}

chunk_videos = []
chunks = {CHUNKS_JSON}
for chunk in chunks:
    cid = chunk['chunk_id']
    audio = Path('{OUTPUT_DIR}/audio/' + cid + '_voice.wav')
    out = Path('{OUTPUT_DIR}/chunks/' + cid + '_video.mp4')

    generate_chunk_video(
        model='grok',
        face_image_path=ref_image,
        audio_path=audio,
        output_path=out,
        persona_spec=persona_spec,
        chunk_text=chunk.get('text', ''),
        emotion=chunk.get('emotion', ''),
    )
    chunk_videos.append({'chunk_id': cid, 'video_path': str(out)})
    print(f'  {cid} done')

print(json.dumps(chunk_videos, indent=2))
"
```

## Kling 2.6 (사용자가 선택한 경우)

원본 영상이 모션 소스 역할:

```bash
source .venv/bin/activate
python -c "
from src.video_gen import generate_chunk_video
from pathlib import Path
import json

face_path = Path('./personas/{PERSONA_NAME}/front_face.png')
bg_path = Path('./personas/{PERSONA_NAME}/background.png')
persona_spec = {PERSONA_SPEC_JSON}

chunk_videos = []
chunks = {CHUNKS_JSON}
for chunk in chunks:
    cid = chunk['chunk_id']
    audio = Path('{OUTPUT_DIR}/audio/' + cid + '_voice.wav')
    out = Path('{OUTPUT_DIR}/chunks/' + cid + '_video.mp4')
    source_video = Path('{VIDEO_DIR}/chunks/' + cid + '/video.mp4')
    generate_chunk_video(
        model='kling26',
        face_image_path=face_path,
        audio_path=audio,
        output_path=out,
        background_path=bg_path,
        source_video_path=source_video,
        persona_spec=persona_spec,
        chunk_text=chunk.get('text', ''),
        emotion=chunk.get('emotion', ''),
    )
    chunk_videos.append({'chunk_id': cid, 'video_path': str(out)})
    print(f'  {cid} done')

print(json.dumps(chunk_videos, indent=2))
"
```

## Rules
- 기본 모델: Grok Imagine Video + Sync Lipsync v2
- Grok: 모션 소스 불필요, reference image에서 직접 생성
- Kling26: 원본 비디오 = 모션 소스
- 에러 시 해당 청크만 재시도
- bg removal 절대 금지

## Output
- {OUTPUT_DIR}/chunks/*_video.mp4
