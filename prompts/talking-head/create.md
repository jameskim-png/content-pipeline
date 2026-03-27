# Talking Head — 오리지널 생성

제목 또는 스크립트만으로 처음부터 토킹헤드 릴스를 생성하는 파이프라인.
모델/TTS 고정: Kling 2.6 Motion Control + Sync Lipsync v2 + Google TTS (ko-KR-Chirp3-HD-Leda).

---

## Phase 0: 사용자 입력

### Q1. 캐릭터 선택

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

**기존 캐릭터가 있으면:**
```
기존 캐릭터가 있어요!

1. {name1} — {gender}, {age_range}, {vibe} [스타일: {style}]
2. {name2} — ...
N+1. 새로 만들기

어떤 캐릭터를 사용할까요?
```

- 기존 선택 → `load_persona()` → Q2로
- "새로 만들기" → `prompts/character/create.md` 로직 인라인 실행 후 돌아와서 Q2로

**기존 캐릭터가 없으면:** → `prompts/character/create.md` 로직 인라인 실행 안내

### Q2. 콘텐츠 입력

```
콘텐츠를 어떻게 만들까요?

1. 제목만 입력 → AI가 스크립트 생성
2. 스크립트 직접 입력
```

- 제목만 → Q2-1로
- 스크립트 직접 → 입력받아 script 포맷으로 변환 (Phase 1에서 처리)

### Q2-1. 목표 길이 (제목만일 때)

```
영상 목표 길이를 선택해주세요:

1. ~30초 (기본)
2. ~60초
3. ~90초
```

### Q3. 자막

```
자막을 포함할까요? (기본: N)
```

### Q4. BGM

```
BGM을 포함할까요? (기본: 없음)
파일 경로를 입력하면 사용합니다.
```

### Q5. 모션 라이브러리 체크

```bash
source .venv/bin/activate
python -c "
from src.motion_refs import list_motion_library_status
import json
status = list_motion_library_status()
print(json.dumps(status, indent=2, ensure_ascii=False))
"
```

- 라이브러리가 비어있으면:
```
모션 라이브러리가 비어있어요!
영상 생성을 위해 감정별 모션 레퍼런스 클립이 필요합니다.

지금 생성할까요? (10감정 x 2클립 = 20클립, ~$3, ~10분)
Y/N
```
  - Y → Phase 0.5로
  - N → 모션 없이는 진행 불가, 안내

- 라이브러리가 있으면 → Q6로

### Q6. API 검증 + 비용 예상

```bash
source .venv/bin/activate
python -c "
from src.config import check_fal_balance, estimate_job_cost
import json

fal = check_fal_balance()
print('fal.ai:', json.dumps(fal))

# Estimate cost (original content: no STT cost)
cost = estimate_job_cost('kling26', {N_CHUNKS}, {TARGET_DURATION}, tts_engine='google', total_chars={TOTAL_CHARS}, original_content=True)
print('Cost:', json.dumps(cost, indent=2))
"
```

```
잔액 + 예상 비용:
├── fal.ai: ${fal_balance}
├── TTS (Google Cloud): ~${tts_cost}
├── 영상 생성 (Kling 2.6 + Sync Lipsync): ~${video_cost}
├── 이미지: ~${image_cost}
└── 총 예상 비용: ~${total}

진행할까요? (Y/N)
```

---

## Phase 0.5: 모션 라이브러리 생성 (필요시만)

캐릭터의 reference image를 사용해서 모션 라이브러리 생성:

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

완료 후 상태 확인:

```bash
source .venv/bin/activate
python -c "
from src.motion_refs import list_motion_library_status
import json
print(json.dumps(list_motion_library_status(), indent=2))
"
```

---

## Phase 1: 스크립트 생성

### 제목만 입력한 경우

```bash
source .venv/bin/activate
python -c "
from src.script_gen import build_script_generation_prompt
import json

persona_spec = {PERSONA_SPEC_JSON}
prompt = build_script_generation_prompt(persona_spec, '{TITLE}', target_duration={TARGET_DURATION})
print(prompt)
"
```

이 프롬프트로 **직접** 스크립트 생성. JSON 형식으로.

### 스크립트 직접 입력한 경우

