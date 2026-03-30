# Phase: Script -- 나레이션 스크립트 + 씬 설명 생성

## 스크립트 생성

주제와 스타일을 기반으로 **직접** 나레이션 스크립트를 생성. JSON 형식으로.

### 프롬프트 가이드

다음 구조로 스크립트를 생성해야 함:

```
제목/주제: {TITLE}
시각 스타일: {STYLE_PROMPT}
목표 길이: ~{TARGET_DURATION}초
언어: {LANGUAGE_LABEL}

스크립트 규칙:
1. 나레이션 대사는 {LANGUAGE_LABEL}로 자연스러운 구어체
2. 목표 길이에 맞게 청크 분할 (1청크 = 3~8초 분량)
3. 도입-전개-마무리 구조
4. 릴스/숏츠에 맞게 강한 첫 문장 (hook)
5. scene_description은 영어로 작성 (Flux 이미지 생성용)
6. animation_prompt는 영어로 작성 (Grok 비디오 생성용)
7. style_prompt와 scene_description이 자연스럽게 결합되도록
```

### JSON 형식

```json
{
  "title": "<제목>",
  "style_prompt": "{STYLE_PROMPT}",
  "full_script": "<전체 나레이션 (연결된 텍스트)>",
  "target_duration": {TARGET_DURATION},
  "chunks": [
    {
      "chunk_id": "chunk_001",
      "text": "<이 청크의 나레이션 대사>",
      "scene_description": "<Flux 이미지 프롬프트 (영어). 스타일 프롬프트와 결합됨>",
      "animation_prompt": "<Grok 비디오 프롬프트 (영어). 카메라 움직임, 모션 설명>",
      "estimated_duration": 4.0
    }
  ]
}
```

### scene_description 작성 가이드

- 영어로 작성 (Flux는 영어 프롬프트 최적)
- style_prompt가 이미 전체 스타일을 정의하므로, 씬별 고유한 내용에 집중
- 구체적인 오브젝트, 배경, 구도 설명
- 예: "A colorful open refrigerator overflowing with misplaced items, vegetables in the freezer section, milk bottles on the door shelf"

### animation_prompt 작성 가이드

- 영어로 작성 (Grok은 영어 프롬프트 최적)
- 카메라 움직임 중심: slow zoom in, gentle pan left, camera orbiting around
- 씬 내 오브젝트 모션: items floating, steam rising, leaves falling
- 4096자 이내 유지
- 예: "Slow zoom into the refrigerator, cold mist gently flowing out, slight camera shake"

## 검증

스크립트 생성 후 기본 검증:

- title 존재
- full_script 존재
- chunks가 비어있지 않음
- 각 청크: text, scene_description, animation_prompt 존재
- 각 청크: estimated_duration 범위 (1~15초)
- style_prompt 존재

## 사용자 확인

```
생성된 스크립트:

제목: {title}
스타일: {style_prompt}
총 길이: ~{target_duration}초
청크 수: {n_chunks}개

chunk_001 (~{duration}s):
  나레이션: "{text}"
  씬: {scene_description (앞 60자)}
  애니: {animation_prompt (앞 60자)}

chunk_002 (~{duration}s):
  나레이션: "{text}"
  씬: {scene_description (앞 60자)}
  애니: {animation_prompt (앞 60자)}
...

수정할 부분이 있나요? (없으면 Enter)
```

수정 요청 시 직접 수정 -> 다시 검증 -> 확인.

## 스크립트 저장

```bash
source .venv/bin/activate
python -c "
from src.utils import save_json
from pathlib import Path

output_dir = Path('{OUTPUT_DIR}')
output_dir.mkdir(parents=True, exist_ok=True)

script = {FINAL_SCRIPT_JSON}
save_json(script, output_dir / 'script.json')
print(f'Script saved: {output_dir}/script.json')
"
```

## Output
- script.json (narration reel format with style_prompt, scene_description, animation_prompt)
- n_chunks, target_duration
