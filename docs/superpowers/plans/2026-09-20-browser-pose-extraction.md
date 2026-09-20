# 브라우저 포즈 추출 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 포즈 추출을 서버(Render 0.1 CPU, 94~296초)에서 폰으로 옮겨 분석을 수 초대로 줄인다.

**Architecture:** 폰이 MediaPipe 로 좌표를 뽑아 서버에 보내고, 서버는 그 좌표로 지표·규칙만 계산한다. `metrics.py`·`phases.detect_phases`·`tracks.py`·`feedback/*` 는 numpy 순수 함수라 한 줄도 바뀌지 않는다. 영상은 분석 경로에서 빠지고 재생용으로만 백그라운드 업로드된다.

**Tech Stack:** `@mediapipe/tasks-vision` 1.0.1 (브라우저) / FastAPI 0.136 / Next.js 16 / Neon Postgres / Cloudflare R2

**Spec:** `docs/superpowers/specs/2026-09-20-browser-pose-extraction-design.md`

## Global Constraints

- **TypeScript strict 모드. `any` 금지** — `unknown` + 타입 가드를 쓴다.
- **모든 사용자 노출 텍스트는 한국어.**
- **백엔드 도구는 `backend/.venv/bin/<도구>` 를 직접 호출한다.**
- **프론트 패키지 매니저는 npm.** 타입 검증은 `npx tsc --noEmit`.
- **`pytest` 출력을 `tail`/`head`/`grep` 으로 파이프하지 않는다.** 종료 코드가 가려진다. 줄여야 하면:
  `\.venv/bin/pytest tests/ -q > /tmp/pt.txt 2>&1; EXIT=$?; tail -5 /tmp/pt.txt; echo "EXIT=$EXIT"`
- **커밋 메시지 끝에** `Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>` 를 붙인다.
- **측정하지 못한 값에 가짜 기본값을 채우지 않는다.** 프레임 유실도 숨기지 말고 센다.
- **지표 알고리즘을 바꾸지 않는다.** 좌표의 출처만 바뀐다. `metrics.py`·`phases.py`·`tracks.py`·`feedback/*` 수정은 이 계획의 범위 밖이다.
- **서버 파이프라인 삭제는 마지막 태스크다.** Task 1·2 를 통과하기 전에 지우지 않는다.

**현재 기준값 (Task 2·9 판정에 쓴다)**
- 백엔드 테스트 201개 통과
- Docker 이미지 1.58GB, 512MB 컨테이너에서 최대 메모리 355MB
- Render 분석 94~296초

---

## Task 1: 스파이크 — 폰에서 MediaPipe 속도 측정 (게이트)

이 태스크만 산출물이 코드가 아니라 **숫자**다. 여기서 막히면 설계 전체가
성립하지 않으므로 **뒤로 넘어가지 말고 사용자에게 보고**한다.

**Files:**
- Create: `frontend/src/app/spike/page.tsx` (일회용, Task 9 에서 삭제)
- Create: `frontend/public/pose_landmarker_lite.task` (서버에서 복사)

**Interfaces:**
- Consumes: 없음
- Produces: 측정 수치. 뒤 태스크는 판정(가능/불가)에만 의존한다.

- [ ] **Step 1: 패키지와 모델을 준비한다**

```bash
cd frontend && npm install @mediapipe/tasks-vision@1.0.1
cp ../backend/app/services/pose_landmarker_lite.task public/
cp node_modules/@mediapipe/tasks-vision/wasm/* public/mp-wasm/ 2>/dev/null \
  || (mkdir -p public/mp-wasm && cp node_modules/@mediapipe/tasks-vision/wasm/* public/mp-wasm/)
```

모델을 구글 CDN 이 아니라 우리 것으로 쓰는 이유는, 서버가 쓰던 것과 **같은
모델**이어야 Task 2 의 대조가 의미를 갖기 때문이다.

- [ ] **Step 2: 측정 페이지를 만든다**

`frontend/src/app/spike/page.tsx`:

```tsx
"use client";

import { useState } from "react";
import { FilesetResolver, PoseLandmarker } from "@mediapipe/tasks-vision";

// 일회용 측정 페이지. 설계의 유일한 미검증 전제인 "폰에서 MediaPipe 가
// 쓸 만한 속도로 도는가" 를 재기 위한 것이다. Task 9 에서 삭제한다.
export default function SpikePage() {
  const [log, setLog] = useState<string[]>([]);
  const say = (s: string) => setLog((prev) => [...prev, s]);

  const run = async (file: File) => {
    setLog([]);
    const t0 = performance.now();
    const fileset = await FilesetResolver.forVisionTasks("/mp-wasm");
    const landmarker = await PoseLandmarker.createFromOptions(fileset, {
      baseOptions: { modelAssetPath: "/pose_landmarker_lite.task", delegate: "GPU" },
      runningMode: "VIDEO",
      numPoses: 1,
    });
    say(`모델 로딩 ${((performance.now() - t0) / 1000).toFixed(1)}초`);

    const video = document.createElement("video");
    video.src = URL.createObjectURL(file);
    video.muted = true;
    video.playsInline = true;
    await new Promise<void>((r) => { video.onloadedmetadata = () => r(); });
    say(`영상 ${video.videoWidth}x${video.videoHeight}, ${video.duration.toFixed(1)}초`);

    const t1 = performance.now();
    let frames = 0;
    let withPose = 0;
    await video.play();
    await new Promise<void>((resolve) => {
      const tick = () => {
        if (video.ended) { resolve(); return; }
        const res = landmarker.detectForVideo(video, performance.now());
        frames += 1;
        if (res.worldLandmarks.length > 0) withPose += 1;
        video.requestVideoFrameCallback(tick);
      };
      video.requestVideoFrameCallback(tick);
    });
    const secs = (performance.now() - t1) / 1000;
    say(`추출 ${secs.toFixed(1)}초 | 프레임 ${frames}개 | 포즈 인식 ${withPose}개`);
    say(`프레임당 ${((secs * 1000) / Math.max(frames, 1)).toFixed(0)}ms`);
    say(secs <= 10 ? "판정: 통과 (10초 이내)" : "판정: 불가 (10초 초과)");
  };

  return (
    <div style={{ padding: 24 }}>
      <h1 style={{ fontSize: 18, fontWeight: 700, marginBottom: 12 }}>
        포즈 추출 속도 측정
      </h1>
      <input
        type="file"
        accept="video/*"
        onChange={(e) => { const f = e.target.files?.[0]; if (f) void run(f); }}
      />
      <pre style={{ marginTop: 16, fontSize: 13, lineHeight: 1.7 }}>
        {log.join("\n")}
      </pre>
    </div>
  );
}
```

- [ ] **Step 3: 타입 검사와 빌드를 통과시킨다**

```bash
cd frontend && npx tsc --noEmit && npm run build 2>&1 | tail -5
```

- [ ] **Step 4: 배포하고 실제 폰에서 잰다**

```bash
git add frontend && git commit -m "$(cat <<'EOF'
chore(spike): measure MediaPipe extraction speed in the browser

설계의 유일한 미검증 전제를 재기 위한 일회용 페이지다.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
EOF
)" && git push origin main
```

폰에서 `https://hoya-swing-master.vercel.app/spike` 를 열고 8초 안팎의 스윙
영상을 고른다. **GPU 델리게이트가 실패하면 `delegate: "CPU"` 로 바꿔 다시
잰다** — iOS Safari 에서 GPU 경로가 막힐 수 있다.

- [ ] **Step 5: 판정한다**

