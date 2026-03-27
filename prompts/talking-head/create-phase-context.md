# Phase: Context — 환경 체크 + 캐릭터 선택

## 1. 환경 체크

```bash
if [ ! -d ".venv" ]; then
    echo "First run detected. Running setup..."
    bash setup.sh
else
    source .venv/bin/activate
    python -c "import fal_client, PIL" 2>/dev/null || {
        echo "Dependencies missing. Running setup..."
        bash setup.sh
    }
fi

source .venv/bin/activate
python -c "
from dotenv import load_dotenv; import os
load_dotenv()
if not os.getenv('FAL_KEY'):
    print('MISSING_KEY: FAL_KEY')
else:
    print('ENV_OK')
"
```

## 2. 캐릭터 선택

기존 캐릭터 스캔 후 선택 또는 `/create-character` 안내:

```bash
source .venv/bin/activate
python -c "
from src.persona import list_personas
import json
personas = list_personas()
if personas:
    print('PERSONAS_FOUND')
    print(json.dumps(personas, indent=2, ensure_ascii=False))
else:
    print('NO_PERSONAS')
"
```

## 3. 콘텐츠 입력 방식

1. 제목만 입력 → AI가 스크립트 생성
2. 스크립트 직접 입력

## Output
- selected_persona (name or new)
- content_mode (title / script)
- title or raw_script
- target_duration (30/60/90초)
- subtitles (Y/N)
- bgm_path (or null)
