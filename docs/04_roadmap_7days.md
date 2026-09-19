# 04. 7일 로드맵 (Roadmap)

> 체크박스는 완료 시 `[x]`로 변경하세요.

---

## Day 1 — 프로젝트 초기화 & 기반 구축 ✅

### Backend
- [x] `backend/` 디렉토리 init (`pyproject.toml`, FastAPI 앱 뼈대)
- [x] `/health` 엔드포인트 구현 & 테스트
- [x] Supabase 프로젝트 생성 & 연결 (`DATABASE_URL` 환경변수) — `.env.example` 구성 완료 (실제 연결은 Supabase 계정 생성 후)
- [x] `users`, `analyses` 테이블 마이그레이션 (Alembic) — `alembic/versions/001_initial_schema.py` 완료
- [x] Cloudflare R2 버킷 생성 & boto3 연결 테스트 — `app/core/storage.py` 완료 (실제 버킷은 계정 생성 후)

### Frontend
- [x] `frontend/` Next.js (16.2.4) 프로젝트 init (`npx create-next-app`)
- [x] 기본 레이아웃 컴포넌트 (Header, Footer)
- [x] 영상 업로드 UI 컴포넌트 (드래그앤드롭)
- [ ] Vercel 배포 연결 — `vercel.json` 구성 완료, GitHub push 후 연결 필요

### 완료 기준
> `/health` 응답 OK + Vercel 배포 URL 생성

---

## Day 2 — 영상 업로드 파이프라인 ✅

### Backend
- [x] `POST /upload` 엔드포인트 구현
  - [x] 파일 검증 (크기, 형식, 길이)
  - [x] R2 업로드 → 스토리지 URL 반환
  - [x] `analyses` 레코드 생성 (status: `queued`)
- [x] 백그라운드 태스크 큐 구성 (FastAPI BackgroundTasks)

### Frontend
- [x] 업로드 API 연동 (React Query mutation)
- [x] 프로그레스 바 구현
- [x] 업로드 완료 후 분석 상태 폴링 시작

### 완료 기준
> 영상 업로드 → R2 저장 → DB 레코드 생성 E2E 확인

---

## Day 3 — 포즈 추정 엔진 구현 ✅

### Backend
- [x] MediaPipe 포즈 추정 모듈 (`services/pose_estimator.py`) — Tasks API (PoseLandmarker) 사용
- [x] 핵심 프레임 자동 감지 (어드레스 / 탑 / 임팩트) — 손목 Y좌표 휴리스틱
- [x] 스윙 지표 계산 함수 구현 (spine_angle, head_movement, tempo_ratio)
- [x] 오버레이 이미지 생성 (어깨·골반선, 척추 라인, 관절) 후 R2 업로드
- [x] 3프레임 스킵 최적화로 처리 속도 단축

### 완료 기준
> 샘플 영상 → 스윙 지표 JSON + 오버레이 이미지 URL 출력 ✅

---

## Day 4 — LLM 피드백 생성 ✅

### Backend
- [x] Gemini API 클라이언트 설정 (httpx 직접 REST 호출 방식, `services/llm_feedback.py`)
- [x] 스윙 지표 → 프롬프트 포맷터 (docs/05_prompts.md 기반 템플릿 사용)
- [x] Gemini 호출 → 교정 피드백 JSON 파싱
- [x] 드릴 추천 생성 & 구조화 (top_issues + drills)
- [x] `GET /analysis/{id}/result` 엔드포인트
- [x] `GET /analysis/{upload_id}/status` 폴링 엔드포인트

### 완료 기준
> 포즈 분석 결과 → Gemini 호출 → 한국어 피드백 JSON 반환 ✅

---

## Day 5 — 결과 화면 UI ✅

