# 06. 데이터 스키마 (Data Schema)

## 1. Pose JSON — 포즈 추정 원시 데이터

MediaPipe BlazePose 33 keypoints 출력 형식.

```typescript
interface Keypoint {
  x: number;          // 정규화 좌표 [0.0, 1.0] (화면 너비 기준)
  y: number;          // 정규화 좌표 [0.0, 1.0] (화면 높이 기준)
  z: number;          // 깊이 (중심 힙 기준 상대값)
  visibility: number; // 가시성 신뢰도 [0.0, 1.0]
}

interface PoseFrame {
  frame_index: number;   // 원본 영상 프레임 번호
  timestamp_ms: number;  // 영상 내 타임스탬프 (milliseconds)
  phase: SwingPhase;     // 스윙 페이즈
  keypoints: {
    // MediaPipe 33 keypoints 인덱스 기준
    nose: Keypoint;                    // 0
    left_eye_inner: Keypoint;          // 1
    left_eye: Keypoint;                // 2
    left_eye_outer: Keypoint;          // 3
    right_eye_inner: Keypoint;         // 4
    right_eye: Keypoint;               // 5
    right_eye_outer: Keypoint;         // 6
    left_ear: Keypoint;                // 7
    right_ear: Keypoint;               // 8
    mouth_left: Keypoint;              // 9
    mouth_right: Keypoint;             // 10
    left_shoulder: Keypoint;           // 11
    right_shoulder: Keypoint;          // 12
    left_elbow: Keypoint;              // 13
    right_elbow: Keypoint;             // 14
    left_wrist: Keypoint;              // 15
    right_wrist: Keypoint;             // 16
    left_pinky: Keypoint;              // 17
    right_pinky: Keypoint;             // 18
    left_index: Keypoint;              // 19
    right_index: Keypoint;             // 20
    left_thumb: Keypoint;              // 21
    right_thumb: Keypoint;             // 22
    left_hip: Keypoint;                // 23
    right_hip: Keypoint;               // 24
    left_knee: Keypoint;               // 25
    right_knee: Keypoint;              // 26
    left_ankle: Keypoint;              // 27
    right_ankle: Keypoint;             // 28
    left_heel: Keypoint;               // 29
    right_heel: Keypoint;              // 30
    left_foot_index: Keypoint;         // 31
    right_foot_index: Keypoint;        // 32
  };
}

type SwingPhase = "address" | "backswing_top" | "impact" | "follow_through";
```

---

## 2. SwingMetrics — 7가지 분석 지표

```typescript
interface SwingMetrics {
  spine_angle: {
    value: number;        // 측정값 (degrees)
    score: number;        // 0~100 점수
    reference_min: 30;
    reference_max: 45;
  };
  hip_rotation: {
    value: number;        // 백스윙 탑에서의 힙 회전각 (degrees)
    score: number;
    reference_min: 45;
    reference_max: null;
  };
  shoulder_rotation: {
    value: number;        // 백스윙 탑에서의 어깨 회전각 (degrees)
    score: number;
    reference_min: 90;
    reference_max: null;
  };
  knee_flex: {
    value: number;        // 어드레스 시 무릎 굴곡각 (degrees)
    score: number;
    reference_min: 20;
    reference_max: 30;
  };
  head_movement: {
    value: number;        // 어드레스~임팩트 머리 이동거리 (cm)
    score: number;
    reference_min: null;
    reference_max: 5;
  };
  weight_transfer: {
    value: number;        // 임팩트 시 왼발 체중 비율 (%)
    score: number;
    reference_min: 60;
    reference_max: null;
  };
  tempo_ratio: {
    value: number;        // 백스윙시간 / 다운스윙시간
    score: number;
    reference_min: 2.5;
    reference_max: 3.5;
  };
}
```

---

## 3. AnalysisResult — 전체 분석 결과

```typescript
interface AnalysisResult {
  // 메타데이터
  analysis_id: string;        // UUID
  upload_id: string;          // 원본 영상 참조
  user_id: string | null;     // 비로그인 시 null
  created_at: string;         // ISO 8601

  // 상태
  status: "queued" | "processing" | "done" | "failed";
  error_message?: string;

  // 영상 정보
  video: {
    duration_ms: number;
    fps: number;
    width: number;
    height: number;
    storage_url: string;       // R2 URL
  };

  // 포즈 데이터
  pose_frames: PoseFrame[];    // 핵심 프레임 4개
  overlay_images: {
    [phase in SwingPhase]?: string;  // 오버레이 이미지 URL per phase
  };

  // 분석 지표
  metrics: SwingMetrics;
  overall_score: number;       // 0~100
  grade: "A" | "B" | "C" | "D";

  // LLM 생성 피드백
  feedback: {
    top_issues: Array<{
      metric: string;
      severity: "high" | "medium" | "low";
      feedback: string;
    }>;
    drills: Array<{
      issue_metric: string;
      drill_name: string;
      steps: string[];
      repetitions: string;
      tip: string;
    }>;
    encouragement: string;
  };

  // 처리 시간 추적
  processing_time_ms: {
    pose_estimation: number;
    metric_calculation: number;
    llm_generation: number;
    total: number;
  };
}
```

---

## 4. DB 테이블 스키마 (PostgreSQL)

```sql
-- 사용자
CREATE TABLE users (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email       VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- 업로드된 영상
CREATE TABLE uploads (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID REFERENCES users(id) ON DELETE SET NULL,
    storage_url TEXT NOT NULL,
    file_size   BIGINT,
    duration_ms INT,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- 분석 결과
CREATE TABLE analyses (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    upload_id     UUID REFERENCES uploads(id) ON DELETE CASCADE,
    user_id       UUID REFERENCES users(id) ON DELETE SET NULL,
    status        VARCHAR(20) DEFAULT 'queued',
    overall_score SMALLINT,
    grade         CHAR(1),
    metrics       JSONB,
    feedback      JSONB,
    pose_frames   JSONB,
    overlay_urls  JSONB,
    error_message TEXT,
    created_at    TIMESTAMPTZ DEFAULT NOW(),
    completed_at  TIMESTAMPTZ
);

CREATE INDEX idx_analyses_user_id ON analyses(user_id);
CREATE INDEX idx_analyses_status ON analyses(status);
```
