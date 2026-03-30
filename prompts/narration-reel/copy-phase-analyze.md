# Phase: Analyze -- STT + 씬 분할 + 컨텐츠 분석

## 1. STT

```bash
source .venv/bin/activate
python -c "
from src.stt import transcribe_and_save
from pathlib import Path
import json
vocals = Path('{AUDIO_DIR}/vocals.wav')
output = Path('{VIDEO_DIR}/transcript.json')
result = transcribe_and_save(vocals, output)
print(json.dumps(result, indent=2, ensure_ascii=False))
"
```

## 2. 청킹

```bash
source .venv/bin/activate
python -c "
from src.chunking import create_chunks
from src.utils import load_json
from pathlib import Path
import json
video = Path('{VIDEO_PATH}')
vocals = Path('{AUDIO_DIR}/vocals.wav')
transcript = load_json(Path('{VIDEO_DIR}/transcript.json'))
output = Path('{VIDEO_DIR}/chunks')
chunks = create_chunks(video, vocals, transcript, output)
print(json.dumps(chunks, indent=2, ensure_ascii=False))
"
```

## 3. 컨텐츠 분석 (Claude 직접)

원본 영상의 컨텐츠를 분석해서 나레이션 릴스로 재창조할 정보를 추출:

- **주제/타이틀 추출**: 원본 영상이 무엇에 대한 것인지
- **씬 구성 분석**: 각 청크가 어떤 장면을 보여주는지
- **톤/분위기**: 교육적, 유머, 감성, 공포 등
- **핵심 비주얼 요소**: 각 씬에서 중요한 시각적 요소

분석 결과를 `analysis.json`에 저장:

```json
{
  "title": "추출된 타이틀",
  "topic": "주제 요약",
  "tone": "교육적/유머/감성/공포",
  "original_language": "감지된 언어",
  "scenes": [
    {
      "chunk_id": "chunk_001",
      "description": "이 씬에서 보여주는 내용",
      "key_visuals": "핵심 비주얼 요소",
      "text": "원본 나레이션/대사"
    }
  ]
}
```

## 4. 분석 결과 저장

```bash
source .venv/bin/activate
python -c "
from src.utils import save_json
from pathlib import Path

analysis = {ANALYSIS_JSON}
save_json(analysis, Path('{VIDEO_DIR}/analysis.json'))
print(f'Analysis saved: {VIDEO_DIR}/analysis.json')
print(f'  Scenes: {len(analysis.get(\"scenes\", []))}')
"
```

## 5. 스타일 유추 (Q3에서 "원본 스타일 유추" 선택 시)

원본 영상의 시각적 스타일을 분석해서 적절한 AI 이미지 스타일 프롬프트 생성.

```
원본 영상 분석 결과:

- 주제: {topic}
- 톤: {tone}
- 씬 수: {n_chunks}
- 추천 스타일: {recommended_style_prompt}

이 스타일로 진행할까요? (또는 다른 프리셋 선택)
```

## Rules
- Demucs 먼저, STT 나중 (BGM 간섭 방지)
- 씬 분석은 나레이션 릴스 재창조를 위한 것 (TH와 다름)
- scene_description 생성에 사용될 기초 데이터 추출

## Output
- transcript.json
- analysis.json (주제, 씬별 분석, 스타일 추천)
- chunks data
