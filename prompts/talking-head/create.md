# Talking Head — 오리지널 생성

제목 또는 스크립트만으로 처음부터 토킹헤드 릴스를 생성하는 파이프라인.
모델 기본: Grok Imagine Video + Sync Lipsync v2 (Kling 2.6 선택 가능). TTS 엔진 고정: Chirp3-HD (음성은 언어에 따라 자동 결정).

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

### Q2.5. 콘텐츠 언어

```bash
source .venv/bin/activate
python -c "
from src.languages import list_languages_summary
print(list_languages_summary())
"
```

```
콘텐츠 언어를 선택해주세요:

{list_languages_summary 출력}

(기본: 1. 한국어)
```

- 한국어 선택 → 스크립트를 한국어로 바로 생성
- 다른 언어 선택 → 스크립트를 한국어로 생성 후 Phase 1.5에서 대상 언어로 번역

언어 설정 로드:

```bash
source .venv/bin/activate
python -c "
from src.languages import get_language_config, get_voice_name
config = get_language_config('{LANG_CODE}')
print(f\"Language: {config['label']}\")
print(f\"Voice: {get_voice_name('{LANG_CODE}')}\")
"
```

→ `VOICE_NAME`, `LANGUAGE_LABEL`, `LANG_CODE` 변수 설정

### Q3. 자막 스타일

```bash
source .venv/bin/activate
python -c "
from src.subtitle_styles import list_styles_summary, load_style_library
print(list_styles_summary())
n = len(load_style_library())
print(f'{n+1}. 새 스타일 만들기')
print(f'{n+2}. 미리보기')
print(f'{n+3}. 없음')
"
```

```
자막 스타일을 선택해주세요:

{list_styles_summary 출력}
N+1. 새 스타일 만들기
N+2. 미리보기
N+3. 없음 (기본)
```

- 스타일 선택 (1~N) → `SUBTITLE_STYLE` 변수 설정, `SUBTITLES=Y`
- "없음" → `SUBTITLES=N`
- "미리보기" → HTML 프리뷰 생성 후 다시 선택:

```bash
source .venv/bin/activate
python -c "
from src.titles import generate_title_preview_html
from src.subtitle_styles import load_style_library
from pathlib import Path

title = '{TITLE}'
output = Path('{OUTPUT_DIR}/preview.html')
generate_title_preview_html(title, output, subtitle_styles=load_style_library())
print(f'Preview: {output}')
"
```

```bash
open {OUTPUT_DIR}/preview.html
```

- "새 스타일 만들기":
  1. 레퍼런스 이미지 경로 또는 텍스트 설명 입력
  2. Claude가 분석 → ASS 파라미터 + preview_css 생성
  3. 미리보기 확인
  4. 이름 입력 → `save_user_style()` 호출로 라이브러리에 영구 추가

```bash
source .venv/bin/activate
python -c "
from src.subtitle_styles import save_user_style
import json
style = {STYLE_JSON}
path = save_user_style('{STYLE_NAME}', style)
print(f'Style saved: {path}')
"
```

### Q3.5. 타이틀 오버레이

```
타이틀을 영상에 표시할까요? (샘플 미리보기를 먼저 볼 수 있어요)

1. 클린 — 흰색, 깔끔한 스트로크
2. 임팩트 — 노란색, 강렬한 느낌
3. 박스 — 흰색, 배경 박스
4. 없음 (기본)
5. 미리보기 보기 → HTML 샘플 열기
```

- "미리보기 보기" 선택 시:

```bash
source .venv/bin/activate
python -c "
from src.titles import generate_title_preview_html
from src.subtitle_styles import load_style_library
from pathlib import Path

title = '{TITLE}'
output = Path('{OUTPUT_DIR}/title_preview.html')
subtitle_styles = load_style_library() if '{SUBTITLES}' == 'Y' else None
generate_title_preview_html(title, output, subtitle_styles=subtitle_styles)
print(f'Preview: {output}')
"
```

```bash
open {OUTPUT_DIR}/title_preview.html
```

→ 브라우저에서 확인 후 다시 1~4 중 선택

- 프리셋 선택 시 (1~3) → 노출 시간 질문:

```
타이틀 노출 시간:
1. 전체 (기본)
2. 첫 5초만 (페이드아웃)
```

### Q4. BGM

```
BGM을 포함할까요? (기본: 없음)
파일 경로를 입력하면 사용합니다.
```

### Q5. 영상 모델 선택

```
영상 생성 모델을 선택해주세요:

1. Grok Imagine Video (기본) — 더 자연스러운 움직임, 모션 라이브러리 불필요
2. Kling 2.6 Motion Control — 모션 레퍼런스 기반, 라이브러리 필요
```

- Grok 선택 (기본) → `MODEL='grok'`, Q6로 (모션 라이브러리 불필요)
- Kling26 선택 → `MODEL='kling26'`, 모션 라이브러리 체크 → Q5.5로

### Q5.5. 모션 라이브러리 체크 (Kling26 선택 시만)

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

