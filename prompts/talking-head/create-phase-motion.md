# Phase: Motion — 모션 라이브러리 체크 + 매칭

## 모션 라이브러리 상태 확인

```bash
source .venv/bin/activate
python -c "
from src.motion_refs import list_motion_library_status
import json
status = list_motion_library_status()
print(json.dumps(status, indent=2, ensure_ascii=False))
"
```

- 비어있으면 → 생성 제안 (10감정 x 2클립, ~$3, ~10분)
- 있으면 → 매칭 진행

## 모션 라이브러리 생성 (필요시)

```bash
source .venv/bin/activate
python -c "
from src.motion_refs import generate_full_motion_library
from pathlib import Path
ref_image = Path('{PERSONA_DIR}/reference_{STYLE}.png')
results = generate_full_motion_library(ref_image, clips_per_emotion=2)
import json
print(json.dumps(results, indent=2, ensure_ascii=False))
"
```

## 모션 매칭

```bash
source .venv/bin/activate
python -c "
from src.motion_refs import select_motion_references_for_script
from src.script_gen import load_script
from pathlib import Path
import json
script = load_script(Path('{OUTPUT_DIR}'))
persona_spec = {PERSONA_SPEC_JSON}
matches = select_motion_references_for_script(script['chunks'], persona_spec=persona_spec)
print(json.dumps(matches, indent=2, ensure_ascii=False))
"
```

## Output
- motion_matches (chunk_id → motion_ref_path mapping)
