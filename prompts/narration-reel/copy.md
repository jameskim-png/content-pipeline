# Narration Reel -- 인스타 재창조

인스타그램 영상을 다운로드하고, 분석하고, AI 씬 이미지 + 나레이션으로 새로 만드는 파이프라인.
Talking Head 재창조와 달리 캐릭터가 없고, 씬마다 다른 AI 이미지를 생성해서 애니메이션화.
TTS 엔진 고정: Chirp3-HD (음성은 언어에 따라 자동 결정).
모든 질문을 처음에 한번에 물어본 후, Phase 1 (분석) -> Phase 2 (재창조)를 순차적으로 실행.

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

### Q3. 시각 스타일

```
씬 이미지의 시각 스타일을 선택해주세요:

1. 3D Pixar -- 밝고 귀여운 3D 애니메이션 (기본)
2. 빈티지 흑백 -- 레트로/역사 다큐 느낌
3. 애니메이션 -- 일본 애니 스타일
4. 포토리얼 -- 사실적인 사진 스타일
5. 원본 스타일 유추 -- 원본 영상 분석 후 스타일 결정
6. 커스텀 -- 직접 입력
```

스타일 프리셋 -> `STYLE_PROMPT` (create.md와 동일)
"원본 스타일 유추" -> Phase 1 분석 후 스타일 결정 (분석 단계에서 처리)

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

### Q6. 타이틀 오버레이

```
타이틀을 영상에 표시할까요? (분석 후 추출된 타이틀 사용)

1. 클린 -- 흰색, 깔끔한 스트로크
2. 임팩트 -- 노란색, 강렬한 느낌
3. 박스 -- 흰색, 배경 박스
4. 없음 (기본)
5. 미리보기 보기
```

### Q7. BGM
```
1. 없음 (기본)
2. BGM 파일 경로 입력
```

### Q8. API Key 검증 + 잔액 체크

```bash
source .venv/bin/activate
python -c "
from src.config import validate_keys, check_fal_balance
import json

keys = validate_keys('grok')
print('API Keys OK:')
for k, v in keys.items():
    print(f'  {k}: {v[:8]}...')

fal = check_fal_balance()
print('fal.ai:', json.dumps(fal))
"
```

---

## 설정 확인

```
설정 확인

소스: {URL} ({COUNT}개 영상)
스타일: {STYLE_NAME}
언어: {LANGUAGE_LABEL} ({VOICE_NAME})
자막: {SUBTITLE_STYLE} (또는 없음)
타이틀: {TITLE_PRESET} (또는 없음)
BGM: {BGM_OPTION}

이 설정으로 진행할까요?
```

---

## Phase 1: 영상 분석 (Analyze)

-> Read `prompts/narration-reel/copy-phase-download.md` 실행
-> Read `prompts/narration-reel/copy-phase-analyze.md` 실행

---

## Phase 2: 재창조 계획

-> Read `prompts/narration-reel/copy-phase-plan.md` 실행

---

## Phase 3: 비용 견적 + 승인

-> Read `prompts/narration-reel/copy-phase-review.md` 실행

---

## Phase 4: 번역 + TTS

-> Read `prompts/narration-reel/copy-phase-prepare.md` 실행

---

## Phase 5: 이미지 생성 + 애니메이션

-> Read `prompts/narration-reel/copy-phase-generate.md` 실행

---

## Phase 6: 어셈블리 + 자막 + 타이틀

-> Read `prompts/narration-reel/copy-phase-post.md` 실행

---

## Phase 7: 최종 리포트

```
전체 파이프라인 완료!

=== Phase 1: 분석 ===
data/{account}/{video_id}/
├── 영상 길이: {duration}s
├── 청크: {n_chunks}개
└── 언어: {language}

=== Phase 2: 재창조 ===
output/{video_id}/
├── final.mp4 (또는 final_subtitled.mp4 / final_titled.mp4)
├── 스타일: {STYLE_NAME}
├── 언어: {LANGUAGE_LABEL} ({VOICE_NAME})
└── 자막: {SUBTITLE_STYLE} (또는 없음)

비용 예상:
├── STT: ~${stt}
├── TTS: ~${tts}
├── 이미지 (Flux): ~${image}
├── 영상 (Grok): ~${video}
└── 총: ~${total}
```

---

## 중요 규칙

1. **모든 질문은 Phase 0에서 한번에** -- 중간에 다시 묻지 않기
2. **캐릭터 없음** -- Narration Reel은 persona 사용 안 함
3. **씬마다 다른 이미지** -- 원본 영상 분석으로 씬별 설명 생성
4. **번역 확인 필수** -- 사용자 검토 후 진행
5. **Demucs -> Whisper 순서 엄수** -- BGM 간섭 방지
6. **자막 타이밍** -- voice_manifest 기반 재계산
7. **어셈블리 순서** -- 무음 클립 concat -> 나레이션 오버레이
8. **에러 시 해당 스텝만 재시도** -- 이전 결과 보존
9. **진행 상황 계속 표시** -- 각 스텝 완료/진행 중 상태 알려주기
10. **비용 추적** -- 잔액 체크 + 예상 비용 표시
11. **TTS 엔진 고정** -- Chirp3-HD. 음성은 언어에 따라 자동 결정
12. **이미지/비디오 프롬프트 영어** -- Flux/Grok 최적
13. **언어 기본값** -- 모든 기본값은 한국어
