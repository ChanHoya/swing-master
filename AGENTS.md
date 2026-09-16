# Swing Master — AI Agent Entry Point

> **이 파일을 가장 먼저 읽으세요.**
> Antigravity / Claude Code 등 모든 에이전트의 공통 진입점입니다.
> 사람용 요약은 `README.md`를 참고하세요.

## 프로젝트 한 줄 정의

**Swing Master** — 골프 스윙 영상을 올리면 AI가 자세를 분석하고 교정 피드백과 드릴을 제공하는 서비스.

## 현재 상태

- **Phase**: 개발 진행 중. `docs/04_roadmap_7days.md` 기준 50개 완료 / 6개 미완료.
- **배포**: 백엔드 Railway (`railway.toml`), 프론트엔드 Vercel (`vercel.json`).
- 시작 전 `docs/04_roadmap_7days.md` 체크박스로 현재 지점을 먼저 확인할 것.

## 실제 구조

```
swing-master/
├── backend/                    # FastAPI 0.136 + uvicorn, alembic 마이그레이션
│   └── app/
│       ├── api/endpoints/      # analysis, auth, health, history, upload
│       ├── core/config.py      # Pydantic Settings (환경변수 로딩)
│       ├── services/
│       │   ├── pose_estimator.py       # MediaPipe 0.10.33 (서버 사이드)
│       │   ├── pose_landmarker_lite.task   # 5.5MB 모델
│       │   └── llm_feedback.py         # Gemini 호출 (httpx)
│       └── models.py
├── frontend/                   # Next.js App Router + React Query + axios
│   └── src/{app,components,context,lib}
├── NewUI/                      # 정적 HTML 프로토타입 (capture, coach, compare, drill …)
├── docs/                       # 00~07 사양 문서
└── .agents/                    # 서브에이전트 정의
```

## 에이전트 읽기 순서

| 순서 | 파일 | 목적 |
|------|------|------|
| 1 | `docs/00_overview.md` | 서비스 정의 & 성공 기준 |
| 2 | `docs/04_roadmap_7days.md` | **현재 어디까지 됐는지 체크박스 확인** |
| 3 | `docs/01_architecture.md` | 시스템 구조 & 데이터 흐름 |
| 4 | `docs/02_tech_stack.md` | 기술 스택 & 버전 |
| 5 | `docs/03_features_mvp.md` | MVP 기능 명세 |
| 6 | `docs/05_prompts.md` | LLM 프롬프트 템플릿 |
| 7 | `docs/06_data_schema.md` | Pose JSON & 분석 결과 타입 |
| 8 | `docs/07_risks.md` | 리스크 & 대응 |

## 서브에이전트 정의

| 파일 | 담당 영역 |
|------|-----------|
| `.agents/frontend.md` | Next.js UI & 사용자 인터랙션 |
| `.agents/vision.md` | 포즈 추정 & 영상 처리 파이프라인 |
| `.agents/llm-integration.md` | LLM API 연동 & 프롬프트 관리 |

## 절대 규칙 (위반 시 작업 중단)

- **TypeScript strict 모드** 필수. `any` 사용 금지 (`unknown` + 타입 가드 사용).
- **API 키는 절대 클라이언트 코드에 포함 금지.** 모든 LLM 호출은 백엔드를 경유한다.
- **카메라/마이크 권한 처리는 항상 try-catch + 사용자 안내 메시지**를 동반한다.
- **새 기능 추가/완료 시 `docs/04_roadmap_7days.md` 체크박스를 업데이트**한다.
- **모든 사용자 노출 텍스트는 한국어.** 코드 주석은 영어/한국어 모두 허용.

## 작업 진행 프로토콜

작업 1건 = 4단계.

1. **계획** — 무엇을 어떤 파일에 어떻게 만들지 1~3줄 요약 후 시작.
2. **구현** — 코드 작성.
3. **검증** — 프론트는 `pnpm tsc --noEmit`, 백엔드는 해당 테스트. 가능하면 모바일 뷰포트에서 동작 확인.
4. **기록** — `docs/04_roadmap_7days.md`의 해당 체크박스 `[ ]` → `[x]`.

## 커밋 규칙

```
feat: 새 기능 추가
fix: 버그 수정
docs: 문서 변경
refactor: 리팩토링 (동작 변경 없음)
chore: 빌드/설정 변경
```

Day 단위 작업은 메시지 앞에 `[Day N]` 태그. 예: `feat(pose): [Day 1] add MediaPipe overlay`.

## 막혔을 때

1. `docs/07_risks.md`의 해당 리스크 대응책을 먼저 확인한다.
2. 그래도 막히면 **작업을 중단하고 사용자에게 옵션을 제시**한다.
3. **자체 판단으로 기술 스택/아키텍처를 변경하지 않는다.** 반드시 사용자 승인 후 진행.
4. 라이브러리 버전 충돌 시 `docs/02_tech_stack.md`에 명시된 버전을 우선한다.

## TODO — 초기 설계와 현재 구현이 갈린 지점

아래는 사람이 결정해야 한다. 에이전트가 임의로 한쪽에 맞추지 말 것.

- **포즈 추정 위치.** 초기 설계는 "100% 클라이언트(브라우저 WASM), 서버로 비디오 전송 금지"였으나,
  현재는 `backend/app/services/pose_estimator.py`에서 서버 사이드로 처리한다.
  개인정보(영상 서버 전송) 관점의 재검토가 필요하다. `docs/01_architecture.md`도 함께 갱신할 것.
- **LLM 호출 추상화.** 초기 설계는 "`LLMProvider` 인터페이스 경유, SDK 직접 호출 금지"였으나,
  현재 `llm_feedback.py`는 httpx로 Gemini를 직접 호출한다. 또한 API 키를 `core/config.py`의
  Pydantic `Settings`가 아니라 `os.getenv("GEMINI_API_KEY")`로 따로 읽고 있어 설정 경로가 이원화돼 있다.
