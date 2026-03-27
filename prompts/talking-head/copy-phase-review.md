# Phase: Review — 비용 예상 + 승인

## API 검증 + 잔액

```bash
source .venv/bin/activate
python -c "
from src.config import validate_keys, check_fal_balance, estimate_job_cost
import json

keys = validate_keys('kling26')
print('API Keys OK:')
for k, v in keys.items():
    print(f'  {k}: {v[:8]}...')

fal = check_fal_balance()
print('fal.ai:', json.dumps(fal))

cost = estimate_job_cost('kling26', {N_CHUNKS}, {TOTAL_DURATION})
print('Cost:', json.dumps(cost, indent=2))
"
```

## 비용 표시

```
API 잔액:
└── fal.ai: ${balance} USD

예상 비용:
├── STT: ~${stt}
├── TTS (Google Cloud): ~${tts}
├── 영상 생성 (Kling 2.6 + Sync Lipsync): ~${video}
└── 총: ~${total}

진행할까요?
```

## 사용자 승인 필수

승인 후 spell 단계로 진행.
