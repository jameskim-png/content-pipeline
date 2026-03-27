# 캐릭터 생성

레퍼런스 이미지 + 메타데이터를 생성하여 콘텐츠 파이프라인에서 재사용.

---

## Phase 1: 사용자 입력

### Q1. 캐릭터 설명 (자유 텍스트)

```
영상에 등장할 캐릭터를 설명해주세요. 자유롭게 써주시면 됩니다!

예시:
- "아이언맨"
- "차분한 30대 여성 교수"
- "갓생 실패 전문가 — 부스스한 머리, 귀여운 잠옷, 반말"
- "이 인스타 계정의 사람처럼: [URL]"
```

입력을 받으면 `build_persona_parse_prompt()`로 구조화:

```python
from src.persona import build_persona_parse_prompt
prompt = build_persona_parse_prompt(user_input)
```

이 프롬프트로 **직접** persona spec JSON을 생성. 빠진 필드가 있으면 추가 질문:

```
캐릭터를 이렇게 이해했어요:

이름: {name}
성별: {gender}
나이대: {age_range}
외모: {visual_traits}
의상: {clothing}
머리: {hair}
말투: {speech_level}
분위기: {vibe}

추가로 확인할게 있어요:
- {missing_field_question_1}
- {missing_field_question_2}
```

사용자 답변 반영 후 최종 spec 확인.

### Q2. 배경 설명

```
이 캐릭터가 영상에서 어디에 있으면 좋을까요?

예시:
- "어수선한 원룸"
- "깔끔한 스튜디오"
- "카페"
- "네온 게이밍 룸"
```

### Q3. 스타일

```
캐릭터 스타일을 선택해주세요:

1. real (실사, 추천)
2. anime (애니메이션)
3. 3d (3D 렌더링)
```

---

## Phase 2: 레퍼런스 이미지 생성

`generate_reference_image()` 사용. **character_sheet 방식이 아님**. bg removal 절대 X.

```bash
source .venv/bin/activate
python -c "
from src.persona import generate_reference_image
from pathlib import Path

persona_spec = {PERSONA_SPEC_JSON}
persona_name = '{PERSONA_NAME}'
background_desc = '{BACKGROUND_DESC}'
style = '{STYLE}'

ref_path = generate_reference_image(
    persona_spec=persona_spec,
    persona_name=persona_name,
    background_desc=background_desc,
    style=style,
    seed=42,
)
print(f'Reference image: {ref_path}')
"
```

### 미리보기

```bash
open ./personas/{PERSONA_NAME}/reference_{STYLE}.png
```

### 사용자 승인

```
레퍼런스 이미지가 생성되었습니다!
미리보기 창에서 확인해주세요!

1. OK → 진행
2. 재생성 (다른 시드로)
3. 프롬프트 수정 후 재생성
```

재생성 시 시드를 변경 (seed=43, 44, ...):

```python
ref_path = generate_reference_image(
    persona_spec=persona_spec,
    persona_name=persona_name,
    background_desc=background_desc,
    style=style,
    seed={NEW_SEED},
)
```

승인 받을 때까지 반복.

---

## Phase 3: 메타데이터 저장

```bash
source .venv/bin/activate
python -c "
from src.persona import save_persona_metadata

save_persona_metadata(
    '{PERSONA_NAME}',
    {PERSONA_SPEC_JSON},
    '{BACKGROUND_DESC}',
    {'reference_prompt': 'auto'},
    style='{STYLE}',
)
print('Metadata saved')
"
```

---

## Phase 4: 결과 리포트

```
캐릭터 생성 완료!

personas/{PERSONA_NAME}/
├── reference_{STYLE}.png
└── metadata.json

캐릭터 정보:
- 이름: {name}
- 성별: {gender}
- 나이대: {age_range}
- 스타일: {style}
- 분위기: {vibe}
- 말투: {speech_level}
- 배경: {background_desc}

이 캐릭터로 영상을 만들려면 콘텐츠 생성을 선택하세요!
```

---

## 중요 규칙

1. **generate_reference_image() 사용** — character_sheet 방식 X
2. **bg removal 절대 금지** — 캐릭터를 배경 위에 직접 생성
3. **이미지 승인 필수** — 승인 전에 메타데이터 저장하지 않기
4. **style 필드 저장** — metadata.json에 style 반드시 포함
5. **9:16 세로형** — reference image는 항상 720x1280
6. **재생성** — 시드 변경으로 다양한 결과 제공
