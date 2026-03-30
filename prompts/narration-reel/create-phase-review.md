# Phase: Review -- 비용 견적 + 승인

TTS 전에 실행. 스크립트 검증 + 비용 확인 + 사용자 승인.

## Step 1: 스크립트 검증

```bash
source .venv/bin/activate
python -c "
from src.utils import load_json
from pathlib import Path
import json

script = load_json(Path('{OUTPUT_DIR}/script.json'))

errors = []
if not script.get('style_prompt'):
    errors.append('style_prompt is missing')
if not script.get('chunks'):
    errors.append('chunks list is empty')

for i, chunk in enumerate(script.get('chunks', [])):
    cid = chunk.get('chunk_id', f'chunk_{i}')
    if not chunk.get('text'):
        errors.append(f'{cid}: text is missing')
    if not chunk.get('scene_description'):
        errors.append(f'{cid}: scene_description is missing')
    if not chunk.get('animation_prompt'):
        errors.append(f'{cid}: animation_prompt is missing')
    dur = chunk.get('estimated_duration', 0)
    if dur < 1 or dur > 15:
        errors.append(f'{cid}: duration {dur}s out of range (1-15s)')

if errors:
    print('VALIDATION_ERRORS:')
    for e in errors:
        print(f'  - {e}')
else:
    print('VALID')
    print(f'Chunks: {len(script[\"chunks\"])}')
    total_dur = sum(c.get(\"estimated_duration\", 0) for c in script[\"chunks\"])
    print(f'Total duration: {total_dur:.1f}s')
"
```

## Step 2: Chunk 테이블 표시

```
Pre-generation Review:

| # | chunk_id | duration | 나레이션 (앞 30자) | 씬 (앞 40자) |
|---|----------|----------|-------------------|-------------|
| 1 | chunk_001 | 4.0s | "냉장고 속 음식을..." | A colorful open refri... |
| 2 | chunk_002 | 5.2s | "첫 번째 NG 습관은..." | Person placing hot so... |
...
```

## Step 3: 비용 견적

```bash
source .venv/bin/activate
python -c "
from src.config import check_fal_balance, estimate_narration_cost
import json

fal = check_fal_balance()
print('fal.ai:', json.dumps(fal))

cost = estimate_narration_cost({N_CHUNKS}, {TOTAL_DURATION}, tts_engine='google', total_chars={TOTAL_CHARS}, original_content=True)
print('Cost:', json.dumps(cost, indent=2))
"
```

```
잔액 + 예상 비용:
├── fal.ai: ${fal_balance}
├── TTS (Google Cloud): ~${tts_cost}
├── 이미지 (Flux 1.1 Pro): ~${image_cost} ({N_CHUNKS}장 x $0.06)
├── 영상 (Grok Imagine Video): ~${video_cost} ({TOTAL_DURATION}초 x $0.05)
└── 총 예상 비용: ~${total}

진행할까요? (Y/N)
```

## Step 4: 사용자 승인

승인 후 다음 Phase로 진행.

## Rules
- TTS 전에 반드시 실행
- 사용자 승인 없이 다음 Phase로 넘어가지 않음
- 에러가 있으면 Phase 1로 돌아가서 수정