사용자 텍스트를 script 포맷으로 구조화:
- 적절히 청크 분할 (3~8초 단위)
- 각 청크에 emotion 태그 부여

### 검증

```bash
source .venv/bin/activate
python -c "
from src.script_gen import validate_script
import json

script = {SCRIPT_JSON}
errors = validate_script(script)
if errors:
    print('VALIDATION_ERRORS:')
    for e in errors:
        print(f'  - {e}')
else:
    print('VALID')
"
```

### 사용자 확인

```
생성된 스크립트:

제목: {title}
총 길이: ~{target_duration}초
청크 수: {n_chunks}개

chunk_001 [{emotion}] (~{duration}s):
  "{text}"

chunk_002 [{emotion}] (~{duration}s):
  "{text}"
...

수정할 부분이 있나요? (없으면 Enter)
```

수정 요청 시:

```bash
source .venv/bin/activate
python -c "
from src.script_gen import build_script_revision_prompt
import json

current_script = {CURRENT_SCRIPT_JSON}
prompt = build_script_revision_prompt(current_script, '{REVISION_REQUEST}')
print(prompt)
"
```

이 프롬프트로 **직접** 스크립트 수정 → 다시 검증 → 확인.

### 스크립트 저장

```bash
source .venv/bin/activate
python -c "
from src.script_gen import save_script
from pathlib import Path

output_dir = Path('{OUTPUT_DIR}')
output_dir.mkdir(parents=True, exist_ok=True)

script = {FINAL_SCRIPT_JSON}
path = save_script(output_dir, script)
print(f'Script saved: {path}')
"
```

---

## Phase 2: TTS (음성 생성)

스크립트를 translation 포맷으로 변환 후 generate_chunk_voices() 호출:

```bash
source .venv/bin/activate
python -c "
from src.script_gen import script_to_translation_format, load_script
from src.voice import generate_chunk_voices
from pathlib import Path

script = load_script(Path('{OUTPUT_DIR}'))
translation = script_to_translation_format(script)

audio_dir = Path('{OUTPUT_DIR}/audio')
results = generate_chunk_voices(
    translation=translation,
    output_dir=audio_dir,
    tts_engine='google',
    voice_name='ko-KR-Chirp3-HD-Leda',
)
for r in results:
    print(f\"  {r['chunk_id']}: {r['actual_duration']:.2f}s\")
print(f'Generated {len(results)} voice files')
"
```

---

## Phase 3: 모션 레퍼런스 매칭

스크립트의 emotion 태그로 모션 클립 매칭:

```bash
source .venv/bin/activate
python -c "
from src.motion_refs import select_motion_references_for_script
from src.script_gen import load_script
from pathlib import Path
import json

script = load_script(Path('{OUTPUT_DIR}'))
matches = select_motion_references_for_script(script['chunks'])
print(json.dumps(matches, indent=2, ensure_ascii=False))
"
```

매칭 결과:
```
모션 매칭 결과:
  chunk_001 [happy] → happy_001.mp4
  chunk_002 [explaining] → explaining_002.mp4
  chunk_003 [surprised] → surprised_001.mp4
  ...
```

---

## Phase 4: 영상 생성

각 청크에 대해 Kling 2.6 Motion Control → Sync Lipsync v2:

```bash
source .venv/bin/activate
python -c "
from src.video_gen import generate_chunk_video
from pathlib import Path
import json

ref_image = Path('{PERSONA_DIR}/reference_{STYLE}.png')

chunk_videos = []
motion_matches = {MOTION_MATCHES_JSON}

for match in motion_matches:
    chunk_id = match['chunk_id']
    motion_ref = Path(match['motion_ref_path'])
    audio_path = Path('{OUTPUT_DIR}/audio/{chunk_id}_voice.wav'.format(chunk_id=chunk_id))
    output = Path('{OUTPUT_DIR}/chunks/{chunk_id}_video.mp4'.format(chunk_id=chunk_id))

    print(f'Generating {chunk_id}...')
    generate_chunk_video(
        model='kling26',
        face_image_path=ref_image,
        audio_path=audio_path,
        output_path=output,
        prompt='Person talking to camera, upper body, natural movement',
        source_video_path=motion_ref,
    )
    chunk_videos.append({'chunk_id': chunk_id, 'video_path': str(output)})
    print(f'  {chunk_id} done')

print(json.dumps(chunk_videos, indent=2))
"
```

