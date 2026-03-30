# Phase: Review -- 비용 견적 + 승인

## Step 1: 예상 비용

```bash
source .venv/bin/activate
python -c "
from src.config import check_fal_balance, estimate_narration_cost
import json

fal = check_fal_balance()
print('fal.ai:', json.dumps(fal))

# copy mode: original_content=False (STT 비용 포함)
cost = estimate_narration_cost({N_CHUNKS}, {TOTAL_DURATION}, tts_engine='google', total_chars={TOTAL_CHARS}, original_content=False)
print('Cost:', json.dumps(cost, indent=2))
"
```

```
잔액 + 예상 비용:
├── fal.ai: ${fal_balance}
├── STT (Whisper): ~${stt_cost}
├── TTS (Google Cloud): ~${tts_cost}
├── 이미지 (Flux 1.1 Pro): ~${image_cost} ({N_CHUNKS}장 x $0.06)
├── 영상 (Grok Imagine Video): ~${video_cost} ({TOTAL_DURATION}초 x $0.05)
└── 총 예상 비용: ~${total}

진행할까요? (Y/N)
```

## Step 2: 사용자 승인

승인 후 다음 Phase로 진행.

## Rules
- copy mode이므로 STT 비용 포함 (original_content=False)
- 사용자 승인 없이 다음 Phase로 넘어가지 않음
