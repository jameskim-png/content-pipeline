# content-pipeline

AI 콘텐츠 생성 파이프라인 (Claude Code 기반).

캐릭터를 만들고, 다양한 콘텐츠 타입으로 릴스/숏츠 영상을 생성합니다.

## 콘텐츠 타입

### 1. Talking Head — AI 캐릭터 토킹헤드

AI 캐릭터가 카메라를 보고 말하는 영상. 립싱크 포함.

| | Create (오리지널) | Copy (인스타 재창조) |
|---|---|---|
| **입력** | 제목/스크립트 | Instagram URL |
| **캐릭터** | 기존 선택 or 새로 생성 | 기존 선택 or 새로 생성 |
| **영상 생성** | Grok + Sync Lipsync | Grok + Sync Lipsync |
| **오디오** | TTS | 원본 BGM + TTS |
| **비용** | ~$2.10/30초 | ~$2.15/30초 |

**Create 흐름:**
스크립트 → TTS → Grok 영상 → Sync Lipsync → 어셈블리 + 자막/타이틀

**Copy 흐름:**
다운로드 → Demucs 분리 → Whisper STT → 청킹 → 번역 → TTS → Grok → Lipsync → BGM 믹스 → 어셈블리

### 2. Narration Reel — AI 장면 + 나레이션

씬마다 AI 이미지를 생성하고 애니메이션화, 나레이션 보이스오버.

| | Create (오리지널) | Copy (인스타 재창조) |
|---|---|---|
| **입력** | 주제 + 시각 스타일 | Instagram URL |
| **이미지** | Flux 1.1 Pro | Flux 1.1 Pro |
| **영상** | Grok Imagine Video (무음) | Grok Imagine Video (무음) |
| **오디오** | TTS 나레이션 | 원본 분석 → TTS |
| **비용** | ~$1.80/30초 | ~$2.00/30초 |

**Create 흐름:**
스크립트+씬 설명 → TTS → Flux 이미지 → Grok 애니메이션 → 클립 결합 + 나레이션 오버레이

**Copy 흐름:**
다운로드 → 분석 (STT/프레임) → 재창조 스크립트 → TTS → Flux → Grok → 어셈블리

---

## Quick Start

```bash
# 1. Clone
git clone <repo-url> && cd content-pipeline

# 2. Setup (venv + deps + API keys)
bash setup.sh

# 3. Claude Code에서 실행
claude
# /content-pipeline
```

## 전제조건

- Python 3.10+
- ffmpeg
- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) CLI
- fal.ai 계정 + API 키 (`FAL_KEY`)
- Google Cloud TTS 인증 (`gcloud auth application-default login`)

## API 키 설정

`.env` 파일:
```
FAL_KEY=your_fal_ai_key
```

Google Cloud TTS:
```bash
gcloud auth application-default login
```

---

## 기술 스택

### 영상 생성
| 모델 | 용도 | API |
|------|------|-----|
| **Grok Imagine Video** | 토킹헤드 영상 / 씬 애니메이션 | fal.ai |
| **Sync Lipsync v2** | 립싱크 합성 (토킹헤드) | fal.ai |
| **Flux 1.1 Pro** | 씬 이미지 생성 (나레이션 릴) | fal.ai |
| Kling 2.6 Motion Control | 모션 트랜스퍼 (대안) | fal.ai |
| VEO 3 | 영상 생성 (대안) | fal.ai |
| HeyGen | 포토 아바타 (대안) | HeyGen API |

### 음성 & 오디오
| 엔진 | 용도 | API |
|------|------|-----|
| **Google Chirp3-HD** | TTS (기본) | Google Cloud |
| ElevenLabs | TTS (대안) | ElevenLabs |
| fal.ai F5-TTS | TTS (폴백) | fal.ai |
| Demucs | 오디오 분리 (로컬) | - |
| Whisper | STT (음성→텍스트) | fal.ai |

