# content-pipeline

AI 콘텐츠 생성 파이프라인 (Claude Code 기반). 캐릭터 관리 + 다양한 콘텐츠 타입 생성.

## 사용법
1. `bash setup.sh` — 환경 셋업 (venv, ffmpeg, API 키)
2. Claude Code에서 `/content-pipeline` 실행

## 커맨드
- `/content-pipeline` — 통합 진입점 (캐릭터 관리 + 콘텐츠 생성)

## 콘텐츠 타입
- **Talking Head** — AI 캐릭터 토킹헤드 릴스/숏츠
  - 오리지널 생성: 제목/스크립트 → 영상
  - 인스타 재창조: Instagram 영상 → AI 캐릭터로 재창조
- **Narration Reel** — AI 생성 장면 + 나레이션 릴스/숏츠
  - 오리지널 생성: 주제 → 씬 이미지 + 애니메이션 + 나레이션
  - 인스타 재창조: Instagram 영상 → AI 장면으로 재창조

## 기술 스택
- **Talking Head 영상 생성**: Grok Imagine Video (fal.ai) + Sync Lipsync v2
- **Narration Reel 이미지**: Flux 1.1 Pro (fal.ai)
- **Narration Reel 영상**: Grok Imagine Video (fal.ai, lip sync 없음)
- **TTS**: Google Cloud TTS `ko-KR-Chirp3-HD-Leda`
- **STT**: fal.ai Whisper (copy 파이프라인)
- **오디오 분리**: Demucs (로컬)

## 실행 규칙
- 모든 python 실행: `.venv/bin/python` 사용
- bg removal 절대 금지 (white fringe 발생, Talking Head만 해당)
- Talking Head: 캐릭터는 배경 위에 직접 생성, 레퍼런스 이미지 9:16 (720x1280)
- Narration Reel: 캐릭터 없음, 씬마다 다른 AI 이미지 생성, 무음 클립 concat → 나레이션 오버레이

## API 키
- `FAL_KEY` (필수) — fal.ai 계정 키
- Google Cloud TTS — `gcloud auth` 인증 필요
