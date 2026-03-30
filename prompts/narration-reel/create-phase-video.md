# Phase: Video -- Grok 씬 애니메이션

## 씬 비디오 생성

각 씬 이미지를 Grok Imagine Video로 애니메이션화. lip sync 없음, 무음 클립 생성.

```bash
source .venv/bin/activate
python -c "
from src.video_gen import generate_scene_video
from src.utils import load_json, get_audio_duration
from pathlib import Path
import json, math

script = load_json(Path('{OUTPUT_DIR}/script.json'))
voice_manifest = load_json(Path('{OUTPUT_DIR}/audio/voice_manifest.json'))

# Build voice duration lookup
voice_dur_map = {v['chunk_id']: v['actual_duration'] for v in voice_manifest}

clips_dir = Path('{OUTPUT_DIR}/clips')
clips_dir.mkdir(parents=True, exist_ok=True)

scene_clips = []
for chunk in script['chunks']:
    chunk_id = chunk['chunk_id']
    image_path = Path('{OUTPUT_DIR}/images/{cid}_scene.png'.format(cid=chunk_id))
    output = clips_dir / f'{chunk_id}_clip.mp4'

    # Duration = ceil(voice + 0.5s) so clip always covers full narration
    voice_dur = voice_dur_map.get(chunk_id, chunk.get('estimated_duration', 5))
    clip_dur = max(3, min(15, math.ceil(voice_dur + 0.5)))

    prompt = chunk.get('animation_prompt', 'gentle camera movement, subtle animation')

    print(f'Generating {chunk_id} ({clip_dur}s)...')
    generate_scene_video(
        image_path=image_path,
        prompt=prompt,
        output_path=output,
        duration=clip_dur,
    )
    scene_clips.append({'chunk_id': chunk_id, 'video_path': str(output)})
    print(f'  {chunk_id} done')

print(json.dumps(scene_clips, indent=2))
"
```

## Rules
- Grok Imagine Video via fal.ai (lip sync 불필요)
- duration = voice_duration + 0.5초 (나레이션보다 약간 긴 영상)
- 최소 3초, 최대 15초 (Grok 제한)
- 720p 해상도
- animation_prompt 사용 (카메라 움직임 + 모션)
- 에러 시 해당 씬만 재시도 (skip 로직 내장)
- 출력: 무음 클립 (오디오는 Phase 6에서 오버레이)

## Output
- {OUTPUT_DIR}/clips/chunk_XXX_clip.mp4 (무음)
