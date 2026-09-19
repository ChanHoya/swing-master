# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

프로젝트 규칙(절대 규칙·작업 프로토콜·커밋 규칙·문서 읽기 순서)은 `AGENTS.md` 에 있고
아래에서 import 한다. **여기에 그 내용을 다시 쓰지 말 것.**
이 파일에는 AGENTS.md 에 없는 것 — 실행 명령과 코드 구조의 배경 — 만 적는다.

@AGENTS.md

---

## 명령어

### 백엔드 (`backend/`)

가상환경은 `backend/.venv` 다. 활성화하지 않고 `.venv/bin/<도구>` 를 직접 부르는 것이 이 저장소의 관례다.

```bash
cd backend
.venv/bin/uvicorn app.main:app --reload --port 8000   # 개발 서버
.venv/bin/pytest tests/ -q                            # 전체 테스트 (141개)
.venv/bin/pytest tests/swing/test_metrics_tempo.py -q # 파일 하나
.venv/bin/pytest tests/swing/test_phases.py::test_이름 # 테스트 하나
.venv/bin/alembic upgrade head                        # 마이그레이션
.venv/bin/python scripts/verify_axes.py <영상경로>      # MediaPipe world 축 방향 검증
```

**pytest 출력을 `tail`/`head`/`grep` 으로 파이프하지 말 것.** 종료 코드가 파이프 끝 명령의
것으로 가려져 실패한 테스트를 통과로 착각한다. 실제로 그렇게 깨진 커밋이 있었다
(`docs/superpowers/plans/HANDOFF-2026-09-17.md`). 꼭 줄여 봐야 하면:

```bash
.venv/bin/pytest tests/ -q > /tmp/pt.txt 2>&1; EXIT=$?; tail -5 /tmp/pt.txt; echo "EXIT=$EXIT"
```

`ruff`/`mypy` 는 `pyproject.toml` 에 선언돼 있지만 `.venv` 에 설치돼 있지 않다.
실제 설치 목록은 `requirements.txt`(런타임) + `requirements-dev.txt`(pytest 뿐)다.

### 프론트엔드 (`frontend/`)

**패키지 매니저는 npm 이다** (`package-lock.json`). AGENTS.md 의 `pnpm tsc --noEmit` 은
오래된 표기이므로 아래를 쓴다.

```bash
cd frontend
npm run dev            # 개발 서버 :3000
npx tsc --noEmit       # 타입 검증 — AGENTS.md 의 필수 검증 단계
npm run lint
npm run build
```

### 의존성 버전의 진실 공급원

`backend/pyproject.toml` 과 `docs/02_tech_stack.md` 의 버전은 실제와 어긋난다
(pyproject: fastapi ^0.115 / Python 3.11, 실제: `requirements.txt` fastapi 0.136 + Docker Python 3.13).
설치 버전을 확인할 때는 **`backend/requirements.txt` 와 `frontend/package.json`** 을 본다.

---

## 아키텍처

### 요청 한 건의 수명

```
POST /upload  →  R2 업로드 → uploads/analyses 행 생성(status=queued)
              →  BackgroundTasks 로 process_pose_estimation(upload_id) 던지고 즉시 응답
GET /analysis/{upload_id}/status   ← 프론트가 폴링 (queued→processing→done/failed)
GET /analysis/{upload_id}/result   ← done 이 되면 한 번 가져온다
```

분석은 요청-응답 밖에서 도는 **같은 프로세스의 백그라운드 작업**이다. 워커도 큐도 없다.
따라서 서버를 재시작하면 진행 중이던 분석은 `processing` 에서 멈춘 채 남는다.

### 분석 파이프라인 (`backend/app/services/swing/`)

`pipeline.py` 가 오케스트레이션(다운로드·DB·R2·asyncio)을 혼자 맡고, 나머지 모듈은
바깥 세상을 모른다. 이 경계가 이 패키지의 핵심 설계다.

| 모듈 | 책임 | 의존성 |
|---|---|---|
| `types.py` | `MetricValue`, `PoseSequence`, `PHASE_KEYS` | numpy 뿐 |
| `metrics.py` | 지표 8개 계산 — **순수 함수만** | numpy 뿐 |
| `phases.py` | 스윙 구간 탐지(`detect_swing_window`) + 7단계 분할(`detect_phases`) | cv2, numpy |
| `pose.py` | MediaPipe 3D world + 2D 픽셀 랜드마크 추출 | mediapipe, supervision, cv2 |
| `tracks.py` | 프레임별 손 궤적(0~1 정규화) | numpy |
| `overlay.py` | 단계별 스켈레톤 이미지 렌더 | supervision, cv2 |
| `pipeline.py` | 위를 엮고 R2·DB에 쓴다 | 전부 + httpx, sqlalchemy |

`metrics.py` 에 numpy 외 의존성을 추가하지 말 것. 실제 영상 없이 합성 좌표로
테스트할 수 있는 것이 이 제약 덕분이고, 테스트 141개 중 대부분이 그 방식이다.

CPU를 오래 쓰는 단계(`detect_swing_window`, `extract_sequence`, `_render_phase_overlays`,
boto3 업로드)는 전부 `loop.run_in_executor` 로 내보낸다. 동기 함수를 파이프라인에
직접 `await` 없이 부르면 이벤트 루프가 멈춘다.

### 지표를 지어내지 않는다 — 이 저장소의 제1 불변식

`MetricValue.value` 가 `None` 인 경우는 두 가지이고 **화면에서 다르게 안내해야 한다.**