| 결과 | 판정 |
|---|---|
| 추출 10초 이내, 포즈 인식 프레임이 전체의 80% 이상 | **통과.** Task 2 로 |
| 추출 10~20초 | **보고 후 결정.** 그래도 서버 94~296초보다는 빠르다 |
| 추출 20초 초과, 또는 모델 로딩 실패 | **불가.** 여기서 멈추고 사용자에게 보고 |

숫자를 사용자에게 그대로 보고한다. 추정치를 쓰지 않는다.

---

## Task 2: 대조 — 서버와 브라우저의 지표가 같은가 (게이트)

브라우저 MediaPipe(WASM 1.0.1)와 서버 MediaPipe(네이티브 0.10.33)는 같은
모델이라도 좌표가 완전히 같지는 않다. 점수가 달라지면 과거 28건과 비교가
깨진다. **차이를 먼저 재고 보고한 뒤** 넘어간다.

**Files:**
- Modify: `frontend/src/app/spike/page.tsx` (좌표를 JSON 으로 내려받는 버튼 추가)
- Create: `backend/scripts/compare_landmarks.py` (일회용 대조 스크립트)

**Interfaces:**
- Consumes: Task 1 의 판정이 "불가" 가 아닐 것
- Produces: 지표 8개의 서버/브라우저 차이. Task 3 은 이 결과에만 의존한다.

- [ ] **Step 1: 스파이크 페이지에 좌표 내보내기를 더한다**

`run()` 안에서 프레임마다 좌표를 모으고, 끝나면 파일로 내려받는다.
`tick()` 의 `landmarker.detectForVideo(...)` 결과를 이렇게 쌓는다.

```tsx
    const collected: Array<{
      t: number;
      world: number[][];
      xy: number[][];
      vis: number[];
    }> = [];
```

`tick()` 안, `frames += 1;` 바로 뒤에 넣는다.

```tsx
        if (res.worldLandmarks.length > 0) {
          collected.push({
            t: video.currentTime,
            world: res.worldLandmarks[0].map((l) => [l.x, l.y, l.z]),
            xy: res.landmarks[0].map((l) => [l.x, l.y]),
            vis: res.landmarks[0].map((l) => l.visibility ?? 0),
          });
        }
```

측정이 끝난 뒤(`say(판정...)` 다음) 내려받기를 붙인다.

```tsx
    const payload = {
      fps: 30,
      resolution: [video.videoWidth, video.videoHeight],
      frames: collected,
    };
    const url = URL.createObjectURL(
      new Blob([JSON.stringify(payload)], { type: "application/json" }),
    );
    const a = document.createElement("a");
    a.href = url;
    a.download = "landmarks.json";
    a.click();
    URL.revokeObjectURL(url);
```

- [ ] **Step 2: 대조 스크립트를 만든다**

`backend/scripts/compare_landmarks.py`:

```python
"""브라우저가 뽑은 좌표와 서버가 뽑은 좌표의 지표를 대조한다.

브라우저 MediaPipe(WASM)와 서버 MediaPipe(네이티브)는 같은 모델이라도
좌표가 완전히 같지 않다. 지표가 얼마나 달라지는지 먼저 재기 위한
일회용 스크립트다.

사용법:
    cd backend && .venv/bin/python scripts/compare_landmarks.py <영상> <landmarks.json>
"""
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.swing.metrics import compute_metrics, metrics_to_json  # noqa: E402
from app.services.swing.phases import detect_phases, detect_swing_window  # noqa: E402
from app.services.swing.pose import extract_sequence  # noqa: E402
from app.services.swing.types import PoseSequence  # noqa: E402


def sequence_from_json(path: str) -> PoseSequence:
    data = json.load(open(path))
    frames = data["frames"]
    w, h = data["resolution"]
    fps = float(data["fps"])
    return PoseSequence(
        world=np.array([f["world"] for f in frames], dtype=np.float32),
        xy_px=np.array([f["xy"] for f in frames], dtype=np.float32) * [w, h],
        visibility=np.array([f["vis"] for f in frames], dtype=np.float32),
        frame_indices=np.array([round(f["t"] * fps) for f in frames], dtype=np.int32),
        fps=fps,
        resolution_wh=(int(w), int(h)),
    )


def main(video: str, landmarks: str) -> int:
    angle = "down_the_line"

    start, end, _ = detect_swing_window(video)
    server_seq = extract_sequence(video, start, end)
    server = metrics_to_json(
        compute_metrics(server_seq, detect_phases(server_seq), angle)
    )

    browser_seq = sequence_from_json(landmarks)
    browser = metrics_to_json(
        compute_metrics(browser_seq, detect_phases(browser_seq), angle)
    )

    print(f"프레임  서버 {len(server_seq)}개  브라우저 {len(browser_seq)}개")
    print(f"{'지표':18s} {'서버':>10s} {'브라우저':>10s} {'차이':>10s}")
    for key in server:
        s = server[key]["value"]
        b = browser.get(key, {}).get("value")
        if s is None or b is None:
            print(f"{key:18s} {str(s):>10s} {str(b):>10s} {'—':>10s}")
            continue
        diff = b - s
        pct = abs(diff) / abs(s) * 100 if s else 0.0
        print(f"{key:18s} {s:10.2f} {b:10.2f} {diff:+9.2f} ({pct:.0f}%)")
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(__doc__)
        raise SystemExit(2)
    raise SystemExit(main(sys.argv[1], sys.argv[2]))
```

- [ ] **Step 3: 같은 영상으로 양쪽을 돌린다**

폰(또는 PC 브라우저)에서 `/spike` 로 영상 하나를 처리해 `landmarks.json` 을
받고, 같은 영상 파일을 로컬에 두고 실행한다.

```bash
cd backend && .venv/bin/python scripts/compare_landmarks.py <영상경로> <landmarks.json>
```

- [ ] **Step 4: 판정한다**

| 결과 | 판정 |
|---|---|
| 측정된 지표가 모두 **10% 이내** 차이 | **통과.** Task 3 으로 |
| 10~25% 차이 | **보고 후 결정.** 과거 기록과 비교가 흔들린다 |
| 25% 초과, 또는 서버는 측정됐는데 브라우저는 실패 | **재검토.** 설계를 다시 본다 |

차이가 큰 지표가 있으면 **어느 것이 얼마나 다른지 그대로 보고**한다. 평균만
말하지 않는다 — 회전 지표 하나가 30% 틀리면 등급이 바뀐다.

- [ ] **Step 5: 커밋**

```bash
cd /Users/chanhojung/swing-master
git add frontend/src/app/spike backend/scripts/compare_landmarks.py
git commit -m "$(cat <<'EOF'
chore(spike): compare browser and server landmark metrics

브라우저 MediaPipe(WASM)와 서버 MediaPipe(네이티브)의 지표 차이를
재기 위한 일회용 스크립트다. 점수가 달라지면 과거 기록과 비교가
깨지므로 전환 전에 확인한다.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 3: 백엔드 어댑터와 새 엔드포인트

**Files:**
- Create: `backend/app/api/endpoints/analysis_from_pose.py`
- Create: `backend/tests/test_pose_payload.py`
- Modify: `backend/app/api/router.py`
- Modify: `backend/app/services/feedback/llm.py` (타임아웃 20초 → 8초)

**Interfaces:**
- Consumes: Task 2 의 판정이 "재검토" 가 아닐 것
- Produces:
  - `sequence_from_payload(payload: PosePayload) -> PoseSequence`
  - `POST /analysis` — 요청 `PosePayload`, 응답은 기존 `GET /analysis/{id}/result` 와 같은 모양
  - `PosePayload` 필드: `camera_angle: str`, `club: str | None`, `fps: float`, `resolution: tuple[int,int]`, `frames: list[PoseFrame]`
  - `PoseFrame` 필드: `t: float`, `world: list[list[float]]`, `xy: list[list[float]]`, `vis: list[float]`

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`backend/tests/test_pose_payload.py`:

```python
"""
브라우저가 보낸 좌표를 PoseSequence 로 바꾸는 어댑터 테스트.

이 어댑터 하나만 새로 쓰면 compute_metrics·detect_phases·build_tracks 는
그대로 쓴다. 그래서 여기서 모양이 틀리면 조용히 엉뚱한 지표가 나온다.
"""
import numpy as np
import pytest
from fastapi import HTTPException

