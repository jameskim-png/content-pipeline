# 캐릭터 목록 조회

기존 캐릭터를 확인하고 상세 정보를 볼 수 있는 뷰어.

---

## Step 1: 캐릭터 스캔

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

---

## Step 2: 결과 표시

### 캐릭터가 있으면

```
등록된 캐릭터 목록:

{번호}. {name} — {gender}, {age_range}, {vibe} [스타일: {style}]
   배경: {background_desc}
   생성일: {created_at}
```

각 캐릭터의 레퍼런스 이미지 경로도 함께 표시:
```
   이미지: personas/{name}/reference_{style}.png
```

### 캐릭터가 없으면

```
등록된 캐릭터가 없습니다.
캐릭터 관리 → 새로 만들기를 선택해주세요!
```

---

## Step 3: 상세 보기 (선택)

사용자가 특정 캐릭터를 선택하면:

```bash
source .venv/bin/activate
python -c "
from src.persona import load_persona
import json
persona = load_persona('{PERSONA_NAME}')
print(json.dumps(persona, indent=2, ensure_ascii=False))
"
```

레퍼런스 이미지 미리보기:
```bash
open ./personas/{PERSONA_NAME}/reference_{STYLE}.png
```

상세 정보 표시:
```
캐릭터 상세: {name}

이름: {name}
성별: {gender}
나이대: {age_range}
외모: {visual_traits}
의상: {clothing}
머리: {hair}
말투: {speech_level}
분위기: {vibe}
배경: {background_desc}
스타일: {style}

이미지: personas/{name}/reference_{style}.png
```
