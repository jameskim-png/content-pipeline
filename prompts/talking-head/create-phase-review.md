# Phase: Review — 비용 예상 + 승인

## 비용 예상

```bash
source .venv/bin/activate
python -c "
from src.config import check_fal_balance, estimate_job_cost
import json
fal = check_fal_balance()
print('fal.ai:', json.dumps(fal))
cost = estimate_job_cost('kling26', {N_CHUNKS}, {TARGET_DURATION}, tts_engine='google', total_chars={TOTAL_CHARS}, original_content=True)
print('Cost:', json.dumps(cost, indent=2))
"
```

## 요약 표시

```
설정 확인:
- 캐릭터: {persona_name} ({style})
- 스크립트: {title}, {n_chunks}개 청크, ~{duration}초
- 모델: Kling 2.6 Motion Control + Sync Lipsync v2
- TTS: Google Cloud ko-KR-Chirp3-HD-Leda

예상 비용:
├── TTS (Google Cloud): ~${tts_cost}
├── 영상 생성: ~${video_cost}
└── 총: ~${total}

진행할까요?
```

## 사용자 승인 필수

승인 후 spell 단계로 진행.