from app.api.endpoints.analysis_from_pose import PoseFrame, PosePayload, sequence_from_payload


def _frame(t: float) -> PoseFrame:
    return PoseFrame(
        t=t,
        world=[[0.0, 0.0, 0.0]] * 33,
        xy=[[0.5, 0.5]] * 33,
        vis=[0.9] * 33,
    )


def _payload(n: int = 10, fps: float = 30.0) -> PosePayload:
    return PosePayload(
        camera_angle="down_the_line",
        club="드라이버",
        fps=fps,
        resolution=(1080, 1920),
        frames=[_frame(i / fps) for i in range(n)],
    )


def test_shapes_match_pose_sequence():
    seq = sequence_from_payload(_payload(12))
    assert seq.world.shape == (12, 33, 3)
    assert seq.xy_px.shape == (12, 33, 2)
    assert seq.visibility.shape == (12, 33)
    assert seq.frame_indices.shape == (12,)


def test_normalised_xy_becomes_pixels():
    """브라우저는 0~1 로 보낸다. 지표는 픽셀을 기대한다."""
    seq = sequence_from_payload(_payload(3))
    assert seq.xy_px[0, 0, 0] == pytest.approx(0.5 * 1080)
    assert seq.xy_px[0, 0, 1] == pytest.approx(0.5 * 1920)


def test_frame_indices_follow_time_and_fps():
    """템포 지표가 프레임 번호와 fps 로 경과 초를 센다."""
    seq = sequence_from_payload(_payload(5, fps=60.0))
    assert list(seq.frame_indices) == [0, 1, 2, 3, 4]
    assert seq.fps == 60.0


def test_rejects_too_few_frames():
    """3프레임 미만이면 PoseSequence 계약이 깨진다."""
    with pytest.raises(HTTPException) as exc:
        sequence_from_payload(_payload(2))
    assert exc.value.status_code == 400
    assert "프레임" in exc.value.detail


def test_rejects_wrong_landmark_count():
    """MediaPipe BlazePose 는 33점이다. 다르면 지표 인덱스가 어긋난다."""
    bad = _payload(5)
    bad.frames[2].world = [[0.0, 0.0, 0.0]] * 20
    with pytest.raises(HTTPException) as exc:
        sequence_from_payload(bad)
    assert exc.value.status_code == 400
    assert "33" in exc.value.detail


def test_rejects_non_finite_numbers():
    """NaN 이 섞이면 지표가 조용히 NaN 이 된다."""
    bad = _payload(5)
    bad.frames[1].xy = [[float("nan"), 0.5]] * 33
    with pytest.raises(HTTPException) as exc:
        sequence_from_payload(bad)
    assert exc.value.status_code == 400


def test_rejects_absurd_frame_count():
    """페이로드 크기 상한. 600프레임이면 20초 분량이다."""
    with pytest.raises(HTTPException) as exc:
        sequence_from_payload(_payload(700))
    assert exc.value.status_code == 400
```

- [ ] **Step 2: 실패를 확인한다**

```bash
cd backend && .venv/bin/pytest tests/test_pose_payload.py -q
```
기대: `ModuleNotFoundError: No module named 'app.api.endpoints.analysis_from_pose'`

- [ ] **Step 3: 어댑터와 엔드포인트를 구현한다**

`backend/app/api/endpoints/analysis_from_pose.py`:

```python
"""
POST /analysis — 브라우저가 뽑은 좌표를 받아 지표와 피드백을 돌려준다.

포즈 추출이 폰으로 옮겨가면서 서버가 할 일은 계산뿐이다. 업로드 →
폴링 → 결과 3단계가 동기 호출 하나가 된다.
"""
from __future__ import annotations

import datetime
import uuid

import numpy as np
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user_id
from app.core.database import get_db
from app.models import Analysis
from app.services.feedback.llm import polish
from app.services.feedback.rules import evaluate
from app.services.swing.metrics import compute_metrics, metrics_to_json
from app.services.swing.phases import detect_phases
from app.services.swing.pipeline import PHASE_LABELS, summarise_metrics
from app.services.swing.tracks import build_tracks
from app.services.swing.types import PoseSequence

router = APIRouter()

LANDMARK_COUNT = 33          # MediaPipe BlazePose
MIN_FRAMES = 3               # PoseSequence 계약
MAX_FRAMES = 600             # 30fps 기준 20초. 페이로드 상한
CAMERA_ANGLES = frozenset({"down_the_line", "face_on", "angled"})


class PoseFrame(BaseModel):
    t: float
    world: list[list[float]]
    xy: list[list[float]]
    vis: list[float]


class PosePayload(BaseModel):
    camera_angle: str
    club: str | None = None
    fps: float
    resolution: tuple[int, int]
    frames: list[PoseFrame]


def _bad(detail: str) -> HTTPException:
    return HTTPException(status_code=400, detail=detail)


def sequence_from_payload(payload: PosePayload) -> PoseSequence:
    """브라우저 좌표를 PoseSequence 로. 모양이 틀리면 400.

    조용히 통과시키면 안 된다. 지표 계산은 인덱스 33점을 전제로 하고,
    NaN 이 하나 섞이면 결과가 통째로 NaN 이 된다.
    """
    frames = payload.frames
    if not (MIN_FRAMES <= len(frames) <= MAX_FRAMES):
        raise _bad(
            f"프레임 수가 맞지 않습니다. ({MIN_FRAMES}~{MAX_FRAMES}개, 받은 값 {len(frames)}개)"
        )
    if payload.camera_angle not in CAMERA_ANGLES:
        raise _bad("촬영 각도를 선택해 주세요. (후면/정면/45°)")
    if payload.fps <= 0:
        raise _bad("영상의 초당 프레임 수가 올바르지 않습니다.")

    width, height = payload.resolution
    if width <= 0 or height <= 0:
        raise _bad("영상 해상도가 올바르지 않습니다.")

    for i, f in enumerate(frames):
        if not (len(f.world) == len(f.xy) == len(f.vis) == LANDMARK_COUNT):
            raise _bad(f"{i}번째 프레임의 랜드마크가 {LANDMARK_COUNT}개가 아닙니다.")

    world = np.array([f.world for f in frames], dtype=np.float32)
    xy = np.array([f.xy for f in frames], dtype=np.float32)
    vis = np.array([f.vis for f in frames], dtype=np.float32)
    times = np.array([f.t for f in frames], dtype=np.float64)

    for name, arr in (("world", world), ("xy", xy), ("vis", vis), ("t", times)):
        if not bool(np.isfinite(arr).all()):
            raise _bad(f"좌표에 유효하지 않은 값이 있습니다. ({name})")

    return PoseSequence(
        world=world,
        xy_px=xy * np.array([width, height], dtype=np.float32),
        visibility=vis,
        frame_indices=np.rint(times * payload.fps).astype(np.int32),
        fps=float(payload.fps),
        resolution_wh=(int(width), int(height)),
    )