1. 스톡 영상 임포트 (추천) — 준비된 클립 폴더 경로 입력
2. 개별 감정 임포트 — 감정별로 하나씩 클립 지정
3. AI 자동 생성 — ~$5, ~10분 (모션이 덜 자연스러울 수 있음)
```
  - 1 → Phase 0.5 폴더 임포트
  - 2 → Phase 0.5 개별 임포트
  - 3 → Phase 0.5 AI 생성

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
cost = estimate_job_cost('{MODEL}', {N_CHUNKS}, {TARGET_DURATION}, tts_engine='google', total_chars={TOTAL_CHARS}, original_content=True)
print('Cost:', json.dumps(cost, indent=2))
"
```

```
잔액 + 예상 비용:
├── fal.ai: ${fal_balance}
├── TTS (Google Cloud): ~${tts_cost}
├── 영상 생성 ({MODEL_LABEL}): ~${video_cost}
├── 이미지: ~${image_cost}
└── 총 예상 비용: ~${total}

진행할까요? (Y/N)
```

- `MODEL_LABEL`: Grok → "Grok + Sync Lipsync", Kling26 → "Kling 2.6 + Sync Lipsync"

---

## Phase 0.5: 모션 라이브러리 구축 (필요시만)

### 옵션 1: 폴더 배치 임포트 (추천)

사용자가 준비한 클립 폴더에서 일괄 임포트. 파일명 규칙: `{emotion}_001.mp4` 또는 `{emotion}.mp4`.
소싱 가이드: `data/motion-references/SOURCING_GUIDE.md` 참조.

```bash
source .venv/bin/activate
python -c "
from src.motion_refs import import_from_folder
import json

report = import_from_folder('{FOLDER_PATH}')
print(json.dumps(report, indent=2, ensure_ascii=False))
"
```

### 옵션 2: 개별 감정 임포트

감정별로 하나씩 클립 경로 지정:

```bash
source .venv/bin/activate
python -c "
from src.motion_refs import import_motion_clip
path = import_motion_clip('{EMOTION}', '{CLIP_PATH}')
print(f'Imported: {path}')
"
```

### 옵션 3: AI 자동 생성 (폴백)

캐릭터의 reference image를 사용해서 모션 라이브러리 AI 생성 (~$5, ~10분):

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

### 완료 후 상태 확인

```bash
source .venv/bin/activate
python -c "
from src.motion_refs import preview_library_status
print(preview_library_status())
"
```

빠진 감정이 있으면 추가 임포트 또는 AI 폴백 제안.

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

## Phase 1.5: 번역 (한국어 이외 언어 선택 시만)

한국어 이외의 언어를 선택한 경우, Phase 1에서 생성/입력된 한국어 스크립트를 대상 언어로 번역.

```bash
source .venv/bin/activate
python -c "
from src.translation import build_translation_prompt
from src.languages import get_language_config
import json

config = get_language_config('{LANG_CODE}')
# transcript = 한국어 스크립트를 원본으로 구성
transcript = {'text': '''{FULL_SCRIPT}'''}
chunks = {CHUNKS_FOR_TRANSLATION_JSON}
persona_spec = {PERSONA_SPEC_JSON}

prompt = build_translation_prompt(transcript, chunks, persona_spec, target_language=config['label'])
print(prompt)
"
```

이 프롬프트로 **직접** 번역 수행 → 사용자 확인 → 번역된 스크립트 저장.

번역 후에는 번역된 텍스트가 이후 TTS, 타이틀, 자막에 모두 사용됨.

---

## Phase 2: Pre-generation Review

스크립트 청킹 후, TTS 전에 실행. `create-phase-review.md` 참조.

```bash
source .venv/bin/activate
python -c "
from src.review import review_chunks
from src.script_gen import load_script
from pathlib import Path
import json

script = load_script(Path('{OUTPUT_DIR}'))
persona_spec = {PERSONA_SPEC_JSON}

result = review_chunks(script['chunks'], persona_spec=persona_spec, model='{MODEL}')
print(json.dumps(result, indent=2, ensure_ascii=False))
"
```

결과 표시 (변경 리포트 + chunk 테이블 + 프롬프트 미리보기 + 비용) → 사용자 승인 → reviewed chunks를 `save_script()`로 저장.

---

