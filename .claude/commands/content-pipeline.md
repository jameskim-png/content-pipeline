# /content-pipeline — 콘텐츠 파이프라인

통합 콘텐츠 생성 파이프라인. 캐릭터 관리 + 콘텐츠 생성을 하나의 진입점에서 처리.

---

## Pre-flight: 환경 체크

```bash
if [ ! -d ".venv" ]; then
    echo "First run detected. Running setup..."
    bash setup.sh
else
    source .venv/bin/activate
    python -c "import fal_client, PIL" 2>/dev/null || {
        echo "Dependencies missing. Running setup..."
        bash setup.sh
    }
fi

source .venv/bin/activate
python -c "
from dotenv import load_dotenv; import os
load_dotenv()
if not os.getenv('FAL_KEY'):
    print('MISSING_KEY: FAL_KEY')
else:
    print('ENV_OK')
"
```

- `MISSING_KEY` → 사용자에게 키 요청, `.env`에 저장 후 재확인
- `ENV_OK` → 메뉴 진행

**모든 python 명령은 `.venv/bin/python`으로 실행.**

---

## 메인 메뉴: 무엇을 할까요?

```
무엇을 할까요?

1. 캐릭터 관리
2. 콘텐츠 생성
```

---

## 경로 1: 캐릭터 관리

```
캐릭터 관리

1. 새로 만들기
2. 기존 캐릭터 보기
```

### 1-1. 새로 만들기
→ Read `prompts/character/create.md` → 해당 프롬프트의 지시에 따라 실행

### 1-2. 기존 캐릭터 보기
→ Read `prompts/character/view.md` → 해당 프롬프트의 지시에 따라 실행

---

## 경로 2: 콘텐츠 생성

### Step 1: 콘텐츠 타입 선택

```
어떤 콘텐츠를 만들까요?

1. Talking Head — AI 캐릭터 토킹헤드 릴스/숏츠
```

(향후 타입 추가 시 여기에 옵션 추가. `workflow.json`의 `content_types` 참조.)

### Step 2: 생성 방식 선택 (Talking Head)

```
어떤 방식으로 만들까요?

1. 오리지널 생성 — 제목/스크립트로 처음부터
2. 인스타 영상 재창조 — 기존 영상을 AI 캐릭터로
```

### Step 2-1: 오리지널 생성
→ Read `prompts/talking-head/create.md` → 해당 프롬프트의 지시에 따라 실행

### Step 2-2: 인스타 영상 재창조
→ Read `prompts/talking-head/copy.md` → 해당 프롬프트의 지시에 따라 실행

---

## 라우터 규칙

1. **Pre-flight는 여기서만** — prompts/ 파일에는 pre-flight 없음
2. **얇은 라우터** — 선택 로직만. 실제 파이프라인은 prompts/ 파일에 위임
3. **캐릭터는 shared resource** — 어떤 콘텐츠 타입에서든 재사용 가능
4. **콘텐츠 생성 시 캐릭터 연동** — 각 파이프라인 내에서 `list_personas()` 스캔 → 기존 캐릭터 선택 or "새로 만들기" 선택 시 `prompts/character/create.md` 로직 인라인 실행
5. **workflow.json 참조** — 새 타입 추가 시 `content_types`에 키 추가 + `prompts/{type}/` 폴더 생성