### 지원 언어
| 언어 | 코드 | TTS 음성 |
|------|------|---------|
| 한국어 | ko | ko-KR-Chirp3-HD-Leda |
| 日本語 | ja | ja-JP-Chirp3-HD-Leda |
| English | en | en-US-Chirp3-HD-Leda |
| 中文 | zh | cmn-CN-Chirp3-HD-Leda |
| Español | es | es-ES-Chirp3-HD-Leda |

---

## 프로젝트 구조

```
content-pipeline/
├── .claude/commands/
│   └── content-pipeline.md        # 통합 진입점 (/content-pipeline)
├── prompts/
│   ├── character/
│   │   ├── create.md              # 캐릭터 생성
│   │   └── view.md                # 캐릭터 목록
│   ├── talking-head/
│   │   ├── create.md              # TH 오리지널
│   │   ├── copy.md                # TH 인스타 재창조
│   │   └── *-phase-*.md           # 세부 phase
│   └── narration-reel/
│       ├── create.md              # NR 오리지널
│       ├── copy.md                # NR 인스타 재창조
│       └── *-phase-*.md           # 세부 phase
├── src/
│   ├── config.py                  # 설정, API 키, 비용 추정
│   ├── persona.py                 # 캐릭터 생성/관리
│   ├── motion_refs.py             # 모션 레퍼런스 라이브러리 (Kling26)
│   ├── download.py                # Instagram 다운로드
│   ├── audio_separation.py        # Demucs 4-stem 분리
│   ├── stt.py                     # Whisper STT
│   ├── chunking.py                # VAD + 씬 감지 청킹
│   ├── analysis.py                # 영상 분석 프롬프트
│   ├── script_gen.py              # 스크립트 생성
│   ├── translation.py             # 번역
│   ├── languages.py               # 언어 설정 + TTS 음성 매핑
│   ├── voice.py                   # TTS (Google/ElevenLabs/fal)
│   ├── image_gen.py               # Flux 씬 이미지 생성
│   ├── video_gen.py               # 영상 생성 (Grok/Kling/VEO/HeyGen)
│   ├── review.py                  # 프리-제너레이션 검증
│   ├── audio_mixing.py            # 오디오 믹싱
│   ├── stitching.py               # TH 어셈블리
│   ├── narration_stitch.py        # NR 어셈블리 (싱크 나레이션)
│   ├── subtitles.py               # SRT/ASS 자막 + 번인
│   ├── subtitle_styles.py         # 자막 스타일 라이브러리
│   ├── titles.py                  # 타이틀 오버레이 + HTML 프리뷰
│   └── utils.py                   # JSON, ffmpeg 유틸
├── personas/                      # 생성된 캐릭터
├── data/                          # 다운로드/분석 데이터
├── output/                        # 최종 영상
├── assets/fonts/                  # Pretendard 폰트
├── workflow.json                  # 콘텐츠 타입 라우팅
├── setup.sh                       # 환경 셋업
└── requirements.txt
```

## 모듈 관계

```
[Instagram URL]
     │
     ▼
download.py ──► audio_separation.py ──► stt.py
     │                                    │
     ▼                                    ▼
  [video]                           chunking.py
                                        │
                                        ▼
                                   analysis.py ──► translation.py
                                                       │
                                                       ▼
[사용자 입력] ──► script_gen.py ──────────────────► voice.py (TTS)
                      │                                │
                      ▼                                ▼
               persona.py ──► video_gen.py ◄──── [voice WAV]
                                   │
                    ┌──────────────┼──────────────┐
                    ▼              ▼              ▼
            image_gen.py    Grok/Kling26    Sync Lipsync
            (NR only)       + motion_refs     (TH only)
                    │              │              │
                    ▼              ▼              ▼
              narration_stitch.py    stitching.py
                    │                     │
                    ▼                     ▼
              subtitles.py ──► titles.py
                                   │
                                   ▼
                              [final.mp4]
```

---

## 새 콘텐츠 타입 추가

1. `workflow.json`의 `content_types`에 키 추가
2. `prompts/{type}/` 폴더에 create.md, copy.md + phase 파일 작성
3. `.claude/commands/content-pipeline.md` 메뉴에 옵션 추가
4. 필요한 `src/` 모듈 추가 (기존 모듈 최대 재사용)

## License

Private repository.
