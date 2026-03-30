# Phase: Images -- Flux 씬 이미지 생성

## 씬 이미지 생성

스크립트의 style_prompt + 각 청크의 scene_description으로 이미지 생성.

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

total_cost = sum(r.get('cost', 0) for r in results)
print(f'Image cost: ~${total_cost:.2f}')
"
```

## 이미지 확인

생성된 이미지 미리보기:

```bash
open {OUTPUT_DIR}/images/
```

```
씬 이미지 생성 완료! ({n_images}장)

미리보기를 확인해주세요.

문제 있는 씬이 있나요?
1. 모두 OK -> 다음 Phase로
2. 특정 씬 재생성 -> 씬 번호 입력
```

### 씬 재생성

사용자가 특정 씬을 다시 생성하고 싶을 때:

```bash
source .venv/bin/activate
python -c "
from src.image_gen import flux_generate_image
from src.utils import load_json
from pathlib import Path

script = load_json(Path('{OUTPUT_DIR}/script.json'))
chunk = script['chunks'][{CHUNK_INDEX}]
style = script.get('style_prompt', '')
prompt = f\"{style}. {chunk['scene_description']}\"

output = Path('{OUTPUT_DIR}/images/{CHUNK_ID}_scene.png')
output.unlink(missing_ok=True)  # 기존 파일 삭제

flux_generate_image(prompt, output)
print(f'Regenerated: {output}')
"
```

```bash
open {OUTPUT_DIR}/images/{CHUNK_ID}_scene.png
```

## Rules
- FLUX.2 Pro via fal.ai
- 720x1280 (9:16 세로형)
- style_prompt + scene_description 결합
- 기존 파일은 자동 스킵 (idempotent)
- 재생성 시 기존 파일 삭제 후 재생성

## Output
- {OUTPUT_DIR}/images/chunk_XXX_scene.png
