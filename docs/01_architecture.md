# 01. 시스템 아키텍처 (Architecture)

## 전체 구조

```
                        ┌─────────────────────────────┐
                        │         사용자 브라우저        │
                        │  (Next.js Frontend / Vercel) │
                        └────────────┬────────────────┘
                                     │ HTTPS
                        ┌────────────▼────────────────┐
                        │      API Gateway (FastAPI)   │
                        │      Railway / Fly.io        │
                        └──┬──────────────────────┬───┘
                    Pose   │                      │  LLM
                  Estimate │                      │  Prompt
                  ┌────────▼──────┐     ┌─────────▼────────┐
                  │  Vision API   │     │   OpenAI GPT-4o  │
                  │ (MediaPipe /  │     │   (Feedback &    │
                  │  AWS Rekognition)   │    Drills 생성)   │
                  └───────────────┘     └──────────────────┘
                        │
              ┌─────────▼──────────┐
              │   Object Storage   │
              │  (S3 / Cloudflare  │
              │      R2)           │
              └────────────────────┘
```

---

## 데이터 흐름

### 1. 영상 업로드 & 분석 요청

```
Client                   API Server              Vision Module
  │                          │                        │
  │──── POST /upload ────────►│                        │
  │     (multipart video)    │                        │
  │                          │──── extract_frames() ──►│
  │                          │                        │──── MediaPipe Pose
  │                          │◄─── pose_keypoints[] ──│     추정 (33 keypoints)
  │                          │                        │
  │                          │──── analyze_swing() ──►│
  │                          │◄─── swing_metrics{} ───│
```

### 2. LLM 피드백 생성

```
API Server               OpenAI GPT-4o
  │                           │
  │──── /v1/chat/completions ─►│
  │    (swing_metrics + template)
  │◄─── feedback_text + drills │
  │                           │
```

### 3. 결과 반환

```
API Server              Client
  │                       │
  │──── JSON response ───►│
  │  {                    │
  │    pose_image_url,    │──── 피드백 화면 렌더링
  │    metrics,           │
  │    feedback,          │
  │    drills[]           │
  │  }                    │
```

---

## 핵심 컴포넌트

| 컴포넌트 | 역할 | 기술 |
|----------|------|------|
| Frontend | 영상 업로드 UI, 결과 시각화 | Next.js 14, TypeScript |
| API Server | 요청 라우팅, 오케스트레이션 | FastAPI (Python 3.11) |
| Vision Module | 포즈 추정, 스윙 지표 계산 | MediaPipe / OpenCV |
| LLM Module | 피드백 & 드릴 텍스트 생성 | OpenAI GPT-4o |
| Storage | 영상 & 결과 이미지 보관 | AWS S3 or Cloudflare R2 |
| DB | 사용자, 분석 결과 저장 | PostgreSQL (Supabase) |

---

## 배포 환경

| 서비스 | 플랫폼 | 비고 |
|--------|--------|------|
| Frontend | Vercel | 자동 CI/CD |
| Backend API | Railway | Docker 컨테이너 |
| DB | Supabase | Managed PostgreSQL |
| Storage | Cloudflare R2 | S3 호환, 저렴한 egress |

---

## 분석 파이프라인 구조 (2026-09-18 개정)

`pose_estimator.py`(439줄, 책임 8개)를 책임 단위로 쪼갰다.
기존 파일은 `process_pose_estimation` 만 재export 하는 8줄 호환 래퍼로 남는다.

```
backend/app/services/
├── swing/
│   ├── types.py     MetricValue · PoseSequence · PHASE_KEYS
│   ├── phases.py    스윙 구간 탐지 + 7단계 분할
│   ├── pose.py      MediaPipe 3D/2D 랜드마크 추출 (supervision 경유 픽셀 변환)
│   ├── metrics.py   지표 8개 계산 — numpy 외 의존성 없는 순수 함수
│   ├── overlay.py   supervision 어노테이터로 스켈레톤 렌더
│   └── pipeline.py  오케스트레이션 (다운로드 · DB · R2 · asyncio)
└── feedback/
    ├── rules.py     지표 → 진단 · 점수 · 등급
    ├── drills.py    지표별 교정 드릴
    └── llm.py       Gemini 윤문. 실패 시 rules 결과를 그대로 반환
```

### 데이터 흐름

```
영상 → detect_swing_window → extract_sequence → detect_phases
     → compute_metrics(camera_angle) → metrics_to_json
     → evaluate(규칙 엔진) → polish(LLM 윤문, 선택적)
     → render_overlay ×7 → R2 업로드 → DB 저장
```

실측 소요 9.5초 (1080×1080, 30fps, 8.7초 영상).

### 규칙 엔진과 LLM의 관계

| | 이전 | 현재 |
|---|---|---|
| 진단 · 점수 · 드릴 결정 | LLM | **규칙 엔진** |
| LLM 역할 | 전부 | **한국어 문장 다듬기만** |
| LLM 실패 시 | 빈 껍데기 + "혼잡합니다" | **규칙 결과가 그대로 나감** |

`polish()` 는 LLM 응답을 신뢰하지 않는다. 점수 · 등급 · 이슈 개수 · 드릴 구성은
절대 덮어쓰지 못하며, 응답이 어떤 모양이든 예외를 던지지 않고 입력을 그대로 돌려준다.

### 포즈 추정 위치

**서버 사이드로 확정.** supervision 이 파이썬 서버 라이브러리라 브라우저에서
돌릴 수 없다. 개인 용도이므로 영상 서버 전송을 감수한다.