- `measurable=False` — 이 촬영 각도에서는 애초에 계산할 수 없다 (`METRIC_ANGLES` 게이팅).
  수평 회전 3종은 `down_the_line` 전용, 좌우 이동 2종은 `face_on` 전용이다.
- `measurable=True, value=None` — 각도는 맞았는데 랜드마크가 부족해 실패했다.

게이팅을 통과해도 `METRIC_LIMITS` 범위를 벗어나면 값을 버린다. 촬영 각도를 잘못 고르면
환산 배율이 폭발해 head_movement 141cm 같은 값이 나오기 때문이다. 기본값으로 메우지 말 것.

`evaluate()` 도 같은 원칙이다. 측정된 지표가 하나도 없으면 `overall_score` 는 `None` 이다.

### 규칙 엔진과 LLM의 관계 (뒤집혀 있다)

진단·점수·등급·드릴은 **`feedback/rules.py` 가 확정**한다. `feedback/llm.py` 의 `polish()` 는
Gemini로 한국어 문장(`feedback`·`tip`·`encouragement`)만 다듬는다.

`polish()` 는 LLM 응답을 신뢰하지 않는다 — 각 필드를 타입 검증한 뒤에만 반영하고,
숫자·등급·이슈 개수·드릴 구성은 절대 덮어쓰지 못하며, 어떤 응답이 와도 예외를 던지지 않고
입력을 그대로 돌려준다. **LLM이 죽어도 규칙 결과가 그대로 서비스된다.**
LLM 쪽에 기능을 더할 때 이 성질을 깨지 말 것.

Gemini 키는 `settings.GEMINI_API_KEY` 를 우선 읽고 `os.getenv` 는 폴백이다.
`OPENAI_*` 설정은 config 에 남아 있으나 현재 코드 경로에서 쓰지 않는다.

### 프론트엔드와 백엔드가 공유하는 계약

`frontend/src/lib/metrics.ts` 의 `METRIC_META`(label·ideal·tolerance)는
`backend/app/services/feedback/rules.py` 의 `RULES` 를 **손으로 복제한 것**이다.
`metricFillRatio()` 도 `score_metric()` 과 같은 계산을 다시 쓴 것이다.
한쪽의 기준값·허용폭을 바꾸면 반드시 다른 쪽도 같이 바꿔야 레이더 차트와 점수가 어긋나지 않는다.

`metrics` 페이로드의 `_meta` 키는 지표가 아니라 재생용 부가 정보다
(`camera_angle`, `swing_start_sec`/`swing_end_sec`, `phase_seconds`, `tracks.hands`, 측정 개수).
지표만 순회할 때 `_meta` 가 섞이면 안 된다 — 백엔드는 `evaluate()`/`summarise_metrics()` 에
넘기기 전에 `_meta` 를 빼고, 프론트는 `METRIC_ORDER` 화이트리스트만 돈다.
`_meta` 의 필드는 예전 분석 결과에는 없으므로
`readMeta()`/`readMetric()` 처럼 타입 가드로 꺼낸다. 없다고 화면이 깨지면 안 된다.

### 인증 — 업로드는 선택, 히스토리는 필수

`core/auth.py` 에 의존성 두 개가 있다. `get_current_user_id` 는 토큰이 없으면 401,
`get_optional_user_id` 는 없으면 `None` 을 돌려준다. 업로드는 비로그인으로도 되어야 하므로
(`ANON_DAILY_LIMIT` 설계) 후자를 쓴다. 토큰은 프론트의 `AuthContext` 가 localStorage 에 두고
axios 기본 헤더에 실어 보낸다. 리프레시 토큰은 없다.

### 분석 결과 화면 (`frontend/src/app/analysis/[id]/page.tsx`, 934줄)

이 저장소에서 가장 큰 파일이고 최근 작업이 몰려 있는 곳이다. 한 파일 안에
레이더 차트·점수 링·7단계 카드·영상 재생 제어(구간 반복, 0.1~1배속, 스윙 구간 크롭)와
손 궤적 캔버스 오버레이(`drawHandPath`)가 같이 있다. 궤적 좌표는 0~1 정규화라
`containRect()` 로 레터박스를 계산해 화면 픽셀로 환산한다.

### 배포

- 백엔드: Railway, **nixpacks 가 아니라 `backend/Dockerfile`**. 빌드 컨텍스트는 저장소 루트라
  Dockerfile 안의 경로가 `backend/` 로 시작한다. 이걸 `backend/` 기준으로 착각하면 빌드가 깨진다.
  `fonts-nanum` 이 빠지면 오버레이 라벨이 "3.탑" 대신 "3" 으로만 나온다.
- 프론트엔드: Vercel, 루트 `vercel.json` 이 `cd frontend && npm run build` 를 돈다.

### 저장소 안의 비-코드 디렉터리

- `NewUI/` — 정적 HTML 와이어프레임. 빌드에 들어가지 않는 디자인 참고물이다.
- `docs/superpowers/`, `.superpowers/sdd/` — 지난 설계 문서·계획서·작업 리포트.
  특히 `docs/superpowers/plans/HANDOFF-2026-09-17.md` 에 미결 검증 항목이 정리돼 있다.
- `backend/app/services/pose_estimator.py`, `llm_feedback.py` — 각각 `swing/pipeline.py`,
  `feedback/llm.py` 로 옮겨 가고 남은 재export 래퍼다. 새 코드는 새 경로를 쓴다.
