# Phase: Script — 스크립트 생성 + 검증

## 제목만 입력한 경우

```bash
source .venv/bin/activate
python -c "
from src.script_gen import build_script_generation_prompt
persona_spec = {PERSONA_SPEC_JSON}
prompt = build_script_generation_prompt(persona_spec, '{TITLE}', target_duration={TARGET_DURATION})
print(prompt)
"
```

이 프롬프트로 **직접** 스크립트 생성 (JSON 형식).

## 스크립트 직접 입력한 경우

사용자 텍스트를 구조화:
- 3~8초 단위 청크 분할
- 각 청크에 emotion 태그 부여

## 검증

```bash
source .venv/bin/activate
python -c "
from src.script_gen import validate_script
script = {SCRIPT_JSON}
errors = validate_script(script)
if errors:
    print('VALIDATION_ERRORS:')
    for e in errors: print(f'  - {e}')
else:
    print('VALID')
"
```

## 사용자 확인 필수

스크립트를 보여주고 수정 여부 확인. 수정 요청 시 `build_script_revision_prompt()` 사용.

## 스크립트 저장

```bash
source .venv/bin/activate
python -c "
from src.script_gen import save_script
from pathlib import Path
output_dir = Path('{OUTPUT_DIR}')
output_dir.mkdir(parents=True, exist_ok=True)
path = save_script(output_dir, {FINAL_SCRIPT_JSON})
print(f'Script saved: {path}')
"
```

## Output
- script.json (saved to output dir)
- n_chunks, total_duration
