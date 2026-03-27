# Talking Head — 인스타 영상 재창조

인스타그램 영상을 다운로드하고, 분석하고, AI 페르소나로 한국어 영상을 새로 만드는 **전체 파이프라인**.
모든 질문을 처음에 한번에 물어본 후, Phase 1 (분석) → Phase 2 (재창조)를 순차적으로 실행.

---

## Phase 0: 전체 질문 수집 (한번에!)

**핵심: 작업 시작 전에 모든 필요 정보를 한번에 수집.**

### Q1. Instagram URL
```
인스타그램 URL을 입력해주세요.
(계정 URL 또는 특정 영상 URL)
```

### Q2. 영상 개수
```
몇 개 영상을 처리할까요? (기본: 1)
```

### Q3. 캐릭터 선택 (기존 or 새로 만들기)

먼저 기존 캐릭터를 스캔:

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

1. {name1} — {gender}, {age_range}, {vibe}
2. {name2} — {gender}, {age_range}, {vibe}
...
N+1. 새로 만들기

어떤 캐릭터를 사용할까요?
```

- 기존 캐릭터 선택 시 → `load_persona()` 실행 → Q6(자막)으로
- "새로 만들기" 선택 시 → `prompts/character/create.md` 로직 인라인 실행 → Q6으로

**기존 캐릭터가 없으면:** → `prompts/character/create.md` 로직 인라인 실행

### Q4. 캐릭터 설명 (자유 텍스트) — 새 캐릭터일 때만
```
영상에 등장할 캐릭터를 설명해주세요!

짧게도 OK: "아이언맨" / "차분한 30대 여성 교수"
길게도 OK: "갓생 실패 전문가 — 부스스한 머리, 귀여운 잠옷..."
레퍼런스도 OK: "이 인스타 계정의 사람처럼: [URL]"
```

→ Claude가 구조화 → 빠진 부분 추가 질문 (대화형)

**persona 구조화 과정:**

1. 사용자 자유 텍스트 입력 받기
2. `src/persona.py`의 `build_persona_parse_prompt(user_input)`으로 프롬프트 생성
3. **직접** 구조화된 persona spec JSON 생성:
   ```json
   {
     "name": "...",
     "gender": "...",
     "age_range": "...",
     "ethnicity": "...",
     "visual_traits": "...",
     "clothing": "...",
     "hair": "...",
     "makeup": "...",
     "voice_tone": "...",
     "speech_level": "...",
     "vibe": "..."
   }
   ```
4. null 필드가 있으면 사용자에게 자연스럽게 추가 질문
5. 최종 spec 사용자 확인

### Q5. 배경 설명 — 새 캐릭터일 때만
```
이 캐릭터가 영상에서 어디에 있으면 좋을까요?

예시: "어수선한 원룸" / "깔끔한 스튜디오" / "카페"
```

### Q6. 자막
```
자막 포함? (기본: Y)
```

### Q7. BGM
```
1. 원본 분위기 매칭
2. BGM 없음
```

### Q8. API Key 검증 + 잔액 체크

```bash
source .venv/bin/activate
python -c "
from src.config import validate_keys, check_fal_balance
import json

keys = validate_keys('kling26')
print('API Keys OK:')
for k, v in keys.items():
    print(f'  {k}: {v[:8]}...')

fal = check_fal_balance()
print('fal.ai:', json.dumps(fal))
"
```

없는 키가 있으면 안내 후 중단.

잔액 표시:
```
API 잔액:
└── fal.ai: ${balance} USD

(예상 비용은 분석 완료 후 확인)
```

잔액이 부족해 보이면 경고.

---

## 설정 확인

모든 입력을 요약해서 사용자에게 확인:

```
설정 확인

소스: {URL} ({COUNT}개 영상)
캐릭터: {PERSONA_NAME} — {persona_summary}
배경: {background_desc}
모델: Kling 2.6 Motion Control + Sync Lipsync v2 (고정)
TTS: Google Cloud TTS ko-KR-Chirp3-HD-Leda (고정)
자막: {Y/N}
BGM: {BGM_OPTION}

이 설정으로 진행할까요?
```

---

## Phase 1: 영상 분석 (Analyze)

### Step 1-1: 다운로드
```bash
source .venv/bin/activate
python -c "
from src.download import parse_instagram_url, download_post, download_account_videos
import json

url = '{URL}'
parsed = parse_instagram_url(url)

if parsed['type'] == 'post':
    results = [download_post(parsed['shortcode'])]
else:
    results = download_account_videos(parsed['username'], {COUNT})

print(json.dumps(results, indent=2, ensure_ascii=False))
"
```

### Step 1-2: 오디오 분리
```bash
source .venv/bin/activate
python -c "
from src.audio_separation import separate_audio
from pathlib import Path
import json

