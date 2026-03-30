# Narration Reel -- 오리지널 생성

주제에서 AI 이미지 + 애니메이션 + 나레이션 릴스를 처음부터 생성하는 파이프라인.
Talking Head와 달리 캐릭터가 없고, 씬마다 다른 AI 이미지를 생성해서 애니메이션화한 뒤 나레이션을 오버레이.
TTS 엔진 고정: Chirp3-HD (음성은 언어에 따라 자동 결정).

---

## Phase 0: 사용자 입력

### Q1. 주제/제목

```
어떤 주제의 나레이션 릴스를 만들까요?
(예: "냉장고의 NG 습관 6선", "일본 쇼와시대 미스터리", "우주에서 가장 위험한 물질 TOP 5")
```

### Q2. 시각 스타일

```
씬 이미지의 시각 스타일을 선택해주세요:

1. 3D Pixar — 밝고 귀여운 3D 애니메이션 (기본)
2. 빈티지 흑백 — 레트로/역사 다큐 느낌
3. 애니메이션 — 일본 애니 스타일
4. 포토리얼 — 사실적인 사진 스타일
5. 커스텀 — 직접 입력
```

스타일 프리셋 → `STYLE_PROMPT`:
- 3D Pixar: `"3D Pixar-style illustration, vibrant colors, soft studio lighting, rounded shapes, clean background"`
- 빈티지 흑백: `"Vintage black and white photograph, film grain, dramatic lighting, 1940s aesthetic"`
- 애니메이션: `"Anime illustration style, detailed background, cel shading, vibrant colors, studio Ghibli inspired"`
- 포토리얼: `"Photorealistic, high detail, natural lighting, 8K quality, professional photography"`
- 커스텀: 사용자 입력을 영어로 변환

### Q3. 목표 길이

```
영상 목표 길이를 선택해주세요:

1. ~30초 (기본)
2. ~60초
3. ~90초
```

### Q4. 콘텐츠 언어

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

-> `VOICE_NAME`, `LANGUAGE_LABEL`, `LANG_CODE` 변수 설정

### Q5. 자막 스타일

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

- 스타일 선택 -> `SUBTITLE_STYLE`, `SUBTITLES=Y`
- "없음" -> `SUBTITLES=N`
- "미리보기" -> HTML 프리뷰 후 다시 선택
- "새 스타일 만들기" -> 분석 + 저장

### Q6. 타이틀 오버레이

```
타이틀을 영상에 표시할까요?

1. 클린 -- 흰색, 깔끔한 스트로크
2. 임팩트 -- 노란색, 강렬한 느낌
3. 박스 -- 흰색, 배경 박스
4. 없음 (기본)
5. 미리보기 보기
```

- 프리셋 선택 시 (1~3) -> 노출 시간 질문:

```
타이틀 노출 시간:
1. 전체 (기본)
2. 첫 5초만 (페이드아웃)
```

### Q7. BGM

```
BGM을 포함할까요? (기본: 없음)
파일 경로를 입력하면 사용합니다.
```

### Q8. API 검증 + 비용 예상

```bash
source .venv/bin/activate
python -c "
from src.config import check_fal_balance, estimate_narration_cost
import json

fal = check_fal_balance()
print('fal.ai:', json.dumps(fal))

cost = estimate_narration_cost({N_CHUNKS}, {TARGET_DURATION}, tts_engine='google', total_chars={TOTAL_CHARS}, original_content=True)
print('Cost:', json.dumps(cost, indent=2))
"
```

```
잔액 + 예상 비용:
├── fal.ai: ${fal_balance}
├── TTS (Google Cloud): ~${tts_cost}
├── 이미지 (Flux): ~${image_cost} ({N_CHUNKS}장 x $0.06)
├── 영상 (Grok): ~${video_cost} ({TARGET_DURATION}초 x $0.05)
└── 총 예상 비용: ~${total}

진행할까요? (Y/N)
```

---

## Phase 1: 스크립트 생성

-> Read `prompts/narration-reel/create-phase-script.md` 실행

---

## Phase 1.5: 번역 (한국어 이외 언어 선택 시만)

한국어 이외의 언어를 선택한 경우, Phase 1에서 생성된 한국어 스크립트를 대상 언어로 번역.

```bash
source .venv/bin/activate
python -c "
from src.translation import build_translation_prompt
from src.languages import get_language_config
import json

config = get_language_config('{LANG_CODE}')
transcript = {'text': '''{FULL_SCRIPT}'''}
chunks = {CHUNKS_FOR_TRANSLATION_JSON}
prompt = build_translation_prompt(transcript, chunks, {}, target_language=config['label'])
print(prompt)
"
```

이 프롬프트로 **직접** 번역 수행 -> 사용자 확인 -> 번역된 스크립트 저장.
번역 시 `scene_description`과 `animation_prompt`는 영어 그대로 유지 (Flux/Grok 프롬프트이므로).

---

## Phase 2: Pre-generation Review

-> Read `prompts/narration-reel/create-phase-review.md` 실행

---

## Phase 3: TTS (음성 생성)

-> Read `prompts/narration-reel/create-phase-audio.md` 실행

---

## Phase 4: 씬 이미지 생성

-> Read `prompts/narration-reel/create-phase-images.md` 실행

---

## Phase 5: 씬 애니메이션

-> Read `prompts/narration-reel/create-phase-video.md` 실행

---

## Phase 6: 어셈블리 + 자막 + 타이틀

-> Read `prompts/narration-reel/create-phase-post.md` 실행

---

## Phase 7: 미리보기 + 결과 리포트

```bash
open {OUTPUT_DIR}/final.mp4
```

```
나레이션 릴스 생성 완료!

{OUTPUT_DIR}/
├── final.mp4
├── script.json
├── images/
│   ├── chunk_001_scene.png
│   └── ...
├── clips/
│   ├── chunk_001_clip.mp4
│   └── ...
└── audio/
    ├── chunk_001_voice.wav
    ├── narration.wav
    ├── voice_manifest.json
    └── ...

제목: {title}
스타일: {STYLE_NAME}
청크 수: {n_chunks}개
총 길이: ~{total_duration}초

비용 예상:
- TTS (Google Cloud): ~${tts_cost}
- 이미지 (Flux): ~${image_cost}
- 영상 (Grok): ~${video_cost}
- 총 예상 비용: ~${total_cost}
```

---

## 중요 규칙

1. **캐릭터 없음** -- Narration Reel은 persona 사용 안 함
2. **씬마다 다른 이미지** -- style_prompt로 전체 스타일 통일, scene_description으로 각 씬 차별화
3. **TTS 엔진 고정** -- Chirp3-HD. 음성은 언어에 따라 자동 결정
4. **스크립트 확인 필수** -- 사용자가 스크립트 검토 후 진행
5. **Pre-generation Review 필수** -- 비용 견적 + 승인
6. **어셈블리 순서** -- 무음 클립 concat -> 연속 나레이션 오버레이 (TH와 다름)
7. **에러 복구** -- 특정 씬 실패 시 해당 씬만 재시도 (skip 로직 내장)
8. **이미지 프롬프트 영어** -- scene_description은 영어로 (Flux 최적)
9. **비디오 프롬프트 영어** -- animation_prompt는 영어로 (Grok 최적)
10. **언어 기본값** -- 모든 기본값은 한국어 (`ko`). 다른 언어 선택 시 Phase 1.5 번역 삽입
11. **자막 스타일** -- `subtitle_styles.py` 라이브러리에서 선택
12. **BGM 믹싱** -- 나레이션 트랙과 BGM을 별도 믹싱 후 영상에 합성
