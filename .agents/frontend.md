# Frontend Sub-Agent

## 역할
Next.js 14 기반 UI/UX 구현 및 사용자 인터랙션 전담

## 담당 영역

| 영역 | 세부 내용 |
|------|-----------|
| 페이지 | 영상 업로드, 분석 결과, 히스토리, 로그인/회원가입 |
| 컴포넌트 | 드래그앤드롭 업로더, 레이더 차트, 피드백 카드, 드릴 리스트 |
| 상태 관리 | React Query (서버 상태), Zustand (클라이언트 상태) |
| 애니메이션 | Framer Motion (분석 중 로딩, 점수 카운트업) |
| 스타일링 | Tailwind CSS + shadcn/ui |

## 파일 구조 (예정)

```
frontend/
├── app/
│   ├── page.tsx              ← 업로드 홈
│   ├── result/[id]/page.tsx  ← 분석 결과
│   ├── history/page.tsx      ← 이력 조회
│   └── auth/page.tsx         ← 로그인/가입
├── components/
│   ├── upload/
│   │   ├── DropZone.tsx
│   │   └── ProgressBar.tsx
│   ├── result/
│   │   ├── ScoreRadar.tsx
│   │   ├── FeedbackCard.tsx
│   │   └── DrillList.tsx
│   └── ui/                   ← shadcn 컴포넌트
├── lib/
│   ├── api.ts                ← API 클라이언트
│   └── types.ts              ← 공유 타입
└── hooks/
    ├── useUpload.ts
    └── useAnalysis.ts
```

## 주요 API 연동

| Hook | 엔드포인트 | 용도 |
|------|-----------|------|
| `useUpload` | `POST /upload` | 영상 업로드 |
| `useAnalysisStatus` | `GET /analysis/:id/status` | 폴링 |
| `useAnalysisResult` | `GET /analysis/:id/result` | 결과 조회 |
| `useHistory` | `GET /history` | 이력 조회 |

## 핵심 UX 원칙

1. **업로드 → 결과까지 3클릭 이내**
2. 분석 진행 중 스켈레톤 + 진행 단계 텍스트 표시
3. 모바일 우선 (375px 기준), 터치 최적화
4. 에러 상태 명확한 안내 + 재시도 버튼

## 참고 문서
- `docs/03_features_mvp.md` — 기능 명세
- `docs/06_data_schema.md` — API 응답 타입
- `docs/05_prompts.md` — 에러 메시지 템플릿
