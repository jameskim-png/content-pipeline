# Phase: Plan -- 재창조 스크립트 생성

## 0. 컨텍스트 로드

```bash
source .venv/bin/activate
python -c "
from src.utils import load_json
from pathlib import Path
import json

analysis = load_json(Path('{VIDEO_DIR}/analysis.json'))
transcript = load_json(Path('{VIDEO_DIR}/transcript.json'))

print('=== Analysis ===')
print(json.dumps(analysis, indent=2, ensure_ascii=False))
print()
print('=== Transcript ===')
print(json.dumps(transcript, indent=2, ensure_ascii=False))
"
```

## 1. STT 기반 나레이션 스크립트 생성

위에서 로드한 analysis.json + transcript.json을 기반으로 나레이션 릴스 스크립트 생성.

Claude가 **직접** 다음을 수행:

1. 원본 텍스트를 나레이션 스타일로 재구성
2. 각 씬에 대한 scene_description 생성 (영어, Flux용)
3. 각 씬에 대한 animation_prompt 생성 (영어, Grok용)
4. style_prompt 적용

### JSON 형식

```json
{
  "title": "<재창조된 타이틀>",
  "style_prompt": "{STYLE_PROMPT}",
  "full_script": "<전체 나레이션 (연결된 텍스트)>",
  "target_duration": {TOTAL_DURATION},
  "original_source": "{URL}",
  "chunks": [
    {
      "chunk_id": "chunk_001",
      "text": "<이 청크의 나레이션 대사>",
      "scene_description": "<Flux 이미지 프롬프트 (영어)>",
      "animation_prompt": "<Grok 비디오 프롬프트 (영어)>",
      "estimated_duration": 4.0,
      "original_text": "<원본 텍스트>"
    }
  ]
}
```

### scene_description 작성 가이드

- 원본 씬의 핵심 비주얼을 AI 이미지로 재해석
- style_prompt와 자연스럽게 결합되도록
- 구체적인 오브젝트, 배경, 구도 설명
- 원본의 텍스트/워터마크 등은 제외

### animation_prompt 작성 가이드

- 원본 영상의 움직임을 참고하되, AI 이미지에 맞게 조정
- 카메라 움직임 중심: slow zoom, gentle pan, orbit
- 씬 내 모션: floating, swaying, particle effects
- 4096자 이내

## 2. 사용자 확인

```
재창조 스크립트:

제목: {title}
원본: {URL}
스타일: {style_prompt}
총 길이: ~{target_duration}초
청크 수: {n_chunks}개

chunk_001 (~{duration}s):
  원본: "{original_text (앞 40자)}"
  나레이션: "{text}"
  씬: {scene_description (앞 60자)}
  애니: {animation_prompt (앞 60자)}

chunk_002 (~{duration}s):
  ...

수정할 부분이 있나요? (없으면 Enter)
```

## 3. 스크립트 저장

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

## Rules
- 원본의 핵심 내용은 유지하되, 나레이션 스타일로 재구성
- scene_description, animation_prompt는 영어로 (Flux/Grok 최적)
- 나레이션 텍스트는 대상 언어로 (LANGUAGE_LABEL)
- 사용자 확인 필수

## Output
- script.json (narration reel format)