## Phase 3: TTS (음성 생성)

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
    voice_name='{VOICE_NAME}',
)
for r in results:
    print(f\"  {r['chunk_id']}: {r['actual_duration']:.2f}s\")
print(f'Generated {len(results)} voice files')
"
```

---

## Phase 3.5: 모션 레퍼런스 매칭 (Kling26 선택 시만)

스크립트의 emotion 태그로 모션 클립 매칭:

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

`create-phase-video.md` 참조. 모델에 따라 분기:

### Grok (기본)

모션 라이브러리 불필요. script chunks에서 직접 순회:

```bash
source .venv/bin/activate
python -c "
from src.video_gen import generate_chunk_video
from src.script_gen import load_script
from pathlib import Path
import json

ref_image = Path('{PERSONA_DIR}/reference_{STYLE}.png')
persona_spec = {PERSONA_SPEC_JSON}
script = load_script(Path('{OUTPUT_DIR}'))

chunk_videos = []
for chunk in script['chunks']:
    chunk_id = chunk['chunk_id']
    audio_path = Path('{OUTPUT_DIR}/audio/{cid}_voice.wav'.format(cid=chunk_id))
    output = Path('{OUTPUT_DIR}/chunks/{cid}_video.mp4'.format(cid=chunk_id))

    print(f'Generating {chunk_id}...')
    generate_chunk_video(
        model='grok',
        face_image_path=ref_image,
        audio_path=audio_path,
        output_path=output,
        persona_spec=persona_spec,
        chunk_text=chunk.get('text', ''),
        emotion=chunk.get('emotion', ''),
    )
    chunk_videos.append({'chunk_id': chunk_id, 'video_path': str(output)})
    print(f'  {chunk_id} done')

print(json.dumps(chunk_videos, indent=2))
"
```

### Kling 2.6 (사용자가 선택한 경우)

모션 라이브러리 필수. Phase 3.5에서 매칭된 motion_matches 사용:

```bash
source .venv/bin/activate
python -c "
from src.video_gen import generate_chunk_video
from src.script_gen import load_script
from pathlib import Path
import json

ref_image = Path('{PERSONA_DIR}/reference_{STYLE}.png')
persona_spec = {PERSONA_SPEC_JSON}
script = load_script(Path('{OUTPUT_DIR}'))
chunk_text_map = {c['chunk_id']: c.get('text', '') for c in script['chunks']}

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
        persona_spec=persona_spec,
        chunk_text=chunk_text_map.get(chunk_id, ''),
        emotion=match.get('emotion', ''),
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
from src.subtitle_styles import get_style, style_to_ass_params
from src.utils import load_json
from src.script_gen import load_script, script_to_translation_format
from pathlib import Path

voice_manifest = load_json(Path('{OUTPUT_DIR}/audio/voice_manifest.json'))
script = load_script(Path('{OUTPUT_DIR}'))
translation = script_to_translation_format(script)

subtitle_chunks = recalculate_subtitle_timings(voice_manifest, translation['chunks'])

output = Path('{OUTPUT_DIR}/subtitles.ass')
style_params = style_to_ass_params(get_style('{SUBTITLE_STYLE}'))
generate_ass(subtitle_chunks, output, **style_params)
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

타이틀 번인 (선택한 경우):
```bash
source .venv/bin/activate
python -c "
from src.titles import burn_title
from pathlib import Path

# 자막이 있으면 subtitled 영상 위에, 없으면 final 위에
video = Path('{OUTPUT_DIR}/final_subtitled.mp4') if Path('{OUTPUT_DIR}/final_subtitled.mp4').exists() else Path('{OUTPUT_DIR}/final.mp4')
output = Path('{OUTPUT_DIR}/final_titled.mp4')

burn_title(video, '{TITLE}', '{TITLE_PRESET}', output, duration='{TITLE_DURATION}')
print(f'Titled video: {output}')
"
```

- `TITLE_PRESET`: "clean", "impact", or "box"
- `TITLE_DURATION`: "full" or "intro"
- 타이틀이 있으면 최종 파일은 `final_titled.mp4`

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
- 영상 생성 ({MODEL_LABEL}): ~${video_cost}
- 이미지: ~${image_cost}
- 총 예상 비용: ~${total_cost}
```

---

## 중요 규칙

1. **모델 기본 Grok** — Grok Imagine Video + Sync Lipsync v2. Kling 2.6 선택 가능
2. **TTS 엔진 고정** — Chirp3-HD. 음성은 언어에 따라 자동 결정 (`{VOICE_NAME}`)
3. **모션 라이브러리** — Kling26 선택 시만 필수. Grok은 불필요
4. **Pre-generation Review 필수** — Phase 2에서 `review_chunks()` 실행 후 승인
5. **스크립트 확인 필수** — 사용자가 스크립트 검토 후 진행
6. **bg removal 절대 금지** — reference image에 배경이 이미 포함
7. **script_to_translation_format()** — 반드시 이 브릿지를 통해 voice 모듈에 전달
8. **에러 복구** — 특정 청크 실패 시 해당 청크만 재시도 (skip 로직 내장)
9. **비용 추적** — original_content=True로 STT 비용 제외
10. **emotion 태그** — Kling26: 모션 라이브러리와 1:1 매칭. Grok: 프롬프트에 직접 반영
11. **연속 클립 회피** — Kling26에서 select_motion_references_for_script()가 자동 처리
12. **언어 기본값** — 모든 기본값은 한국어 (`ko`). 다른 언어 선택 시 Phase 1.5 번역 삽입
13. **자막 스타일** — `subtitle_styles.py` 라이브러리에서 선택. `style_to_ass_params()`로 변환