### Frontend
- [x] 분석 상태 로딩 화면 (애니메이션 스피너)
- [x] 종합 점수 링 (SVG 애니메이션, 등급별 색상)
- [x] 스윙 지표 레이더 차트 (SVG, 외부 라이브러리 없음)
- [x] 교정 피드백 카드 컴포넌트 (심각도 배지 포함)
- [x] 드릴 추천 카드 컴포넌트 (단계·반복횟수·팁)
- [x] 스켈레톤 오버레이 이미지 뷰어 (hover 줌인 효과)
- [x] API 에러 시 안내 UI (재시도 버튼 포함)

### 완료 기준
> 분석 완료 후 결과 페이지 전체 렌더링 확인 ✅

---

## Day 6 — 히스토리 & 인증 ✅

### Backend
- [x] `POST /auth/register`, `POST /auth/login` (bcrypt 해시 + JWT 발급)
- [x] `GET /history` (사용자별 분석 이력, JWT 인증 가드)

### Frontend
- [x] 로그인/회원가입 모달 (탭 전환, 에러 핸들링)
- [x] `AuthContext` — 전역 로그인 상태 + localStorage 영속화
- [x] 히스토리 페이지 (`/history`) — 분석 목록 카드 + 통계 (총 분석수, 평균 점수)
- [x] 헤더 로그인 버튼 / 로그인 상태 이메일 표시 / 로그아웃

### 완료 기준
> 로그인 후 이전 분석 결과 조회 가능 ✅

---

## Day 7 — QA, 최적화, 배포 🚧

### 성능 최적화 (분석 속도 10초 이내 목표)
- [x] PoseLandmarker 싱글톤 캐싱 (재로딩 2~3초 절감)
- [x] 2프레임 스킵 (`swing/pose.py` 의 `skip=2`)
- [x] 640p 리사이즈 전처리 (MediaPipe 추론 속도 4배 향상)
- [ ] 최대 150프레임 처리 후 조기 종료 — **미구현.** 완료로 표시돼 있었으나
      코드에 해당 로직이 없다 (2026-09-18 확인)
- [x] R2 업로드 + Gemini 피드백 병렬(asyncio.gather) 실행

### 에러 핸들링 정비
- [x] 모든 Gemini 모델 4종 Fallback 체인 (503/429 자동 전환)
- [x] 분석 실패 시 `status: failed` DB 기록 & UI 에러 메시지

### 배포 준비
- [x] `vercel.json` — 프론트엔드 배포 설정
- [x] `railway.toml` — 백엔드 배포 설정
- [x] `backend/requirements.txt` 생성
- [ ] Vercel GitHub 연동 + 환경변수 등록
- [ ] Railway 백엔드 배포 + 환경변수 등록

### 추가 QA
- [x] 분석 소요 시간 측정 → **9.5초** 확인 (2026-09-18, 1080×1080/30fps/8.7초 영상)
- [x] 에러 핸들링 & 사용자 에러 메시지 정비 — 측정 실패를 두 가지로 구분해 안내
- [ ] 클로즈드 베타 초대 링크 배포

### 완료 기준
> 분석 10초 이내 + Vercel/Railway 배포 URL 생성

---

## 전체 진행현황

| Day | 주요 목표 | 상태 |
|-----|-----------|------|
| 1 | 프로젝트 초기화 | ✅ 완료 |
| 2 | 업로드 파이프라인 | ✅ 완료 |
| 3 | 포즈 추정 엔진 | ✅ 완료 |
| 4 | LLM 피드백 생성 | ✅ 완료 |
| 5 | 결과 화면 UI | ✅ 완료 |
| 6 | 히스토리 & 인증 | ✅ 완료 |
| 7 | QA & 배포 | 🚧 진행 중 |

---

## Plan 1 — 지표 실측화 (2026-09-16 ~ 09-18, 완료)

계획서: `docs/superpowers/plans/2026-09-16-metrics-measurement.md`
설계 문서: `docs/superpowers/specs/2026-09-16-supervision-metrics-upgrade-design.md`

### 배경

"유료 LLM 비용 절감"으로 시작했으나 **그 전제가 사실이 아니었다.**
Gemini 에는 텍스트 프롬프트만 가고 영상은 서버 내부 MediaPipe 가 처리한다.
콘솔 확인 결과 3개월간 청구 내역이 없었다(체감 비용은 별개 서비스의 것).

