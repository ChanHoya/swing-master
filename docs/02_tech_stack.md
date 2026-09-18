# 02. 기술 스택 (Tech Stack)

## 확정 스택 & 버전

### Frontend

| 기술 | 버전 | 선정 근거 |
|------|------|-----------|
| Next.js | 14.x (App Router) | SSR + 파일 기반 라우팅, Vercel 최적화 |
| TypeScript | 5.x | 타입 안전성, IDE 자동완성 |
| Tailwind CSS | 3.x | 빠른 스타일링, 디자인 일관성 |
| React Query | 5.x (TanStack) | 서버 상태 관리, 폴링 |
| Framer Motion | 11.x | 분석 진행 애니메이션 |
| shadcn/ui | latest | 접근성 갖춘 UI 컴포넌트 |

### Backend

| 기술 | 버전 | 선정 근거 |
|------|------|-----------|
| Python | 3.11 | MediaPipe 호환성, 생태계 |
| FastAPI | 0.111.x | 비동기 지원, 자동 OpenAPI 문서 |
| MediaPipe | 0.10.x | 구글 지원, 빠른 포즈 추정 |
| OpenCV | 4.x | 영상 프레임 추출 |
| Pydantic | 2.x | 데이터 검증, 스키마 자동 생성 |
| SQLAlchemy | 2.x | Async ORM |
| Alembic | 1.x | DB 마이그레이션 |

### AI / ML

| 기술 | 버전/모델 | 선정 근거 |
|------|-----------|-----------|
| 규칙 엔진 | `feedback/rules.py` | 진단·점수·드릴을 확정한다. LLM 없이 완결되므로 API 장애에 영향받지 않는다 |
| Gemini API | gemini-2.5-flash (fallback 3종) | 규칙 엔진 결과의 **문장만** 다듬는다. 실패하면 규칙 결과가 그대로 나간다 |
| MediaPipe Pose | BlazePose lite | 33 keypoints + `pose_world_landmarks`(미터 단위 3D). 회전 지표는 이 3D 없이 계산 불가 |
| supervision | 0.30.3 (MIT) | 키포인트 표준화와 스켈레톤 오버레이. 뼈대 정의를 데이터로 분리 |

### 인프라

| 기술 | 플랫폼 | 선정 근거 |
|------|--------|-----------|
| Frontend 배포 | Vercel | Next.js 네이티브 지원, 무료 티어 |
| Backend 배포 | Railway | Docker 지원, 간단한 설정 |
| 데이터베이스 | Supabase (PostgreSQL 15) | 관리형, 무료 500MB |
| 파일 스토리지 | Cloudflare R2 | S3 호환, 무료 10GB/월 |

---

## 버전 고정 정책

- **`requirements.txt`** / **`package.json`** 에 패치 버전까지 고정 (`==` / 정확한 semver)
- 의존성 업데이트는 주간 PR로만 반영 (Renovate Bot)
- Python 환경: `pyproject.toml` + `poetry.lock`

---

## 선택하지 않은 스택 & 이유

| 대안 | 제외 이유 |
|------|-----------|
| YOLO-Pose | **3D를 주지 않는다.** COCO 17점을 이미지 평면 2D로만 회귀하므로 어깨·힙 회전을 계산할 수 없다. 사람 탐지·ROI 크롭 용도로는 유효하나 torch(macOS arm64 휠 121MB)를 끌어와 Railway 배포를 압박한다 |
| LangChain | MVP 규모에서 over-engineering |
| AWS Lambda | Cold start 지연 → 분석 UX 저하 |
| Firebase | Supabase 대비 쿼리 유연성 부족 |