video_path = Path('{VIDEO_PATH}')
audio_dir = video_path.parent / 'audio'
result = separate_audio(video_path, audio_dir)
print(json.dumps({k: str(v) for k, v in result.items()}, indent=2))
"
```

### Step 1-3: STT
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

### Step 1-4: 청킹
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

### Step 1-5: 분석 (Claude 직접)
- 타이틀 추출: `build_title_prompt()` → 분석
- BGM 분석: `build_bgm_prompt()` → 분석
- 청크별 분석: `build_chunk_analysis_prompt()` → 각 청크 분석
- 결과를 `analysis.json`과 각 청크 `analysis.json`에 저장
- `build_index()`로 마스터 인덱스 생성

### Step 1-6: 예상 비용 표시

분석 완료 후 청크 수와 총 길이가 확정되면 비용 예상:

```bash
source .venv/bin/activate
python -c "
from src.config import estimate_job_cost
import json
cost = estimate_job_cost('kling26', {N_CHUNKS}, {TOTAL_DURATION})
print(json.dumps(cost, indent=2))
"
```

```
Phase 1 완료 — 영상 분석

- 길이: {duration}s
- 청크: {n_chunks}개
- 언어: {language}
- BGM: {있음/없음}

예상 비용:
├── STT: ~${stt}
├── TTS: ~${tts}
├── 이미지: ~$0.08
├── 영상: ~${video}
└── 총: ~${total}

Phase 2로 진행합니다...
```

---

## Phase 2: 영상 재창조 (Recreate)

Phase 0에서 이미 수집한 정보 사용 (질문 다시 안 함).

### Step 2-1: Character Sheet + Background 생성

**기존 캐릭터 선택 시 → 이 스텝 스킵** (이미지가 존재하므로)

새 캐릭터일 때만 실행:

```bash
source .venv/bin/activate
python -c "
from src.persona import generate_character_sheet, generate_background, crop_front_face, save_persona_metadata
from pathlib import Path

persona_spec = {PERSONA_SPEC_JSON}
persona_name = '{PERSONA_NAME}'
background_desc = '{BACKGROUND_DESC}'

sheet_path = generate_character_sheet(persona_spec, persona_name, seed=42)
bg_path = generate_background(background_desc, persona_name, seed=42)
face_path = sheet_path.parent / 'front_face.png'
crop_front_face(sheet_path, face_path)

save_persona_metadata(persona_name, persona_spec, background_desc, {
    'character_sheet_prompt': 'auto',
    'background_prompt': 'auto',
})
print(f'Sheet: {sheet_path}')
print(f'Background: {bg_path}')
print(f'Face: {face_path}')
"
```

**이미지 미리보기 — `open` 명령으로 macOS Preview 앱에서 확인:**
```bash
open ./personas/{PERSONA_NAME}/character_sheet.png
open ./personas/{PERSONA_NAME}/background.png
```

→ "미리보기 창을 확인해주세요!"

**사용자 승인 필수:**
```
Character Sheet와 Background가 생성되었습니다.
미리보기 창에서 확인해주세요!

1. 둘 다 OK
2. 캐릭터 재생성
3. 배경 재생성
4. 둘 다 재생성
```

### Step 2-2: 번역
`build_translation_prompt()` → 직접 번역 수행.

**사용자에게 번역 결과 보여주고 수정 여부 확인:**
```
번역 결과:

chunk_001 (3.5s):
  EN: "Hey everyone, today we're going to talk about..."
  KR: "안녕 여러분, 오늘은 ... 에 대해 얘기할 건데"
  ...
```

### Step 2-3: 음성 생성 (Google TTS)
```bash
source .venv/bin/activate
python -c "
from src.voice import generate_chunk_voices
from src.utils import load_json
from pathlib import Path