---

## Phase 5: 오디오 믹싱

```bash
source .venv/bin/activate
python -c "
from src.audio_mixing import mix_all_chunks
from src.script_gen import load_script
from pathlib import Path

script = load_script(Path('{OUTPUT_DIR}'))
voice_dir = Path('{OUTPUT_DIR}/audio')
audio_out = Path('{OUTPUT_DIR}/audio')
bgm_path = Path('{BGM_PATH}') if '{BGM_PATH}' != '' else None

results = mix_all_chunks(voice_dir, audio_out, script['chunks'], bgm_path)
print(f'Mixed {len(results)} audio files')
"
```

---

## Phase 6: 자막 생성 (선택한 경우만)

```bash
source .venv/bin/activate
python -c "
from src.subtitles import recalculate_subtitle_timings, generate_ass
from src.utils import load_json
from src.script_gen import load_script, script_to_translation_format
from pathlib import Path

voice_manifest = load_json(Path('{OUTPUT_DIR}/audio/voice_manifest.json'))
script = load_script(Path('{OUTPUT_DIR}'))
translation = script_to_translation_format(script)

subtitle_chunks = recalculate_subtitle_timings(voice_manifest, translation['chunks'])

output = Path('{OUTPUT_DIR}/subtitles.ass')
generate_ass(subtitle_chunks, output)
print(f'Subtitles saved: {output} ({len(subtitle_chunks)} entries)')
"
```

---

## Phase 7: 최종 스티칭

```bash
source .venv/bin/activate
python -c "
from src.stitching import stitch_chunks
from pathlib import Path

output_dir = Path('{OUTPUT_DIR}')
final_path = output_dir / 'final.mp4'

stitch_chunks(
    chunk_videos={CHUNK_VIDEOS_JSON},
    mixed_audios={MIXED_AUDIOS_JSON},
    output_path=final_path,
)
print(f'Final video: {final_path}')
"
```

자막 번인 (선택한 경우):
```bash
source .venv/bin/activate
python -c "
from src.subtitles import burn_subtitles
from pathlib import Path

video = Path('{OUTPUT_DIR}/final.mp4')
subs = Path('{OUTPUT_DIR}/subtitles.ass')
output = Path('{OUTPUT_DIR}/final_subtitled.mp4')

burn_subtitles(video, subs, output)
print(f'Subtitled video: {output}')
"
```

---

## Phase 8: 미리보기 + 결과 리포트

```bash
open {OUTPUT_DIR}/final.mp4
```

```
오리지널 토킹헤드 영상 생성 완료!

{OUTPUT_DIR}/
├── final.mp4
├── script.json
├── chunks/
│   ├── chunk_001_video.mp4
│   └── ...
└── audio/
    ├── chunk_001_voice.wav
    ├── chunk_001_mixed.wav
    ├── voice_manifest.json
    └── ...

제목: {title}
캐릭터: {persona_name} ({style})
청크 수: {n_chunks}
총 길이: ~{total_duration}초

비용 예상:
- TTS (Google Cloud): ~${tts_cost}
- 영상 생성 (Kling 2.6 + Sync Lipsync): ~${video_cost}
- 이미지: ~${image_cost}
- 총 예상 비용: ~${total_cost}
```

---

## 중요 규칙

1. **모델 고정** — Kling 2.6 Motion Control + Sync Lipsync v2. 선택지 없음
2. **TTS 고정** — Google Cloud TTS `ko-KR-Chirp3-HD-Leda`. 선택지 없음
3. **모션 라이브러리 필수** — 비어있으면 먼저 생성 제안
4. **스크립트 확인 필수** — 사용자가 스크립트 검토 후 진행
5. **bg removal 절대 금지** — reference image에 배경이 이미 포함
6. **script_to_translation_format()** — 반드시 이 브릿지를 통해 voice 모듈에 전달
7. **에러 복구** — 특정 청크 실패 시 해당 청크만 재시도 (skip 로직 내장)
8. **비용 추적** — original_content=True로 STT 비용 제외
9. **emotion 태그** — 스크립트의 emotion이 모션 라이브러리와 1:1 매칭
10. **연속 클립 회피** — select_motion_references_for_script()가 자동 처리
