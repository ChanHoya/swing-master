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
- [x] 6프레임 스킵 (기존 3프레임 → 2배 추가 단축)
- [x] 640p 리사이즈 전처리 (MediaPipe 추론 속도 4배 향상)
- [x] 최대 150프레임 처리 후 조기 종료
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
- [ ] 분석 소요 시간 측정 → 10초 이하 확인
- [ ] 에러 핸들링 & 사용자 에러 메시지 정비
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
