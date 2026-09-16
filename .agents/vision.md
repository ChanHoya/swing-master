# Vision Sub-Agent

## 역할
포즈 추정 & 영상 처리 파이프라인 구현 전담

## 담당 영역

| 영역 | 세부 내용 |
|------|-----------|
| 프레임 추출 | OpenCV로 영상에서 핵심 프레임 추출 |
| 포즈 추정 | MediaPipe BlazePose 33 keypoints 추출 |
| 스윙 분석 | 7가지 지표 계산 알고리즘 구현 |
| 이미지 생성 | keypoint 오버레이 이미지 생성 & R2 업로드 |
| 품질 검사 | 영상 밝기/블러 사전 검사 |

## 파일 구조 (예정)

```
backend/
└── vision/
    ├── __init__.py
    ├── video_processor.py      ← 프레임 추출, 품질 검사
    ├── pose_estimator.py       ← MediaPipe 포즈 추정
    ├── swing_analyzer.py       ← 7가지 지표 계산
    ├── overlay_renderer.py     ← 오버레이 이미지 생성
    └── phase_detector.py       ← 스윙 페이즈 자동 감지
```

## 핵심 알고리즘

### 스윙 페이즈 감지
```
어드레스    : 클럽헤드 정지 상태 + 어드레스 자세 감지
백스윙 탑   : 오른손 최고점 도달 프레임
임팩트      : 양손 최저점 + 클럽 수직 프레임
팔로우스루  : 임팩트 후 0.3초 누적 회전 최대 프레임
```

### 지표 계산 공식

| 지표 | 계산 방법 |
|------|-----------|
| `spine_angle` | 어깨 중점 → 힙 중점 벡터와 수직선 사이 각도 |
| `hip_rotation` | 어드레스 힙 라인 → 백스윙 탑 힙 라인 회전각 |
| `shoulder_rotation` | 어드레스 어깨 라인 → 백스윙 탑 어깨 라인 회전각 |
| `knee_flex` | 대퇴부~종아리 벡터 사이 각도 (180° - 굴곡각) |
| `head_movement` | 어드레스~임팩트 nose keypoint 픽셀 이동 → cm 변환 |
| `weight_transfer` | 임팩트 시 left_ankle x좌표 무게 비율 추정 |
| `tempo_ratio` | 어드레스→탑 프레임 수 / 탑→임팩트 프레임 수 |

## 성능 목표

| 작업 | 목표 처리 시간 |
|------|----------------|
| 품질 검사 | < 1초 |
| 프레임 추출 (4개) | < 3초 |
| 포즈 추정 (4 프레임) | < 5초 |
| 지표 계산 | < 1초 |
| 오버레이 생성 + 업로드 | < 5초 |
| **Vision 합계** | **< 15초** |

## 의존성

```toml
mediapipe = "0.10.*"
opencv-python-headless = "4.*"
numpy = "1.26.*"
pillow = "10.*"
boto3 = "1.34.*"   # R2 업로드
```

## 참고 문서
- `docs/06_data_schema.md` — PoseFrame, SwingMetrics 타입 정의
- `docs/07_risks.md` — R01, R02, R05 리스크 대응