대신 진짜 문제가 드러났다 — **LLM 에 넘기던 7개 지표 중 5개가 가짜였다.**
`head_movement` 는 `1.7` 하드코딩, 나머지 4개는 프롬프트 기본값이
모든 사용자에게 동일하게 들어갔다.

### 완료 항목

- [x] 지표 8개 실측화 (`pose_world_landmarks` 3D 활용, X-팩터 신규 추가)
- [x] 촬영 각도별 게이팅 — 각도상 불가한 지표는 `measurable: false`
- [x] 물리적 범위 검사 — 불가능한 값은 "측정 실패"로 차단
- [x] `pose_estimator.py` 439줄을 `swing/` 패키지 6모듈로 분할
- [x] supervision 어노테이터로 오버레이 교체 (한글 라벨은 Pillow)
- [x] 규칙 엔진 신설 — LLM 없이 진단·점수·드릴 완결
- [x] LLM 을 문장 윤문 역할로 축소, 악의적 응답 방어
- [x] 프론트엔드 지표 3개 → 8개, "측정 불가"/"측정 실패" 구분
- [x] MediaPipe world landmark 축 방향 실측 검증 (설계 §6 최상위 리스크 해소)
- [x] 실제 영상 11개로 검증 — 정상 8/11
- [x] 문서 갱신

테스트 118개 통과. 분석 소요 9.5초(목표 10초 이내 충족).

### 남은 과제

- [ ] `detect_swing_window` 정확도 — 실패 3/11 의 원인
- [ ] `head_movement` 의 어깨폭 40cm 가정 재검토
- [ ] Plan 2 — 기기 간 흐름(모바일 촬영 → PC 상세 분석). 선행 조건은
      `POST /upload` 의 `user_id` 귀속 버그 수정

---

## 영상 재생·궤적 (2026-09-19)

분석 결과를 "읽는" 것에서 "보는" 것으로 옮기는 작업. 지표 숫자만으로는
자기 스윙의 무엇이 문제인지 알기 어렵다는 피드백에서 출발했다.

### 완료 항목

- [x] 슬로모션 재생 (1 / 0.75 / 0.5 / 0.25 / 0.1배속)
- [x] 7단계 카드 클릭 → 해당 영상 지점으로 이동
- [x] 카드별 재생 버튼 → 앞뒤 단계까지를 반복 재생
- [x] 구간 길이에 맞춰 배속 자동 선택 (`speedForSpan`, 목표 재생시간 2.0초)
- [x] 손 궤적 오버레이 — 양 손목 중점, 탑 기준으로 백스윙/다운스윙 색 분리
- [x] 궤적 on/off 토글
- [x] 재생 구간을 어드레스 직전~피니시 직후로 크롭
      (실측: 11.0초 영상 → 2.3초. 걸어오는 장면·공 줍는 장면 제외)
- [x] "전체 영상 보기" 버튼 — 크롭을 끄고 원본 전체 재생

### 하지 않기로 한 것

- **공 궤적(탄도·방향)** — 30fps 에서는 불가능. 임팩트 후 공은 프레임당
  1.8m 를 이동해 1~3프레임 만에 사라진다. 실제 영상의 임팩트 직후를 차분해
  재보니 "공 크기 물체" 후보가 프레임당 28~1026개로, 배경 흔들림과
  구분되지 않았다. 240fps 슬로모션 촬영으로 바꾸면 재검토 가능.
- **클럽헤드 추적** — MediaPipe 는 사람 관절만 준다. Hough 변환으로 샤프트를
  찾아보았으나 ROI 산정 방식을 두 번 바꿔도 **임팩트 프레임에서 후보 0개**였고,
  검출된 구간도 끝점이 제각각이라 어느 선이 클럽인지 고를 수 없었다.
  배경 모서리를 클럽헤드로 그리는 것은 이 프로젝트가 없애려던 종류의 거짓말이라
  손 궤적만 그린다.

테스트 138개 통과.
