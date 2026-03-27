# content-pipeline

AI 콘텐츠 생성 파이프라인 (Claude Code 기반).

캐릭터를 만들고, 다양한 콘텐츠 타입으로 영상을 생성합니다. 현재 Talking Head 지원.

## 전제조건

- Python 3.10+
- ffmpeg
- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) CLI
- fal.ai 계정 + API 키
- Google Cloud TTS 인증 (`gcloud auth application-default login`)

## Quick Start

```bash
# 1. Clone
git clone <repo-url> && cd content-pipeline

# 2. Setup (venv + deps + API keys)
bash setup.sh

# 3. Open in Claude Code
claude

# 4. Run the pipeline
# /content-pipeline
```

## 프로젝트 구조

```
content-pipeline/
├── .claude/commands/
│   └── content-pipeline.md    # 통합 진입점 (유일한 커맨드)
├── prompts/                   # 파이프라인 프롬프트
│   ├── character/
│   │   ├── create.md          # 캐릭터 생성
│   │   └── view.md            # 캐릭터 목록 조회
│   └── talking-head/
│       ├── create.md          # 오리지널 토킹헤드 생성
│       ├── copy.md            # 인스타 영상 재창조
│       └── *-phase-*.md       # 세부 phase 프롬프트
├── src/                       # Python 모듈
│   ├── config.py              # 설정, API 키, EMOTION_CATEGORIES
│   ├── download.py            # Instagram 다운로드
│   ├── audio_separation.py    # Demucs 오디오 분리
│   ├── stt.py                 # fal.ai Whisper STT
│   ├── chunking.py            # VAD + 씬 감지 청킹
│   ├── analysis.py            # 영상 분석 프롬프트
│   ├── translation.py         # 번역 프롬프트
│   ├── persona.py             # 캐릭터 관리
│   ├── script_gen.py          # 스크립트 생성
│   ├── motion_refs.py         # 모션 레퍼런스 라이브러리
│   ├── voice.py               # TTS (Google Cloud / fal.ai)
│   ├── video_gen.py           # 영상 생성 (Kling 2.6 + Sync Lipsync)
│   ├── audio_mixing.py        # 오디오 믹싱
│   ├── subtitles.py           # 자막 생성 + 번인
│   ├── stitching.py           # 최종 영상 스티칭
│   └── utils.py               # 유틸리티
├── personas/                  # 생성된 캐릭터 (이미지 + 메타데이터)
├── data/                      # 다운로드된 원본 영상 + 분석 결과
├── output/                    # 최종 생성 영상
├── workflow.json              # 콘텐츠 타입 + 프롬프트 매핑
├── setup.sh                   # 원커맨드 환경 셋업
├── requirements.txt
├── CLAUDE.md                  # Claude Code 컨텍스트
└── README.md
```

## 콘텐츠 타입

### Talking Head

AI 캐릭터 토킹헤드 릴스/숏츠.

**오리지널 생성** (`/content-pipeline` → 콘텐츠 생성 → Talking Head → Create)
1. 스크립트 생성 (제목 → AI 생성 or 직접 입력)
2. TTS (Google Cloud)
3. 모션 레퍼런스 매칭 (emotion 태그 기반)
4. Kling 2.6 Motion Control → Sync Lipsync v2
5. 오디오 믹싱 → 스티칭

**인스타 재창조** (`/content-pipeline` → 콘텐츠 생성 → Talking Head → Copy)
1. Instagram 영상 다운로드
2. 오디오 분리 (Demucs) → STT (Whisper) → 청킹
3. 영상 분석 (표정, 동작, BGM)
4. 캐릭터 선택/생성 → 번역 → TTS
5. Kling 2.6 Motion Control (원본 영상이 모션 소스)
6. Sync Lipsync v2 → 오디오 믹싱 → 스티칭

## API 키 설정

`.env` 파일에 추가:
```
FAL_KEY=your_fal_ai_key
```

Google Cloud TTS는 별도 인증:
```bash
gcloud auth application-default login
```

## 새 콘텐츠 타입 추가

1. `workflow.json`의 `content_types`에 키 추가
2. `prompts/{type}/` 폴더에 프롬프트 작성
3. `/content-pipeline` 라우터에 옵션 추가

## License

Private repository.