translation = load_json(Path('{OUTPUT_DIR}/translated_script.json'))
results = generate_chunk_voices(
    translation=translation,
    output_dir=Path('{OUTPUT_DIR}/audio'),
    tts_engine='google',
    voice_name='ko-KR-Chirp3-HD-Leda',
)
for r in results:
    print(f\"  {r['chunk_id']}: {r['actual_duration']:.2f}s\")
print(f'Generated {len(results)} voice files')
"
```

### Step 2-4: 영상 생성 (Kling 2.6 Motion Control + Sync Lipsync v2)

원본 영상이 모션 소스 역할. 각 청크의 원본 비디오를 source_video_path로 전달:

```bash
source .venv/bin/activate
python -c "
from src.video_gen import generate_chunk_video
from pathlib import Path
import json

face_path = Path('./personas/{PERSONA_NAME}/front_face.png')
bg_path = Path('./personas/{PERSONA_NAME}/background.png')

chunk_videos = []
chunks = {CHUNKS_JSON}
for chunk in chunks:
    cid = chunk['chunk_id']
    audio = Path('{OUTPUT_DIR}/audio/' + cid + '_voice.wav')
    out = Path('{OUTPUT_DIR}/chunks/' + cid + '_video.mp4')
    source_video = Path('{VIDEO_DIR}/chunks/' + cid + '/video.mp4')
    generate_chunk_video(
        model='kling26',
        face_image_path=face_path,
        audio_path=audio,
        output_path=out,
        background_path=bg_path,
        source_video_path=source_video,
    )
    chunk_videos.append({'chunk_id': cid, 'video_path': str(out)})
    print(f'  {cid} done')

print(json.dumps(chunk_videos, indent=2))
"
```

### Step 2-5: 오디오 믹싱
```bash
source .venv/bin/activate
python -c "
from src.audio_mixing import mix_all_chunks
from pathlib import Path

results = mix_all_chunks(
    voice_dir=Path('{OUTPUT_DIR}/audio'),
    output_dir=Path('{OUTPUT_DIR}/audio'),
    chunks={CHUNKS_JSON},
    bgm_path={BGM_PATH_OR_NONE},
)
print(f'Mixed {len(results)} files')
"
```

### Step 2-6: 자막 (선택)

실제 TTS 길이 기반으로 타이밍 재계산 후 자막 생성:

```bash
source .venv/bin/activate
python -c "
from src.subtitles import recalculate_subtitle_timings, generate_ass
from src.utils import load_json
from pathlib import Path

voice_manifest = load_json(Path('{OUTPUT_DIR}/audio/voice_manifest.json'))
translation = load_json(Path('{OUTPUT_DIR}/translated_script.json'))

# Recalculate timings based on actual TTS durations
subtitle_chunks = recalculate_subtitle_timings(voice_manifest, translation['chunks'])

generate_ass(subtitle_chunks, Path('{OUTPUT_DIR}/subtitles.ass'))
print(f'Subtitles generated with {len(subtitle_chunks)} entries')
"
```

### Step 2-7: 최종 스티칭
```bash
source .venv/bin/activate
python -c "
from src.stitching import stitch_chunks
from pathlib import Path

stitch_chunks(
    chunk_videos={CHUNK_VIDEOS_JSON},
    mixed_audios={MIXED_AUDIOS_JSON},
    output_path=Path('{OUTPUT_DIR}/final.mp4'),
)
print('Stitching complete!')
"
```

자막 번인 (선택):
```bash
source .venv/bin/activate
python -c "
from src.subtitles import burn_subtitles
from pathlib import Path

burn_subtitles(
    Path('{OUTPUT_DIR}/final.mp4'),
    Path('{OUTPUT_DIR}/subtitles.ass'),
    Path('{OUTPUT_DIR}/final_subtitled.mp4'),
)
"
```

### Step 2-8: 확장 메타데이터 저장

파이프라인 완료 후 사용된 설정을 persona metadata에 저장 (다음 실행에서 재사용):

```bash
source .venv/bin/activate
python -c "
from src.persona import save_persona_metadata

save_persona_metadata(
    '{PERSONA_NAME}',
    {PERSONA_SPEC_JSON},
    '{BACKGROUND_DESC}',
    {'character_sheet_prompt': 'auto', 'background_prompt': 'auto'},
    video_model='kling26',
    tts_engine='google',
)
print('Metadata saved')
"
```

---

## Phase 3: 최종 리포트

```
전체 파이프라인 완료!

=== Phase 1: 분석 ===
data/{account}/{video_id}/
├── 영상 길이: {duration}s
├── 청크: {n_chunks}개
└── 언어: {language}

=== Phase 2: 재창조 ===
output/{video_id}/
├── final.mp4 (또는 final_subtitled.mp4)
├── 캐릭터: {persona_name}
├── 모델: Kling 2.6 + Sync Lipsync v2
├── TTS: Google Cloud ko-KR-Chirp3-HD-Leda
└── 자막: {Y/N}

personas/{persona_name}/
├── character_sheet.png
├── front_face.png
└── background.png

비용 예상:
├── 이미지: ~$0.08
├── STT: ~${stt}
├── TTS: ~${tts}
├── 영상: ~${video}
└── 총: ~${total}
```

---

## 중요 규칙

1. **모든 질문은 Phase 0에서 한번에** — 중간에 다시 묻지 않기
2. **기존 캐릭터 재사용** — `list_personas()`로 스캔, 선택하면 이미지 생성 스킵
3. **Character sheet + Background 승인 필수** — 승인 전 영상 생성 안 함
4. **이미지 미리보기** — `open` 명령으로 macOS Preview에서 확인
5. **번역 확인 필수** — 사용자 검토 후 진행
6. **Demucs → Whisper 순서 엄수** — BGM 간섭 방지
7. **자막 타이밍** — `recalculate_subtitle_timings()`로 실제 TTS 길이 기반 재계산
8. **에러 시 해당 스텝만 재시도** — 이전 결과 보존 (skip 로직 내장)
9. **진행 상황 계속 표시** — 각 스텝 완료/진행 중 상태 알려주기
10. **비용 추적** — 잔액 체크 + 예상 비용 표시
11. **모델 고정** — Kling 2.6 Motion Control + Sync Lipsync v2. 선택지 없음
12. **TTS 고정** — Google Cloud TTS `ko-KR-Chirp3-HD-Leda`. 선택지 없음
13. **메타데이터 저장** — 파이프라인 완료 후 확장 필드 저장
