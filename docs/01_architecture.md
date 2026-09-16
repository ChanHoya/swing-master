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
