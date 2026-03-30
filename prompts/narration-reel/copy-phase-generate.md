# Phase: Generate -- 이미지 생성 + 애니메이션

## 1. 씬 이미지 생성

```bash
source .venv/bin/activate
python -c "
from src.image_gen import generate_scene_images
from src.utils import load_json
from pathlib import Path
import json

script = load_json(Path('{OUTPUT_DIR}/script.json'))
images_dir = Path('{OUTPUT_DIR}/images')

results = generate_scene_images(script, images_dir)
print(json.dumps(results, indent=2))
print(f'Generated {len(results)} scene images')
"
```

이미지 확인:
```bash
open {OUTPUT_DIR}/images/
```

문제 있는 씬이 있으면 재생성 (create-phase-images.md 참조).

## 2. 씬 애니메이션

```bash
source .venv/bin/activate
python -c "
from src.video_gen import generate_scene_video
from src.utils import load_json, get_audio_duration
from pathlib import Path
import json, math

script = load_json(Path('{OUTPUT_DIR}/script.json'))
voice_manifest = load_json(Path('{OUTPUT_DIR}/audio/voice_manifest.json'))

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
- 이미지: FLUX.2 Pro, 720x1280
- 비디오: Grok Imagine Video, 720p, lip sync 없음
- duration = voice_duration + 0.5초
- 에러 시 해당 씬만 재시도 (skip 로직 내장)

## Output
- {OUTPUT_DIR}/images/chunk_XXX_scene.png
- {OUTPUT_DIR}/clips/chunk_XXX_clip.mp4 (무음)
