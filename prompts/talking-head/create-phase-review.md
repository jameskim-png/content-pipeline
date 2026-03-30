# Phase: Pre-generation Review

TTS 전에 실행. 분할/병합 후 TTS가 올바른 chunks로 생성되도록 보장.

## Step 1: review_chunks() 호출

```bash
source .venv/bin/activate
python -c "
from src.review import review_chunks
from src.script_gen import load_script
from pathlib import Path
import json

script = load_script(Path('{OUTPUT_DIR}'))
persona_spec = {PERSONA_SPEC_JSON}

result = review_chunks(script['chunks'], persona_spec=persona_spec, model='{MODEL}')
print(json.dumps(result, indent=2, ensure_ascii=False))
"
```

## Step 2: 결과 표시

### 변경 리포트

```
Pre-generation Review 결과:

변경 사항:
{report 항목들 - duration 재계산, split, merge, emotion remap, renumber}

경고:
{warnings 항목들 - 남아있는 이슈}
```

### Chunk 테이블

```
| # | chunk_id | emotion | duration | text (앞 30자) |
|---|----------|---------|----------|----------------|
| 1 | chunk_001 | happy | 5.2s | "안녕 여러분..." |
| 2 | chunk_002 | explaining | 8.3s | "오늘은 이..." |
...
```

### 프롬프트 미리보기

```
chunk_001 [{MODEL}]:
  "{prompt_preview}"

chunk_002 [{MODEL}]:
  "{prompt_preview}"
...
```

### 비용 예상

```bash
source .venv/bin/activate
python -c "
from src.config import check_fal_balance
import json
fal = check_fal_balance()
print('fal.ai:', json.dumps(fal))
"
```

```
잔액 + 예상 비용:
├── fal.ai: ${fal_balance}
├── TTS (Google Cloud): ~${tts_cost}
├── 영상 생성 ({MODEL_LABEL}): ~${video_cost}
├── 이미지: ~${image_cost}
└── 총 예상 비용: ~${total}

진행할까요? (Y/N)
```

## Step 3: 사용자 승인

승인 후 → reviewed chunks를 script.json에 저장:

```bash
source .venv/bin/activate
python -c "
from src.script_gen import save_script
from pathlib import Path
import json

reviewed_chunks = {REVIEWED_CHUNKS_JSON}
script = {
    'title': '{TITLE}',
    'full_script': '{FULL_SCRIPT}',
    'target_duration': {TARGET_DURATION},
    'chunks': reviewed_chunks,
}
path = save_script(Path('{OUTPUT_DIR}'), script)
print(f'Reviewed script saved: {path}')
"
```

## Rules
- TTS 전에 반드시 실행
- 사용자 승인 없이 다음 Phase로 넘어가지 않음
- warnings가 있으면 사용자에게 명시적으로 알림
- reviewed chunks가 저장된 후 TTS Phase로 진행
