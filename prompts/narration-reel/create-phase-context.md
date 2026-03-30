# Phase: Context -- 환경 체크 + 스타일 선택

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

## 2. 주제 입력

사용자로부터 나레이션 릴스 주제/제목 입력받기.

## 3. 시각 스타일 선택

프리셋 또는 커스텀 스타일 입력 -> `STYLE_PROMPT` 변수 설정.

## 4. 목표 길이 + 언어 + 자막/타이틀/BGM 설정

create.md의 Q3~Q7 순서대로 수집.

## Output
- title (주제/제목)
- style_prompt (영어 스타일 프롬프트)
- target_duration (30/60/90초)
- lang_code, voice_name, language_label
- subtitles (Y/N), subtitle_style
- title_preset, title_duration
- bgm_path (or null)
