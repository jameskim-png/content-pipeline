# Phase: Generate — 영상 생성 (Kling 2.6 + Sync Lipsync v2)

원본 영상이 모션 소스 역할. 각 청크의 원본 비디오를 source_video_path로 전달:

```bash
source .venv/bin/activate
python -c "
from src.video_gen import generate_chunk_video
from pathlib import Path
import json

face_path = Path('./personas/{PERSONA_NAME}/front_face.png')
bg_path = Path('./personas/{PERSONA_NAME}/background.png')

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
    )
    chunk_videos.append({'chunk_id': cid, 'video_path': str(out)})
    print(f'  {cid} done')

print(json.dumps(chunk_videos, indent=2))
"
```

## Rules
- 모델 고정: Kling 2.6 Motion Control + Sync Lipsync v2
- 원본 비디오 = 모션 소스
- 에러 시 해당 청크만 재시도
- bg removal 절대 금지

## Output
- {OUTPUT_DIR}/chunks/*_video.mp4
