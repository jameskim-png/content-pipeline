# Phase: Analyze — STT + 청킹 + 분석

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

## 3. 분석 (Claude 직접)

- `build_title_prompt()` → 타이틀 추출
- `build_bgm_prompt()` → BGM 분석
- `build_chunk_analysis_prompt()` → 청크별 분석 (표정, 동작, 오버레이)
- 결과를 `analysis.json`에 저장
- `build_index()`로 마스터 인덱스 생성

## Rules
- Demucs 먼저, STT 나중 (BGM 간섭 방지)
- 청크 경계: 문장 경계에서 자르기

## Output
- transcript.json, analysis.json, chunks.json, index.json