@router.post("")
async def analyse(
    payload: PosePayload,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> dict:
    seq = sequence_from_payload(payload)
    phases = detect_phases(seq)
    metrics_payload = metrics_to_json(
        compute_metrics(seq, phases, payload.camera_angle)
    )

    phase_seconds = {
        name: round(float(seq.frame_indices[idx]) / seq.fps, 2)
        for name, idx in phases.items()
    }
    # 영상 크롭 구간을 단계에서 유도한다. detect_swing_window 의 회색조 차분
    # 휴리스틱보다 정확하고, 그 함수는 이 전환으로 사라진다.
    starts = [phase_seconds[k] for k in ("address", "finish") if k in phase_seconds]
    metrics_payload["_meta"] = {
        "camera_angle": payload.camera_angle,
        "club": payload.club,
        "swing_start_sec": round(max(min(starts) - 0.4, 0.0), 2) if starts else 0.0,
        "swing_end_sec": round(max(starts) + 0.4, 2) if starts else 0.0,
        "phase_seconds": phase_seconds,
        "tracks": build_tracks(seq),
        # 좌표를 남긴다. 알고리즘을 고쳐도 영상 없이 재계산할 수 있다.
        "landmarks": {
            "world": [[[round(v, 4) for v in p] for p in f.world] for f in payload.frames],
            "xy": [[[round(v, 4) for v in p] for p in f.xy] for f in payload.frames],
            "t": [round(f.t, 3) for f in payload.frames],
        },
        **summarise_metrics(
            {k: v for k, v in metrics_payload.items() if k != "_meta"}
        ),
    }

    feedback = await polish(
        evaluate({k: v for k, v in metrics_payload.items() if k != "_meta"})
    )

    analysis = Analysis(
        user_id=uuid.UUID(user_id),
        status="done",
        # 채우지 않으면 히스토리의 날짜가 비고 정렬 기준도 사라진다.
        completed_at=datetime.datetime.now(),
        overall_score=feedback.get("overall_score"),
        grade=feedback.get("grade"),
        metrics=metrics_payload,
        feedback=feedback,
        camera_angle=payload.camera_angle,
        club=payload.club,
    )
    db.add(analysis)
    await db.commit()
    await db.refresh(analysis)

    return {
        "analysis_id": str(analysis.id),
        "status": "done",
        "overall_score": analysis.overall_score,
        "grade": analysis.grade,
        "metrics": analysis.metrics,
        "feedback": analysis.feedback,
        "overlay_urls": None,
        "completed_at": analysis.completed_at,
    }
```

이 코드는 Task 4 의 스키마 변경(`Analysis.camera_angle`·`club`,
`upload_id` nullable, `completed_at` 기본값)을 전제한다. **Task 4 를 먼저
끝내고 이 태스크를 완료 처리한다.**

- [ ] **Step 4: 라우터에 붙이고 LLM 타임아웃을 조인다**

`backend/app/api/router.py`:

```python
from app.api.endpoints import health, upload, analysis, auth, history, analysis_from_pose
...
api_router.include_router(analysis_from_pose.router, prefix="/analysis", tags=["Analysis"])
```

`backend/app/services/feedback/llm.py` 의 `httpx.AsyncClient(timeout=20.0)` 를
`timeout=8.0` 으로 바꾼다. 응답이 동기가 되어 사용자가 직접 기다리기 때문이다.
실패해도 규칙 결과가 그대로 나가므로 짧게 잡아도 잃는 것이 없다.

- [ ] **Step 5: 전체 테스트**

```bash
cd backend && .venv/bin/pytest tests/ -q > /tmp/pt.txt 2>&1; EXIT=$?; tail -5 /tmp/pt.txt; echo "EXIT=$EXIT"
```
기대: `EXIT=0`, 201 + 7 = **208개**.

- [ ] **Step 6: 커밋**

```bash
cd /Users/chanhojung/swing-master
git add backend
git commit -m "$(cat <<'EOF'
feat(api): accept landmarks and return the analysis synchronously

포즈 추출이 폰으로 옮겨가면서 서버가 할 일은 계산뿐이다. 업로드 →
폴링 → 결과 3단계가 동기 호출 하나가 된다. BackgroundTasks 도
queued/processing 상태도 없어진다.

어댑터 하나만 새로 쓰면 compute_metrics·detect_phases·build_tracks 는
그대로 쓴다 — numpy 외 의존성을 두지 않은 제약이 여기서 값을 한다.

좌표를 _meta.landmarks 에 남긴다. 알고리즘을 고쳐도 영상 없이
재계산할 수 있다. 이번 작업에서 백필을 두 번 하며 그때마다 영상
27건을 내려받아야 했다.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 4: 스키마 변경 — 영상을 분석에서 떼어낸다

**Files:**
- Modify: `backend/app/models.py`
- Create: `backend/alembic/versions/003_analysis_without_upload.py`
- Modify: `backend/app/api/endpoints/history.py`

**Interfaces:**
- Consumes: 없음
- Produces: `Analysis.camera_angle`, `Analysis.club`, `Analysis.video_url` (모두 nullable), `Analysis.upload_id` nullable

- [ ] **Step 1: 모델을 고친다**

`backend/app/models.py` 의 `Analysis` 에서 `upload_id` 를 nullable 로 바꾸고
세 컬럼을 더한다.

```python
    upload_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("uploads.id", ondelete="CASCADE"), nullable=True
    )
    # 촬영 각도는 어떤 지표를 계산할 수 있는지를 정한다(metrics.METRIC_ANGLES).
    # 영상이 분석의 전제가 아니게 되면서 uploads 가 아니라 여기에 둔다.
    camera_angle: Mapped[str | None] = mapped_column(String(20), nullable=True)
    club: Mapped[str | None] = mapped_column(String(20), nullable=True)
    # 재생용 영상. 분석이 끝난 뒤 백그라운드로 올라와 채워진다.
    video_url: Mapped[str | None] = mapped_column(Text, nullable=True)
```

`Analysis.upload` 관계도 `Mapped["Upload | None"]` 로 바꾼다.

- [ ] **Step 2: 마이그레이션을 쓴다**

`backend/alembic/versions/003_analysis_without_upload.py`:

```python
"""analyses 를 영상과 독립시킨다

Revision ID: 003
Revises: 002
Create Date: 2026-09-20 00:00:00.000000

포즈 추출이 폰으로 옮겨가면서 영상은 분석의 입력이 아니라 재생용
부가물이 된다. upload_id 가 NOT NULL 이면 영상 없이 분석을 만들 수 없다.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("analyses", sa.Column("camera_angle", sa.String(20), nullable=True))
    op.add_column("analyses", sa.Column("club", sa.String(20), nullable=True))
    op.add_column("analyses", sa.Column("video_url", sa.Text(), nullable=True))
    op.alter_column("analyses", "upload_id", existing_type=sa.UUID(), nullable=True)

    # 기존 값을 uploads 에서 옮긴다. 옛 기록은 NULL 이던 것이 그대로 NULL 이다.
    op.execute("""
        UPDATE analyses a
           SET camera_angle = u.camera_angle,
               club         = u.club,
               video_url    = u.storage_url
          FROM uploads u
         WHERE u.id = a.upload_id
    """)


def downgrade() -> None:
    op.alter_column("analyses", "upload_id", existing_type=sa.UUID(), nullable=False)
    op.drop_column("analyses", "video_url")
    op.drop_column("analyses", "club")
    op.drop_column("analyses", "camera_angle")
```

- [ ] **Step 3: history 가 analyses 의 값을 읽도록 고친다**

`backend/app/api/endpoints/history.py` 에서 `Upload` 조인을 없앤다.

```python
    stmt = (
        select(Analysis)
        .where(Analysis.user_id == uid)
        .order_by(Analysis.created_at.desc())
        .limit(20)
    )
    analyses = list((await db.execute(stmt)).scalars().all())

    items = []
    for a in analyses:
```

그리고 항목의 두 줄을 바꾼다.

```python
            "camera_angle": a.camera_angle,
            "club": a.club,
```

- [ ] **Step 4: analysis_id 로 결과를 읽는 경로를 만든다**

상세 화면 경로가 `upload_id` → `analysis_id` 기준으로 바뀌므로, 그 id 로
저장된 결과를 돌려주는 엔드포인트가 필요하다. 기존
`GET /analysis/{upload_id}/result` 는 옛 기록 때문에 남긴다.

`backend/app/api/endpoints/analysis.py` 에 더한다.

```python
@router.get("/by-id/{analysis_id}")
async def get_by_analysis_id(
    analysis_id: uuid.UUID, db: AsyncSession = Depends(get_db)
) -> dict:
    """analysis_id 로 결과를 읽는다.

    좌표만으로 만든 분석에는 upload 레코드가 없으므로 upload_id 로는
    찾을 수 없다. 옛 기록을 위해 기존 경로는 남긴다.
    """
    analysis = (await db.execute(
        select(Analysis).where(Analysis.id == analysis_id)
    )).scalars().first()
    if not analysis:
        raise HTTPException(status_code=404, detail="분석을 찾을 수 없습니다.")
    return {
        "analysis_id": str(analysis.id),
        "status": analysis.status,
        "overall_score": analysis.overall_score,
        "grade": analysis.grade,
        "metrics": analysis.metrics,
        "feedback": analysis.feedback,
        "overlay_urls": analysis.overlay_urls,
        "video_url": analysis.video_url,
        "completed_at": analysis.completed_at,
    }
```

프론트의 히스토리는 `router.push(`/analysis/${item.analysis_id}`)` 로 바꾸고,
상세 화면은 `/analysis/by-id/{id}` 를 먼저 시도한 뒤 404 면 기존
`/analysis/{id}/result` 로 떨어진다 — 옛 북마크와 기록을 버리지 않는다.

- [ ] **Step 5: Neon 에 적용한다**

```bash
cd backend && DATABASE_URL="<Neon asyncpg URL>" .venv/bin/alembic upgrade head
```

적용 후 확인한다.

```bash
psql "<Neon psql URL>" -tAc "
  select count(*) filter (where camera_angle is not null) || ' / ' || count(*)
    || ' 건에 각도, ' || count(*) filter (where video_url is not null) || ' 건에 영상'
  from public.analyses"
```

- [ ] **Step 6: 전체 테스트와 커밋**

```bash
cd backend && .venv/bin/pytest tests/ -q > /tmp/pt.txt 2>&1; EXIT=$?; tail -5 /tmp/pt.txt; echo "EXIT=$EXIT"
cd /Users/chanhojung/swing-master && git add backend && git commit -m "$(cat <<'EOF'
refactor(db): make the analysis independent of the uploaded video

영상은 분석의 입력이 아니라 재생용 부가물이 된다. upload_id 가
NOT NULL 이면 영상 없이 분석을 만들 수 없어 좌표만으로 분석하는
새 경로가 성립하지 않는다.

camera_angle·club 을 uploads 에서 analyses 로 옮기고 video_url 을
더했다. 기존 값은 마이그레이션에서 조인해 옮긴다.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 5: 브라우저 추출 모듈

**Files:**
- Create: `frontend/src/lib/pose/types.ts`
- Create: `frontend/src/lib/pose/extractor.ts`
- Create: `frontend/src/lib/pose/sources.ts`
- Create: `frontend/src/lib/pose/swingWindow.ts`

**Interfaces:**
- Consumes: Task 3 의 `PosePayload` 모양
- Produces:
  - `extractFromFile(file: File, onProgress?: (r: number) => void): Promise<Extraction>`
  - `createCameraExtractor(stream: MediaStream): CameraExtractor`
  - `findSwingWindow(frames: PoseFrameData[]): { start: number; end: number }`
  - `Extraction` = `{ frames: PoseFrameData[]; fps: number; resolution: [number, number]; expectedFrames: number }`
  - `PoseFrameData` = `{ t: number; world: number[][]; xy: number[][]; vis: number[] }`

- [ ] **Step 1: 타입을 정의한다**

`frontend/src/lib/pose/types.ts`:

```typescript
/** 서버 analysis_from_pose.PoseFrame 과 1:1 로 대응해야 한다. */
export interface PoseFrameData {
  /** 영상 시작부터의 초. */
  t: number;
  /** (33, 3) 미터 단위 3D. 회전 지표가 이것 없이 계산되지 않는다. */
  world: number[][];
  /** (33, 2) 0~1 정규화. 서버가 resolution 을 곱해 픽셀로 바꾼다. */
  xy: number[][];
  /** (33,) 0~1 */
  vis: number[];
}

export interface Extraction {
  frames: PoseFrameData[];
  fps: number;
  resolution: [number, number];
  /** 영상 길이 × fps. frames.length 와 비교해 유실을 센다. */
  expectedFrames: number;
}

/** MediaPipe BlazePose 의 손목·팔꿈치 인덱스. 스윙 구간 탐지에 쓴다. */
export const L_WRIST = 15;
export const R_WRIST = 16;
```

- [ ] **Step 2: 스윙 구간 탐지를 쓴다 (순수 함수)**

`frontend/src/lib/pose/swingWindow.ts`:

```typescript
import { L_WRIST, R_WRIST, type PoseFrameData } from "./types";

/**
 * 좌표에서 스윙 구간을 찾는다.
 *
 * 서버의 detect_swing_window 는 회색조 차분을 써서 "공 줍기·이동"을 스윙으로
 * 오인했고, 좁히려던 시도가 정상 6/11 → 2/11 로 악화돼 원복됐다. 손목이
 * 올라갔다 빠르게 내려오는 패턴은 오인할 여지가 거의 없다.
 *
 * 손목 속도가 가장 큰 지점을 임팩트로 보고 그 앞뒤를 구간으로 잡는다.
 */
const BEFORE_SEC = 1.6;   // 임팩트 이전 — 어드레스와 백스윙을 담는다
const AFTER_SEC = 1.2;    // 임팩트 이후 — 팔로우스루와 피니시를 담는다

export function findSwingWindow(
  frames: PoseFrameData[],
): { start: number; end: number } {
  if (frames.length < 3) {
    return { start: frames[0]?.t ?? 0, end: frames[frames.length - 1]?.t ?? 0 };
  }

  let peakAt = frames[0].t;
  let peakSpeed = -1;
  for (let i = 1; i < frames.length; i += 1) {
    const dt = frames[i].t - frames[i - 1].t;
    if (dt <= 0) continue;
    let best = 0;
    for (const idx of [L_WRIST, R_WRIST]) {
      const dx = frames[i].xy[idx][0] - frames[i - 1].xy[idx][0];
      const dy = frames[i].xy[idx][1] - frames[i - 1].xy[idx][1];
      best = Math.max(best, Math.hypot(dx, dy) / dt);
    }
    if (best > peakSpeed) {
      peakSpeed = best;
      peakAt = frames[i].t;
    }
  }

  const first = frames[0].t;
  const last = frames[frames.length - 1].t;
  return {
    start: Math.max(first, peakAt - BEFORE_SEC),
    end: Math.min(last, peakAt + AFTER_SEC),
  };
}

/** 구간 안의 프레임만 남긴다. */
export function clipToWindow(
  frames: PoseFrameData[],
  window: { start: number; end: number },
): PoseFrameData[] {
  return frames.filter((f) => f.t >= window.start && f.t <= window.end);
}
```

- [ ] **Step 3: 추출기를 쓴다**

`frontend/src/lib/pose/extractor.ts`:

```typescript
import { FilesetResolver, PoseLandmarker } from "@mediapipe/tasks-vision";

import type { PoseFrameData } from "./types";

/**
 * PoseLandmarker 를 감싼다. 프레임이 어디서 오는지 모른다.
 *
 * 모델과 WASM 을 우리 쪽에서 서빙한다. 구글 CDN 을 런타임 의존으로 두지
 * 않고, 서버가 쓰던 것과 같은 모델이라야 숫자가 비교 가능하다.
 */
let cached: PoseLandmarker | null = null;

export async function getLandmarker(): Promise<PoseLandmarker> {
  if (cached) return cached;
  const fileset = await FilesetResolver.forVisionTasks("/mp-wasm");
  cached = await PoseLandmarker.createFromOptions(fileset, {
    baseOptions: {
      modelAssetPath: "/pose_landmarker_lite.task",
      delegate: "GPU",
    },
    runningMode: "VIDEO",
    numPoses: 1,
    // 서버 pose.py 와 같은 값. 임계값이 다르면 인식되는 프레임이 달라진다.
    minPoseDetectionConfidence: 0.25,
    minPosePresenceConfidence: 0.25,
    minTrackingConfidence: 0.25,
  });
  return cached;
}

/** 한 프레임을 추론해 좌표로 바꾼다. 포즈가 없으면 null. */
export function detectFrame(
  landmarker: PoseLandmarker,
  source: HTMLVideoElement,
  timestampMs: number,
  t: number,
): PoseFrameData | null {
  const res = landmarker.detectForVideo(source, timestampMs);
  if (res.worldLandmarks.length === 0 || res.landmarks.length === 0) return null;
  return {
    t,
    world: res.worldLandmarks[0].map((l) => [l.x, l.y, l.z]),
    xy: res.landmarks[0].map((l) => [l.x, l.y]),
    vis: res.landmarks[0].map((l) => l.visibility ?? 0),
  };
}
```

- [ ] **Step 4: 공급원 둘을 쓴다**

`frontend/src/lib/pose/sources.ts`:

```typescript
import { detectFrame, getLandmarker } from "./extractor";
import type { Extraction, PoseFrameData } from "./types";

/**
 * 파일에서 좌표를 뽑는다.
 *
 * 해상도를 깎지 않고 원본 프레임을 그대로 넘긴다. 서버는 640px 로 줄여
 * 넣어서 멀리 찍힌 골퍼가 어깨폭 17px 이 됐다. MediaPipe 가 자체 ROI 크롭을
 * 원본 픽셀에서 하게 해야 정밀도가 산다.
 */
export async function extractFromFile(
  file: File,
  onProgress?: (ratio: number) => void,
): Promise<Extraction> {
  const landmarker = await getLandmarker();
  const video = document.createElement("video");
  video.src = URL.createObjectURL(file);
  video.muted = true;
  video.playsInline = true;

  try {
    await new Promise<void>((resolve, reject) => {
      video.onloadedmetadata = () => resolve();
      video.onerror = () => reject(new Error("영상을 읽지 못했습니다"));
    });

    const duration = Number.isFinite(video.duration) ? video.duration : 0;
    const frames: PoseFrameData[] = [];
    let ticks = 0;

    await video.play();
    await new Promise<void>((resolve) => {
      const tick = () => {
        if (video.ended) { resolve(); return; }
        ticks += 1;
        const got = detectFrame(landmarker, video, performance.now(), video.currentTime);
        if (got) frames.push(got);
        if (duration > 0) onProgress?.(Math.min(video.currentTime / duration, 1));
        video.requestVideoFrameCallback(tick);
      };
      video.requestVideoFrameCallback(tick);
    });

    return {
      frames,
      fps: duration > 0 ? ticks / duration : 30,
      resolution: [video.videoWidth, video.videoHeight],
      expectedFrames: ticks,
    };
  } finally {
    URL.revokeObjectURL(video.src);
  }
}

export interface CameraExtractor {
  video: HTMLVideoElement;
  start: () => void;
  stop: () => Extraction;
}

/**
 * 카메라 스트림에서 실시간으로 뽑는다.
 *
 * 폰이 버거우면 프레임이 조용히 건너뛰어진다. 기대 프레임 수(ticks)와 실제
 * 인식 수(frames.length)를 따로 세어 화면에 보여준다 — 결과가 나쁠 때
 * 원인을 알 수 있어야 한다.
 */
export function createCameraExtractor(stream: MediaStream): CameraExtractor {
  const video = document.createElement("video");
  video.srcObject = stream;
  video.muted = true;
  video.playsInline = true;

  const frames: PoseFrameData[] = [];
  let ticks = 0;
  let running = false;
  let t0 = 0;

  const loop = async () => {
    const landmarker = await getLandmarker();
    const tick = () => {
      if (!running) return;
      ticks += 1;
      const t = (performance.now() - t0) / 1000;
      const got = detectFrame(landmarker, video, performance.now(), t);
      if (got) frames.push(got);
      video.requestVideoFrameCallback(tick);
    };
    video.requestVideoFrameCallback(tick);
  };

  return {
    video,
    start: () => {
      running = true;
      t0 = performance.now();
      frames.length = 0;
      ticks = 0;
      void video.play().then(loop);
    },
    stop: () => {
      running = false;
      const elapsed = (performance.now() - t0) / 1000;
      return {
        frames,
        fps: elapsed > 0 ? ticks / elapsed : 30,
        resolution: [video.videoWidth, video.videoHeight],
        expectedFrames: ticks,
      };
    },
  };
}
```

- [ ] **Step 5: 타입 검사와 커밋**

```bash
cd frontend && npx tsc --noEmit && npm run build 2>&1 | tail -3
cd /Users/chanhojung/swing-master && git add frontend/src/lib/pose
git commit -m "$(cat <<'EOF'
feat(pose): extract landmarks in the browser

추출기는 프레임이 어디서 오는지 모르고, 스윙 구간 탐지는 MediaPipe 를
모른다. 공급원 둘(카메라 스트림 / 파일)에 추출기 하나를 꽂는다.

해상도를 깎지 않고 원본 프레임을 넘긴다. 서버는 640px 로 줄여 넣어서
멀리 찍힌 골퍼가 어깨폭 17px 이 됐다.

스윙 구간을 손목 속도로 찾는다. 서버의 회색조 차분은 공 줍기·이동을
스윙으로 오인했고 좁히려던 시도가 6/11 → 2/11 로 악화돼 원복됐다.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 6: 촬영 화면과 파일 경로

**Files:**
- Create: `frontend/src/app/capture/page.tsx`
- Modify: `frontend/src/app/upload/page.tsx`
- Modify: `frontend/src/lib/api.ts` (분석 호출 추가)

**Interfaces:**
- Consumes: Task 5 의 `extractFromFile`·`createCameraExtractor`·`findSwingWindow`·`clipToWindow`, Task 3 의 `POST /analysis`
- Produces: 없음 (화면)

- [ ] **Step 1: 분석 호출을 api.ts 에 더한다**

```typescript
import type { Extraction } from "@/lib/pose/types";

export interface AnalysisResponse {
  analysis_id: string;
  overall_score: number | null;
  grade: string | null;
  metrics: Record<string, unknown>;
  feedback: Record<string, unknown>;
}

export async function requestAnalysis(
  extraction: Extraction,
  frames: Extraction["frames"],
  cameraAngle: string,
  club: string,
): Promise<AnalysisResponse> {
  const res = await apiClient.post("/analysis", {
    camera_angle: cameraAngle,
    club,
    fps: extraction.fps,
    resolution: extraction.resolution,
    frames,
  });
  return res.data as AnalysisResponse;
}
```

- [ ] **Step 2: 촬영 화면을 만든다**

`frontend/src/app/capture/page.tsx` 에 다음 흐름을 구현한다.

1. `navigator.mediaDevices.getUserMedia({ video: { facingMode: "environment" }, audio: false })`
   를 **try-catch 로 감싸고 실패 시 한국어 안내**를 띄운다(AGENTS.md 절대 규칙).
2. `createCameraExtractor(stream)` 로 추출기를 만들고 `video` 를 화면에 붙인다.
3. 녹화 버튼 → `extractor.start()` 와 `new MediaRecorder(stream)` 을 함께 시작.
4. 녹화 중 인식 프레임 수를 표시한다: `{frames}/{ticks} 인식`.
5. 정지 → `extractor.stop()` → `findSwingWindow` → `clipToWindow` →
   `requestAnalysis` → `router.push('/analysis/' + analysis_id)`.
6. `MediaRecorder` 의 blob 은 Task 8 에서 백그라운드 업로드에 쓴다.

카메라 권한 거부 시 문구는 `"카메라 권한이 필요합니다. 브라우저 설정에서 허용한 뒤 다시 시도해 주세요."` 로 한다.

- [ ] **Step 3: 파일 경로를 새 흐름으로 바꾼다**

`frontend/src/app/upload/page.tsx` 의 `uploadMutation` 을 교체한다. 영상을
올려 분석하던 것을 **좌표를 뽑아 분석하는 것**으로 바꾼다.

```tsx
  const analyseMutation = useMutation({
    mutationFn: async (file: File) => {
      setPrepProgress(0);
      const extraction = await extractFromFile(file, setPrepProgress);
      setPrepProgress(null);
      const window = findSwingWindow(extraction.frames);
      const clipped = clipToWindow(extraction.frames, window);
      if (clipped.length < 3) {
        throw new Error("스윙을 찾지 못했습니다. 전신이 보이도록 다시 촬영해 주세요.");
      }
      return requestAnalysis(extraction, clipped, cameraAngle, club);
    },
  });
```

완료되면 `router.push('/analysis/' + data.analysis_id)`. **폴링 코드는
지운다** — 응답이 동기이므로 `statusData`·`refetchInterval`·`useEffect` 전환
로직이 모두 불필요하다.

`downscaleVideo` 는 **여기서 쓰지 않는다.** 분석에 영상을 보내지 않으므로
줄일 이유가 없다. Task 8 의 재생용 업로드에서만 쓴다.

- [ ] **Step 4: 타입 검사·빌드·커밋**

```bash
cd frontend && npx tsc --noEmit && npm run build 2>&1 | tail -3
cd /Users/chanhojung/swing-master && git add frontend/src
git commit -m "$(cat <<'EOF'
feat(ui): analyse from landmarks instead of uploading the video

촬영 화면을 새로 만들고 파일 경로를 좌표 기반으로 바꿨다. 응답이
동기이므로 폴링 코드를 지웠다.

녹화 중 인식 프레임 수를 보여준다. 폰이 버거우면 프레임이 조용히
건너뛰어지므로, 결과가 나쁠 때 원인을 알 수 있어야 한다.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 7: 상세 화면 — 좌표로 스켈레톤을 그린다

**Files:**
- Modify: `frontend/src/app/analysis/[id]/page.tsx`
- Modify: `frontend/src/lib/metrics.ts` (landmarks 읽기 추가)

**Interfaces:**
- Consumes: Task 3 이 저장하는 `_meta.landmarks`
- Produces: 없음 (화면)

- [ ] **Step 1: metrics.ts 에 landmarks 읽기를 더한다**

```typescript
/** 저장된 프레임별 좌표. 옛 기록에는 없다. */
export interface StoredLandmarks {
  xy: number[][][];
  t: number[];
}

/** "_meta.landmarks" 를 안전하게 꺼낸다. 모양이 다르면 undefined. */
export function readLandmarks(
  metrics: Record<string, unknown> | undefined,
): StoredLandmarks | undefined {
  const meta = metrics?.["_meta"];
  if (typeof meta !== "object" || meta === null) return undefined;
  const raw = (meta as Record<string, unknown>).landmarks;
  if (typeof raw !== "object" || raw === null) return undefined;
  const obj = raw as Record<string, unknown>;
  if (!Array.isArray(obj.xy) || !Array.isArray(obj.t)) return undefined;
  if (obj.xy.length === 0 || obj.xy.length !== obj.t.length) return undefined;
  return { xy: obj.xy as number[][][], t: obj.t as number[] };
}

/** MediaPipe BlazePose 의 뼈대. 스켈레톤을 그릴 때 쓴다. */
export const POSE_EDGES: [number, number][] = [
  [11, 12], [11, 13], [13, 15], [12, 14], [14, 16],
  [11, 23], [12, 24], [23, 24],
  [23, 25], [25, 27], [24, 26], [26, 28],
];
```

- [ ] **Step 2: 단계 카드를 캔버스로 바꾼다**

`analysis/[id]/page.tsx` 에서 단계 카드가 `<img src={overlay_urls[phase]} />`
를 쓰는 부분을 다음 규칙으로 바꾼다.

```tsx
// 좌표가 있으면 그린다. 없으면 저장된 이미지를 쓴다.
// 옛 기록 28건은 오버레이 JPEG 를 갖고 좌표가 없고, 새 기록은 반대다.
// 둘 다 다뤄야 한다 — 옛 기록을 버리지도, 가짜 좌표를 만들지도 않는다.
{landmarks
  ? <PhaseSkeleton landmarks={landmarks} timeSec={phaseSeconds[phase]} videoRef={videoRef} />
  : overlayUrls?.[phase]
    ? <img src={overlayUrls[phase]} alt={PHASE_LABELS[phase]} />
    : <div className="text-muted">이미지 없음</div>}
```

`PhaseSkeleton` 은 `timeSec` 에 가장 가까운 `landmarks.t` 인덱스를 찾아
`POSE_EDGES` 를 캔버스에 그린다. 손 궤적을 그리는 `drawHandPath` 와 같은
좌표 환산(`containRect`)을 쓴다.

- [ ] **Step 3: 타입 검사·빌드·커밋**

```bash
cd frontend && npx tsc --noEmit && npm run build 2>&1 | tail -3
cd /Users/chanhojung/swing-master && git add frontend/src
git commit -m "$(cat <<'EOF'
feat(ui): draw phase skeletons from stored landmarks

구워진 JPEG 대신 좌표로 그린다. 켜고 끄고 확대할 수 있다.

옛 기록 28건은 오버레이 이미지를 갖고 좌표가 없다. 새 기록은 반대다.
둘 다 다룬다 — 옛 기록을 버리지도, 가짜 좌표를 만들지도 않는다.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 8: 영상 백그라운드 업로드

**Files:**
- Modify: `backend/app/api/endpoints/upload.py`
- Modify: `frontend/src/app/capture/page.tsx`
- Modify: `frontend/src/app/upload/page.tsx`

**Interfaces:**
- Consumes: Task 4 의 `Analysis.video_url`, Task 6 의 `analysis_id`
- Produces: `POST /upload` 가 `analysis_id` 를 받아 `analyses.video_url` 을 채운다

- [ ] **Step 1: 업로드 엔드포인트를 재생용으로 바꾼다**

`upload.py` 에서 `Upload`·`Analysis` 생성과 `BackgroundTasks` 를 걷어내고,
받은 `analysis_id` 의 `video_url` 만 채운다.

```python
@router.post("")
async def upload_video(
    analysis_id: uuid.UUID = Form(...),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
) -> dict:
    """재생용 영상을 보관한다. 분석은 이미 끝나 있다."""
    content_type = normalise_content_type(file.content_type)
    ...  # 기존 크기 검증과 R2 업로드는 그대로
    analysis = (await db.execute(
        select(Analysis).where(
            Analysis.id == analysis_id, Analysis.user_id == uuid.UUID(user_id)
        )
    )).scalars().first()
    if analysis is None:
        raise HTTPException(status_code=404, detail="분석을 찾을 수 없습니다.")
    analysis.video_url = storage_url
    await db.commit()
    return {"video_url": storage_url}
```

- [ ] **Step 2: 화면에서 백그라운드로 올린다**

두 화면 모두, 분석 응답을 받아 결과 페이지로 넘어간 **뒤에** 영상을 올린다.
여기서 `downscaleVideo` 를 쓴다 — 재생용이므로 640px 로 충분하고 업로드가
빨라진다.

```tsx
// 결과는 이미 보여줬다. 영상은 재생용이므로 기다리지 않는다.
void (async () => {
  const prepared = await downscaleVideo(blob as File);
  const form = new FormData();
  form.append("analysis_id", analysisId);
  form.append("file", prepared.blob, "swing.mp4");
  await apiClient.post("/upload", form);
})();
```

- [ ] **Step 3: 테스트·빌드·커밋**

```bash
cd backend && .venv/bin/pytest tests/ -q > /tmp/pt.txt 2>&1; EXIT=$?; tail -5 /tmp/pt.txt; echo "EXIT=$EXIT"
cd ../frontend && npx tsc --noEmit
cd /Users/chanhojung/swing-master && git add backend frontend
git commit -m "$(cat <<'EOF'
refactor(upload): store the video for replay, not for analysis

분석은 좌표로 이미 끝나 있다. 영상은 재생용이므로 결과를 보여준 뒤
백그라운드로 올린다. 사용자가 기다리지 않는다.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 9: 서버 파이프라인 삭제

**Task 1·2 를 통과했고 Task 3~8 이 실제 폰에서 동작하는 것을 확인한 뒤에만
실행한다.** 지우면 되돌릴 곳이 없다.

**Files:**
- Delete: `backend/app/services/swing/pose.py`, `backend/app/services/swing/overlay.py`
- Delete: `backend/app/services/pose_landmarker_lite.task`
- Delete: `backend/tests/swing/test_pose.py`, `backend/tests/swing/test_overlay.py`
- Delete: `frontend/src/app/spike/page.tsx`, `backend/scripts/compare_landmarks.py`
- Modify: `backend/app/services/swing/phases.py` (`detect_swing_window` 제거, cv2 import 제거)
- Modify: `backend/app/services/swing/pipeline.py` (분석 오케스트레이션 제거)
- Modify: `backend/requirements.txt`, `backend/Dockerfile`
- Modify: `backend/app/api/endpoints/analysis.py` (구형 status/result 엔드포인트)

**Interfaces:**
- Consumes: Task 3~8 이 실제 폰에서 동작함
- Produces: 없음

- [ ] **Step 1: 파이썬 코드를 지운다**

`pipeline.py` 에서 `PHASE_LABELS` 와 `summarise_metrics` 는 Task 3 이 쓰므로
남긴다. 나머지(`download_video`, `_render_phase_overlays`,
`process_pose_estimation`)를 지우고, 파일을 `app/services/swing/labels.py`
로 옮긴 뒤 `analysis_from_pose.py` 의 import 를 고친다.

`phases.py` 에서 `detect_swing_window` 와 `import cv2` 를 지운다.

- [ ] **Step 2: 의존성을 지운다**

`requirements.txt` 에서 다음 줄을 제거한다.

```
mediapipe==0.10.33
opencv-python-headless==4.11.0.86
supervision==0.30.3
scipy==1.17.1
matplotlib==3.10.8
av==18.1.0
sounddevice==0.5.5
openai==1.30.1
google-genai==1.73.1
```

`Dockerfile` 의 apt 줄에서 `libgl1 libegl1 libgles2 libglib2.0-0 libgomp1
fonts-nanum` 을 빼고, opencv 재설치 줄(`pip uninstall ... opencv ...`)도
통째로 지운다. 이제 GUI 라이브러리도 한글 폰트도 필요 없다 — 오버레이를
서버에서 그리지 않기 때문이다.

- [ ] **Step 3: 테스트가 남은 것만 통과하는지 본다**

```bash
cd backend && .venv/bin/pytest tests/ -q > /tmp/pt.txt 2>&1; EXIT=$?; tail -5 /tmp/pt.txt; echo "EXIT=$EXIT"
```
기대: `EXIT=0`, **186 + 7 = 193개**. (201 − 15(pose·overlay 테스트) + 7(Task 3 신규))
더 줄었다면 무언가를 잘못 지운 것이다.

- [ ] **Step 4: 이미지가 실제로 작아졌는지 확인한다**

```bash
cd /Users/chanhojung/swing-master
docker build -t swing-api-slim -f backend/Dockerfile . > /tmp/b.log 2>&1
echo "EXIT=$?"; docker images swing-api-slim --format '{{.Size}}'
```
기대: 1.58GB → **약 200MB**.

- [ ] **Step 5: 커밋하고 배포한다**

```bash
git add -A backend frontend
git commit -m "$(cat <<'EOF'
refactor: delete the server-side pose pipeline

포즈 추출이 폰으로 옮겨가 서버에서 mediapipe·opencv·supervision·scipy·
matplotlib 가 필요 없어졌다. Dockerfile 의 GUI 라이브러리와 한글 폰트도
함께 뺀다 — 오버레이를 서버에서 그리지 않기 때문이다.

detect_swing_window 도 사라진다. AGENTS.md 에 "영상 전체를 반환한다
(실패 3/11)" 고 기록된 알려진 결함이 삭제로 해결됐다.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
EOF
)"
git push origin main
```

- [ ] **Step 6: 문서를 맞춘다**

`AGENTS.md` 의 "해소된 설계 쟁점" 에서 "포즈 추정 위치 — 서버 사이드로
확정" 항목을 갱신하고, "TODO" 의 `detect_swing_window` 항목을 지운다.
`docs/01_architecture.md` 와 `docs/02_tech_stack.md` 의 파이프라인 그림도
고친다. `docs/04_roadmap_7days.md` 체크박스를 갱신한다.

---

## 되돌리는 법

Task 9 이전까지는 서버 파이프라인이 그대로 있으므로, 새 경로에 문제가 생기면
프론트에서 기존 업로드 흐름으로 되돌리면 된다. Task 9 이후에는 되돌릴 곳이
없으므로, 그 전에 실제 폰에서 촬영 → 결과 → 재생까지 한 번에 되는 것을
확인한다.
