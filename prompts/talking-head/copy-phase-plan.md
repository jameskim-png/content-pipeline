# Phase: Plan — 캐릭터 선택 + 번역 계획

## 1. 캐릭터 선택

기존 캐릭터 스캔:

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

- 기존 캐릭터 선택 → load_persona()
- 새로 만들기 → persona spec 구조화 + 배경 설명

## 2. 설정 수집

- 자막 포함 여부 (기본: Y)
- BGM 옵션 (원본 매칭 / 없음)

## 3. 설정 요약

```
설정 확인:
- 소스: {URL} ({COUNT}개 영상)
- 캐릭터: {PERSONA_NAME}
- 모델: Kling 2.6 Motion Control + Sync Lipsync v2 (고정)
- TTS: Google Cloud {VOICE_NAME}
- 언어: {LANGUAGE_LABEL}
- 자막: {Y/N}
- BGM: {option}
```

## Output
- selected persona spec
- subtitle/bgm preferences
