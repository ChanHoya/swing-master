# 지표 실측화 구현 계획 (Plan 1)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 골프 스윙 지표 8개를 MediaPipe `pose_world_landmarks` 기반 실측으로 계산하고, 측정 불가 시 가짜 기본값 대신 `None`을 반환한다.

**Architecture:** `pose_estimator.py`(439줄, 책임 8개)를 `swing/` 패키지로 분할한다. 핵심은 `swing/metrics.py`를 numpy만 의존하는 순수 함수로 만드는 것 — DB·파일·네트워크를 건드리지 않으므로 실제 영상 없이 합성 좌표로 테스트할 수 있다. 시각화는 supervision의 `VertexAnnotator`/`EdgeAnnotator`가 맡고, 피드백은 규칙 엔진이 확정한 뒤 LLM이 문장만 다듬는다.

**Tech Stack:** Python 3.13, numpy 1.26.4, MediaPipe 0.10.33, supervision 0.30.3, OpenCV 4.x, pytest, FastAPI 0.136

**Spec:** `docs/superpowers/specs/2026-09-16-supervision-metrics-upgrade-design.md`

## Global Constraints

- **가짜 기본값 금지** — 측정 실패 시 `None`. `metrics.get("hip_rotation", 32.0)` 같은 패턴을 새로 만들지 않는다 (스펙 §3.4).
- **`metrics.py`는 numpy만 의존** — cv2·mediapipe·supervision·DB import 금지 (스펙 §4.2).
- **모든 사용자 노출 텍스트는 한국어** (`AGENTS.md`).
- **MediaPipe 랜드마크 인덱스**: 0 코, 11/12 어깨(좌/우), 23/24 힙, 25/26 무릎, 27/28 발목.
- **3D world 좌표**: 힙 중심 원점, 미터 단위. **6개 지표가 사용.**
- **2D 픽셀 좌표**: `sv.KeyPoints.from_mediapipe()` 반환값. **`head_movement`·`weight_shift`만 사용** (스펙 §3.1).
- **어깨 너비 기준**: 40.0cm.
- **촬영 각도**: `down_the_line` | `face_on`. 각도별 계산 가능 지표는 Task 7 참조.
- **커밋 메시지**: `feat:` / `fix:` / `refactor:` / `test:` / `docs:` / `chore:` 접두사 (`AGENTS.md`).

---

## Task 0: 테스트 환경 구축

현재 `backend/tests/test_health.py`는 pytest를 쓰지만 **pytest가 설치되어 있지 않다.** 테스트가 한 번도 실행된 적이 없다는 뜻이다. 이걸 먼저 고치지 않으면 이후 모든 TDD 단계가 불가능하다.

**Files:**
- Create: `backend/requirements-dev.txt`
- Create: `backend/pytest.ini`
- Modify: `backend/requirements.txt`

**Interfaces:**
- Consumes: 없음
- Produces: `pytest` 실행 가능 상태. 이후 모든 Task가 여기에 의존한다.

- [ ] **Step 1: 개발 의존성 파일 생성**

`backend/requirements-dev.txt`:

```
pytest==8.3.4
pytest-asyncio==0.25.0
```

- [ ] **Step 2: pytest 설정 파일 생성**

`backend/pytest.ini`:

```ini
[pytest]
testpaths = tests
python_files = test_*.py
asyncio_mode = auto
```

- [ ] **Step 3: 런타임 의존성에 supervision 추가**

`backend/requirements.txt`의 `starlette==1.0.0` 줄 바로 앞에 알파벳 순서로 삽입:

```
supervision==0.30.3
```

- [ ] **Step 4: 설치**

```bash
cd backend && .venv/bin/pip install -r requirements-dev.txt -r requirements.txt
```

- [ ] **Step 5: 기존 테스트가 통과하는지 확인**

```bash
cd backend && .venv/bin/pytest tests/ -v
```

Expected: `test_health_ok` PASS

FAIL하면 그 원인을 먼저 해결한다. 깨진 테스트 위에 새 테스트를 쌓지 않는다.

- [ ] **Step 6: supervision import 확인**

```bash
cd backend && .venv/bin/python -c "import supervision as sv; print(sv.__version__); print(sv.KeyPoints, sv.VertexAnnotator, sv.EdgeAnnotator)"
```

Expected: `0.30.3` 과 세 클래스가 출력

- [ ] **Step 7: 커밋**

```bash
git add backend/requirements-dev.txt backend/pytest.ini backend/requirements.txt
git commit -m "chore: add pytest and supervision dependencies"
```

---

## Task 1: 자료구조 정의

**Files:**
- Create: `backend/app/services/swing/__init__.py`
- Create: `backend/app/services/swing/types.py`
- Test: `backend/tests/swing/__init__.py`, `backend/tests/swing/test_types.py`

**Interfaces:**
- Consumes: 없음
- Produces:
  - `MetricValue(value: float | None, confidence: float, unit: str, measurable: bool)` — 동결 데이터클래스
  - `MetricValue.unmeasurable(unit: str) -> MetricValue`
  - `MetricValue.failed(unit: str) -> MetricValue`
  - `PoseSequence(world, xy_px, visibility, frame_indices, fps, resolution_wh)` — 동결 데이터클래스, `__len__` 지원
  - `PHASE_KEYS: tuple[str, ...]`

- [ ] **Step 1: 실패하는 테스트 작성**

`backend/tests/swing/__init__.py` (빈 파일)을 만들고, `backend/tests/swing/test_types.py`:

```python
import numpy as np
import pytest

from app.services.swing.types import MetricValue, PoseSequence, PHASE_KEYS


def test_metric_value_holds_measurement():
    m = MetricValue(value=42.5, confidence=0.9, unit="°", measurable=True)
    assert m.value == 42.5
    assert m.confidence == 0.9
    assert m.unit == "°"
    assert m.measurable is True


def test_unmeasurable_has_none_value():
    """촬영 각도상 측정할 수 없는 지표는 값이 없어야 한다."""
    m = MetricValue.unmeasurable(unit="°")
    assert m.value is None
    assert m.measurable is False
    assert m.confidence == 0.0


def test_failed_has_none_value_but_is_measurable():
    """각도상으로는 측정 가능한데 랜드마크가 부족해 실패한 경우."""
    m = MetricValue.failed(unit="cm")
    assert m.value is None
    assert m.measurable is True
    assert m.confidence == 0.0


def test_metric_value_is_frozen():
    m = MetricValue(value=1.0, confidence=1.0, unit="°", measurable=True)
    with pytest.raises(Exception):
        m.value = 2.0  # type: ignore[misc]


def test_phase_keys_are_seven_in_swing_order():
    assert PHASE_KEYS == (
        "address", "takeaway", "top", "downswing",
        "impact", "followthrough", "finish",
    )


def test_pose_sequence_reports_frame_count():
    seq = PoseSequence(
        world=np.zeros((5, 33, 3), dtype=np.float32),
        xy_px=np.zeros((5, 33, 2), dtype=np.float32),
        visibility=np.ones((5, 33), dtype=np.float32),
        frame_indices=np.arange(5, dtype=np.int32),
        fps=60.0,
        resolution_wh=(1280, 720),
    )
    assert len(seq) == 5
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
cd backend && .venv/bin/pytest tests/swing/test_types.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'app.services.swing'`

- [ ] **Step 3: 최소 구현**

`backend/app/services/swing/__init__.py` (빈 파일).

`backend/app/services/swing/types.py`:

```python
"""
swing/types.py — 스윙 분석 파이프라인의 공용 자료구조.

의존성은 numpy 뿐이다. 이 모듈은 DB·파일·네트워크를 알지 못한다.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

# 스윙 7단계 — 시간 순서
PHASE_KEYS: tuple[str, ...] = (
    "address", "takeaway", "top", "downswing",
    "impact", "followthrough", "finish",
)


@dataclass(frozen=True)
class MetricValue:
    """지표 하나의 측정 결과.

    value 가 None 인 경우는 두 가지다.
      - measurable=False : 촬영 각도상 애초에 측정할 수 없다.
      - measurable=True  : 측정 대상이지만 랜드마크가 부족해 실패했다.
    두 경우를 화면에서 다르게 안내해야 하므로 구분해 둔다.
    """

    value: float | None
    confidence: float
    unit: str
    measurable: bool

    @classmethod
    def unmeasurable(cls, unit: str) -> MetricValue:
        """이 촬영 각도에서는 측정할 수 없는 지표."""
        return cls(value=None, confidence=0.0, unit=unit, measurable=False)

    @classmethod
    def failed(cls, unit: str) -> MetricValue:
        """측정 대상이지만 랜드마크 부족으로 계산하지 못한 지표."""
        return cls(value=None, confidence=0.0, unit=unit, measurable=True)


@dataclass(frozen=True)
class PoseSequence:
    """스윙 구간에서 추출한 프레임별 포즈.

    world        : (F, 33, 3) 힙 중심 원점, 미터 단위 3D
    xy_px        : (F, 33, 2) 이미지 픽셀 좌표
    visibility   : (F, 33)    0.0~1.0
    frame_indices: (F,)       원본 영상에서의 프레임 번호
    fps          : 원본 영상의 초당 프레임 수
    resolution_wh: 원본 영상 해상도 (width, height)
    """

    world: np.ndarray
    xy_px: np.ndarray
    visibility: np.ndarray
    frame_indices: np.ndarray
    fps: float
    resolution_wh: tuple[int, int]

    def __len__(self) -> int:
        return int(self.world.shape[0])
```

- [ ] **Step 4: 테스트 통과 확인**

```bash
cd backend && .venv/bin/pytest tests/swing/test_types.py -v
```

Expected: 6 passed

- [ ] **Step 5: 커밋**

```bash
git add backend/app/services/swing/ backend/tests/swing/
git commit -m "feat(swing): add MetricValue and PoseSequence data structures"
```

---

## Task 2: 기하 헬퍼 함수

회전·각도 계산의 토대다. 여기가 틀리면 지표 전부가 틀리므로 먼저 합성 좌표로 못 박는다.

**Files:**
- Create: `backend/app/services/swing/metrics.py`
- Test: `backend/tests/swing/test_metrics_geometry.py`

**Interfaces:**
- Consumes: 없음 (numpy만)
- Produces:
  - `wrap_deg(deg: float) -> float` — 각도를 [-180, 180]으로 정규화
  - `horizontal_angle(p_left: np.ndarray, p_right: np.ndarray) -> float` — 두 3D 점을 잇는 벡터를 수평면(x-z)에 투영한 각도(도)
  - `angle_at(a: np.ndarray, b: np.ndarray, c: np.ndarray) -> float` — b를 꼭짓점으로 하는 a-b-c 사이각(도), 0~180
  - 랜드마크 상수: `NOSE`, `L_SHOULDER`, `R_SHOULDER`, `L_HIP`, `R_HIP`, `L_KNEE`, `R_KNEE`, `L_ANKLE`, `R_ANKLE`
  - `SHOULDER_WIDTH_CM: float = 40.0`

- [ ] **Step 1: 실패하는 테스트 작성**

`backend/tests/swing/test_metrics_geometry.py`:

```python
import math

import numpy as np
import pytest

from app.services.swing.metrics import (
    SHOULDER_WIDTH_CM,
    L_ANKLE,
    L_HIP,
    L_KNEE,
    L_SHOULDER,
    NOSE,
    R_ANKLE,
    R_HIP,
    R_KNEE,
    R_SHOULDER,
    angle_at,
    horizontal_angle,
    wrap_deg,
)


def test_landmark_indices_match_mediapipe():
    """MediaPipe BlazePose 33점 규격."""
    assert (NOSE, L_SHOULDER, R_SHOULDER) == (0, 11, 12)
    assert (L_HIP, R_HIP) == (23, 24)
    assert (L_KNEE, R_KNEE) == (25, 26)
    assert (L_ANKLE, R_ANKLE) == (27, 28)
    assert SHOULDER_WIDTH_CM == 40.0


@pytest.mark.parametrize(
    "raw,expected",
    [(0.0, 0.0), (180.0, 180.0), (190.0, -170.0), (-190.0, 170.0), (370.0, 10.0)],
)
def test_wrap_deg_normalizes_to_half_turn(raw, expected):
    assert wrap_deg(raw) == pytest.approx(expected, abs=1e-6)


def test_horizontal_angle_is_zero_when_aligned_with_x_axis():
    """어깨가 카메라와 나란하면(x축 방향) 0도."""
    left = np.array([-0.2, 0.0, 0.0], dtype=np.float32)
    right = np.array([0.2, 0.0, 0.0], dtype=np.float32)
    assert horizontal_angle(left, right) == pytest.approx(0.0, abs=1e-4)


def test_horizontal_angle_is_ninety_when_rotated_into_depth():
    """몸이 90도 돌아 어깨가 깊이(z) 방향으로 서면 90도."""
    left = np.array([0.0, 0.0, -0.2], dtype=np.float32)
    right = np.array([0.0, 0.0, 0.2], dtype=np.float32)
    assert horizontal_angle(left, right) == pytest.approx(90.0, abs=1e-4)


def test_horizontal_angle_ignores_vertical_component():
    """y(상하)는 수평 회전과 무관하므로 결과가 바뀌면 안 된다."""
    left = np.array([-0.2, 5.0, 0.0], dtype=np.float32)
    right = np.array([0.2, -3.0, 0.0], dtype=np.float32)
    assert horizontal_angle(left, right) == pytest.approx(0.0, abs=1e-4)


def test_angle_at_right_angle():
    a = np.array([1.0, 0.0, 0.0], dtype=np.float32)
    b = np.array([0.0, 0.0, 0.0], dtype=np.float32)
    c = np.array([0.0, 1.0, 0.0], dtype=np.float32)
    assert angle_at(a, b, c) == pytest.approx(90.0, abs=1e-4)


def test_angle_at_straight_line():
    """다리를 곧게 폈을 때 힙-무릎-발목은 180도."""
    a = np.array([0.0, 0.0, 0.0], dtype=np.float32)
    b = np.array([0.0, 1.0, 0.0], dtype=np.float32)
    c = np.array([0.0, 2.0, 0.0], dtype=np.float32)
    assert angle_at(a, b, c) == pytest.approx(180.0, abs=1e-4)


def test_angle_at_returns_nan_for_degenerate_input():
    """두 점이 겹치면 각도가 정의되지 않는다. 0을 지어내면 안 된다."""
    p = np.array([1.0, 1.0, 1.0], dtype=np.float32)
    assert math.isnan(angle_at(p, p, np.array([2.0, 2.0, 2.0], dtype=np.float32)))
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
cd backend && .venv/bin/pytest tests/swing/test_metrics_geometry.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'app.services.swing.metrics'`

- [ ] **Step 3: 최소 구현**

`backend/app/services/swing/metrics.py`:

```python
"""
swing/metrics.py — 포즈 좌표에서 골프 스윙 지표를 계산한다.

순수 함수만 둔다. numpy 외의 의존성을 추가하지 말 것.
그래야 실제 영상 없이 합성 좌표로 테스트할 수 있다.
"""
from __future__ import annotations

import math

import numpy as np

# ── MediaPipe BlazePose 33점 인덱스 ────────────────────────────────────────
NOSE = 0
L_SHOULDER, R_SHOULDER = 11, 12
L_HIP, R_HIP = 23, 24
L_KNEE, R_KNEE = 25, 26
L_ANKLE, R_ANKLE = 27, 28

# 성인 평균 어깨 너비. 픽셀 → cm 환산의 기준자로 쓴다.
SHOULDER_WIDTH_CM: float = 40.0


def wrap_deg(deg: float) -> float:
    """각도를 [-180, 180] 범위로 정규화한다."""
    return (deg + 180.0) % 360.0 - 180.0


def horizontal_angle(p_left: np.ndarray, p_right: np.ndarray) -> float:
    """두 3D 점을 잇는 벡터를 수평면(x-z)에 투영한 각도(도).

    y(상하) 성분은 무시한다. 몸통의 좌우 회전만 보기 위해서다.
    """
    dx = float(p_right[0] - p_left[0])
    dz = float(p_right[2] - p_left[2])
    return math.degrees(math.atan2(dz, dx))


def angle_at(a: np.ndarray, b: np.ndarray, c: np.ndarray) -> float:
    """b를 꼭짓점으로 하는 a-b-c 사이각(도), 0~180.

    벡터 길이가 0이면 각도가 정의되지 않으므로 NaN을 반환한다.
    0을 반환하면 "완전히 접힌 관절"로 오독되므로 그렇게 하지 않는다.
    """
    v1 = np.asarray(a, dtype=np.float64) - np.asarray(b, dtype=np.float64)
    v2 = np.asarray(c, dtype=np.float64) - np.asarray(b, dtype=np.float64)
    n1 = float(np.linalg.norm(v1))
    n2 = float(np.linalg.norm(v2))
    if n1 == 0.0 or n2 == 0.0:
        return math.nan
    cos = float(np.dot(v1, v2)) / (n1 * n2)
    return math.degrees(math.acos(max(-1.0, min(1.0, cos))))
```

- [ ] **Step 4: 테스트 통과 확인**

```bash
cd backend && .venv/bin/pytest tests/swing/test_metrics_geometry.py -v
```

Expected: 12 passed

- [ ] **Step 5: 커밋**

```bash
git add backend/app/services/swing/metrics.py backend/tests/swing/test_metrics_geometry.py
git commit -m "feat(swing): add geometry helpers for metric calculation"
```

---

## Task 3: 회전 지표 — 어깨 회전 · 힙 회전 · X-factor

가짜 기본값 `88.0`·`32.0`이 박혀 있던 두 지표와, 스펙에서 새로 추가한 X-factor다.

**Files:**
- Modify: `backend/app/services/swing/metrics.py`
- Test: `backend/tests/swing/test_metrics_rotation.py`

**Interfaces:**
- Consumes: Task 2의 `wrap_deg`, `horizontal_angle`, 랜드마크 상수
- Produces:
  - `rotation_between(world_ref, world_target, idx_left, idx_right) -> float` — 기준 프레임 대비 회전량(도), 0~180
  - `shoulder_rotation(world, addr_i, top_i) -> float`
  - `hip_rotation(world, addr_i, top_i) -> float`
  - `x_factor(shoulder_deg, hip_deg) -> float`

- [ ] **Step 1: 실패하는 테스트 작성**

`backend/tests/swing/test_metrics_rotation.py`:

```python
import math

import numpy as np
import pytest

from app.services.swing.metrics import (
    L_HIP,
    L_SHOULDER,
    R_HIP,
    R_SHOULDER,
    hip_rotation,
    rotation_between,
    shoulder_rotation,
    x_factor,
)


def _blank_world(frames: int = 2) -> np.ndarray:
    return np.zeros((frames, 33, 3), dtype=np.float32)


def _set_pair(world, frame, idx_left, idx_right, deg, half_width=0.2):
    """수평면에서 deg 만큼 돌아간 좌우 한 쌍을 심는다."""
    rad = math.radians(deg)
    dx, dz = math.cos(rad) * half_width, math.sin(rad) * half_width
    world[frame, idx_left] = (-dx, 0.0, -dz)
    world[frame, idx_right] = (dx, 0.0, dz)


def test_rotation_between_measures_relative_turn():
    world = _blank_world()
    _set_pair(world, 0, L_SHOULDER, R_SHOULDER, 0.0)
    _set_pair(world, 1, L_SHOULDER, R_SHOULDER, 90.0)
    result = rotation_between(world[0], world[1], L_SHOULDER, R_SHOULDER)
    assert result == pytest.approx(90.0, abs=1e-3)


def test_rotation_between_is_zero_when_no_turn():
    world = _blank_world()
    _set_pair(world, 0, L_SHOULDER, R_SHOULDER, 35.0)
    _set_pair(world, 1, L_SHOULDER, R_SHOULDER, 35.0)
    result = rotation_between(world[0], world[1], L_SHOULDER, R_SHOULDER)
    assert result == pytest.approx(0.0, abs=1e-3)


def test_rotation_between_is_direction_agnostic():
    """좌타·우타에 따라 회전 방향이 반대이므로 크기만 본다."""
    world = _blank_world()
    _set_pair(world, 0, L_SHOULDER, R_SHOULDER, 0.0)
    _set_pair(world, 1, L_SHOULDER, R_SHOULDER, -80.0)
    assert rotation_between(world[0], world[1], L_SHOULDER, R_SHOULDER) == pytest.approx(80.0, abs=1e-3)


def test_rotation_between_wraps_past_half_turn():
    """170도에서 -170도로 간 것은 20도 회전이지 340도가 아니다."""
    world = _blank_world()
    _set_pair(world, 0, L_SHOULDER, R_SHOULDER, 170.0)
    _set_pair(world, 1, L_SHOULDER, R_SHOULDER, -170.0)
    assert rotation_between(world[0], world[1], L_SHOULDER, R_SHOULDER) == pytest.approx(20.0, abs=1e-3)


def test_shoulder_rotation_uses_shoulder_landmarks():
    world = _blank_world(3)
    _set_pair(world, 0, L_SHOULDER, R_SHOULDER, 0.0)
    _set_pair(world, 2, L_SHOULDER, R_SHOULDER, 95.0)
    assert shoulder_rotation(world, addr_i=0, top_i=2) == pytest.approx(95.0, abs=1e-3)


def test_hip_rotation_uses_hip_landmarks():
    world = _blank_world(3)
    _set_pair(world, 0, L_HIP, R_HIP, 0.0)
    _set_pair(world, 2, L_HIP, R_HIP, 48.0)
    assert hip_rotation(world, addr_i=0, top_i=2) == pytest.approx(48.0, abs=1e-3)


def test_x_factor_is_shoulder_minus_hip():
    assert x_factor(95.0, 48.0) == pytest.approx(47.0)


def test_x_factor_can_be_negative_when_hips_outturn_shoulders():
    """비정상 스윙이지만 실제로 나올 수 있다. 0으로 깎지 않는다."""
    assert x_factor(40.0, 55.0) == pytest.approx(-15.0)


def test_rotation_between_returns_nan_for_zero_length_vector():
    """좌우 랜드마크가 겹치면 각도가 정의되지 않는다."""
    world = _blank_world()
    result = rotation_between(world[0], world[1], L_SHOULDER, R_SHOULDER)
    assert math.isnan(result)
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
cd backend && .venv/bin/pytest tests/swing/test_metrics_rotation.py -v
```

Expected: FAIL — `ImportError: cannot import name 'rotation_between'`

- [ ] **Step 3: 구현 추가**

`backend/app/services/swing/metrics.py` 끝에 덧붙인다:

```python
# ── 회전 지표 ──────────────────────────────────────────────────────────────
def _is_degenerate_pair(frame: np.ndarray, idx_left: int, idx_right: int) -> bool:
    """좌우 랜드마크가 사실상 겹쳐 방향을 정의할 수 없는가."""
    v = np.asarray(frame[idx_right], dtype=np.float64) - np.asarray(
        frame[idx_left], dtype=np.float64
    )
    return float(math.hypot(v[0], v[2])) < 1e-9


def rotation_between(
    world_ref: np.ndarray,
    world_target: np.ndarray,
    idx_left: int,
    idx_right: int,
) -> float:
    """기준 프레임 대비 목표 프레임의 수평 회전량(도), 0~180.

    좌타·우타에 따라 부호가 반대이므로 크기만 돌려준다.
    방향을 정의할 수 없으면 NaN.
    """
    if _is_degenerate_pair(world_ref, idx_left, idx_right) or _is_degenerate_pair(
        world_target, idx_left, idx_right
    ):
        return math.nan
    a0 = horizontal_angle(world_ref[idx_left], world_ref[idx_right])
    a1 = horizontal_angle(world_target[idx_left], world_target[idx_right])
    return abs(wrap_deg(a1 - a0))


def shoulder_rotation(world: np.ndarray, addr_i: int, top_i: int) -> float:
    """어드레스 대비 탑에서의 어깨 회전량(도)."""
    return rotation_between(world[addr_i], world[top_i], L_SHOULDER, R_SHOULDER)


def hip_rotation(world: np.ndarray, addr_i: int, top_i: int) -> float:
    """어드레스 대비 탑에서의 힙 회전량(도)."""
    return rotation_between(world[addr_i], world[top_i], L_HIP, R_HIP)


def x_factor(shoulder_deg: float, hip_deg: float) -> float:
    """어깨와 힙 회전의 차이. 골프에서 비거리를 결정하는 핵심 지표.

    힙이 어깨보다 더 돌아간 비정상 스윙에서는 음수가 나온다.
    실제로 일어나는 일이므로 0으로 깎지 않는다.
    """
    return shoulder_deg - hip_deg
```

- [ ] **Step 4: 테스트 통과 확인**

```bash
cd backend && .venv/bin/pytest tests/swing/test_metrics_rotation.py -v
```

Expected: 9 passed

- [ ] **Step 5: 커밋**

```bash
git add backend/app/services/swing/metrics.py backend/tests/swing/test_metrics_rotation.py
git commit -m "feat(swing): compute shoulder rotation, hip rotation and X-factor"
```

---

## Task 4: 자세 지표 — 무릎 굴곡 · 척추 각도

`knee_flex`는 가짜 기본값 `22.0`이 박혀 있던 지표다. `spine_angle`은 기존 2D 계산을 3D로 교체한다.

**MediaPipe world 좌표계 주의**: y축은 **아래가 양수**다(이미지 좌표와 같은 방향). 어깨는 힙보다 위에 있으므로 `shoulder.y - hip.y`는 **음수**다. 따라서 기울기 계산에 `abs()`를 쓴다. 이 가정은 Task 9에서 실제 영상으로 검증한다.

**Files:**
- Modify: `backend/app/services/swing/metrics.py`
- Test: `backend/tests/swing/test_metrics_posture.py`

**Interfaces:**
- Consumes: Task 2의 `angle_at`, 랜드마크 상수
- Produces:
  - `knee_flex(world, addr_i) -> float` — 좌우 평균 굴곡각(도). 곧게 펴면 0
  - `spine_angle(world, addr_i) -> float` — 수직 대비 전방 기울기(도). 똑바로 서면 0

- [ ] **Step 1: 실패하는 테스트 작성**

`backend/tests/swing/test_metrics_posture.py`:

```python
import math

import numpy as np
import pytest

from app.services.swing.metrics import (
    L_ANKLE,
    L_HIP,
    L_KNEE,
    L_SHOULDER,
    R_ANKLE,
    R_HIP,
    R_KNEE,
    R_SHOULDER,
    knee_flex,
    spine_angle,
)


def _blank_world(frames: int = 1) -> np.ndarray:
    return np.zeros((frames, 33, 3), dtype=np.float32)


def _straight_leg(world, frame, hip_i, knee_i, ankle_i, x=0.1):
    """y는 아래가 양수. 곧게 편 다리."""
    world[frame, hip_i] = (x, 0.0, 0.0)
    world[frame, knee_i] = (x, 0.45, 0.0)
    world[frame, ankle_i] = (x, 0.90, 0.0)


def _bent_leg(world, frame, hip_i, knee_i, ankle_i, x=0.1, forward=0.2):
    """무릎만 앞(z 음수)으로 내민 다리."""
    world[frame, hip_i] = (x, 0.0, 0.0)
    world[frame, knee_i] = (x, 0.45, -forward)
    world[frame, ankle_i] = (x, 0.90, 0.0)


def test_knee_flex_is_zero_for_straight_legs():
    world = _blank_world()
    _straight_leg(world, 0, L_HIP, L_KNEE, L_ANKLE, x=-0.1)
    _straight_leg(world, 0, R_HIP, R_KNEE, R_ANKLE, x=0.1)
    assert knee_flex(world, addr_i=0) == pytest.approx(0.0, abs=1e-3)


def test_knee_flex_is_positive_when_knees_bend():
    world = _blank_world()
    _bent_leg(world, 0, L_HIP, L_KNEE, L_ANKLE, x=-0.1)
    _bent_leg(world, 0, R_HIP, R_KNEE, R_ANKLE, x=0.1)
    result = knee_flex(world, addr_i=0)
    assert result > 0.0
    # 무릎이 0.2m 앞으로, 상하 각 0.45m → 좌우 대칭이므로 한쪽 계산과 같다
    expected = 180.0 - math.degrees(
        math.acos(
            np.dot([0.0, -0.45, 0.2], [0.0, 0.45, 0.2])
            / (math.hypot(0.45, 0.2) ** 2)
        )
    )
    assert result == pytest.approx(expected, abs=1e-3)


def test_knee_flex_averages_left_and_right():
    """한쪽만 굽으면 평균이므로 양쪽 다 굽었을 때의 절반이다."""
    world = _blank_world()
    _straight_leg(world, 0, L_HIP, L_KNEE, L_ANKLE, x=-0.1)
    _bent_leg(world, 0, R_HIP, R_KNEE, R_ANKLE, x=0.1)
    both = _blank_world()
    _bent_leg(both, 0, L_HIP, L_KNEE, L_ANKLE, x=-0.1)
    _bent_leg(both, 0, R_HIP, R_KNEE, R_ANKLE, x=0.1)
    assert knee_flex(world, 0) == pytest.approx(knee_flex(both, 0) / 2.0, abs=1e-3)


def test_knee_flex_is_nan_when_landmarks_collapse():
    world = _blank_world()  # 전부 원점 → 벡터 길이 0
    assert math.isnan(knee_flex(world, addr_i=0))


def test_spine_angle_is_zero_when_upright():
    """어깨가 힙 바로 위에 있으면 기울기 0."""
    world = _blank_world()
    world[0, L_HIP] = (-0.15, 0.0, 0.0)
    world[0, R_HIP] = (0.15, 0.0, 0.0)
    world[0, L_SHOULDER] = (-0.2, -0.5, 0.0)
    world[0, R_SHOULDER] = (0.2, -0.5, 0.0)
    assert spine_angle(world, addr_i=0) == pytest.approx(0.0, abs=1e-3)


def test_spine_angle_is_forty_five_when_bent_equally():
    """수직 0.5m, 전방 0.5m 기울면 45도."""
    world = _blank_world()
    world[0, L_HIP] = (-0.15, 0.0, 0.0)
    world[0, R_HIP] = (0.15, 0.0, 0.0)
    world[0, L_SHOULDER] = (-0.2, -0.5, -0.5)
    world[0, R_SHOULDER] = (0.2, -0.5, -0.5)
    assert spine_angle(world, addr_i=0) == pytest.approx(45.0, abs=1e-3)


def test_spine_angle_is_nan_when_shoulders_and_hips_coincide():
    world = _blank_world()
    assert math.isnan(spine_angle(world, addr_i=0))
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
cd backend && .venv/bin/pytest tests/swing/test_metrics_posture.py -v
```

Expected: FAIL — `ImportError: cannot import name 'knee_flex'`

- [ ] **Step 3: 구현 추가**

`backend/app/services/swing/metrics.py` 끝에 덧붙인다:

```python
# ── 자세 지표 ──────────────────────────────────────────────────────────────
def knee_flex(world: np.ndarray, addr_i: int) -> float:
    """어드레스에서의 무릎 굴곡각(도), 좌우 평균. 곧게 펴면 0.

    힙-무릎-발목 사이각의 여각이다. 한쪽이라도 계산 불가면 NaN.
    """
    frame = world[addr_i]
    left = angle_at(frame[L_HIP], frame[L_KNEE], frame[L_ANKLE])
    right = angle_at(frame[R_HIP], frame[R_KNEE], frame[R_ANKLE])
    if math.isnan(left) or math.isnan(right):
        return math.nan
    return ((180.0 - left) + (180.0 - right)) / 2.0


def spine_angle(world: np.ndarray, addr_i: int) -> float:
    """어드레스에서 척추가 수직 대비 앞으로 기운 각도(도).

    MediaPipe world 좌표는 y축 아래가 양수라 어깨는 힙보다 y가 작다.
    부호에 의존하지 않도록 수직 성분은 절댓값으로 쓴다.
    """
    frame = world[addr_i]
    shoulder_c = (
        np.asarray(frame[L_SHOULDER], dtype=np.float64)
        + np.asarray(frame[R_SHOULDER], dtype=np.float64)
    ) / 2.0
    hip_c = (
        np.asarray(frame[L_HIP], dtype=np.float64)
        + np.asarray(frame[R_HIP], dtype=np.float64)
    ) / 2.0
    v = shoulder_c - hip_c
    if float(np.linalg.norm(v)) < 1e-9:
        return math.nan
    horizontal = math.hypot(float(v[0]), float(v[2]))
    return math.degrees(math.atan2(horizontal, abs(float(v[1]))))
```

- [ ] **Step 4: 테스트 통과 확인**

```bash
cd backend && .venv/bin/pytest tests/swing/test_metrics_posture.py -v
```

Expected: 7 passed

- [ ] **Step 5: 커밋**

```bash
git add backend/app/services/swing/metrics.py backend/tests/swing/test_metrics_posture.py
git commit -m "feat(swing): compute knee flex and 3D spine angle"
```

---

## Task 5: 2D 픽셀 지표 — 헤드 무브먼트 · 체중 이동

이 둘만 픽셀 좌표를 쓴다. world 좌표는 힙 중심이 원점이라 **몸 전체의 공간 이동이 상쇄되므로** 계산이 불가능하다 (스펙 §3.1).

- `head_movement`: 지금 `1.7`로 **하드코딩**되어 있다.
- `weight_shift`: 지금 `weight_transfer`라는 이름으로 기본값 `55.0`이 들어간다. 이름과 정의를 모두 바꾼다.

**Files:**
- Modify: `backend/app/services/swing/metrics.py`
- Test: `backend/tests/swing/test_metrics_pixel.py`

**Interfaces:**
- Consumes: Task 2의 랜드마크 상수, `SHOULDER_WIDTH_CM`
- Produces:
  - `head_movement_cm(xy_px, addr_i, impact_i) -> float`
  - `weight_shift_pct(xy_px, addr_i, impact_i) -> float`

- [ ] **Step 1: 실패하는 테스트 작성**

`backend/tests/swing/test_metrics_pixel.py`:

```python
import math

import numpy as np
import pytest

from app.services.swing.metrics import (
    L_ANKLE,
    L_HIP,
    L_SHOULDER,
    NOSE,
    R_ANKLE,
    R_HIP,
    R_SHOULDER,
    head_movement_cm,
    weight_shift_pct,
)


def _blank_px(frames: int) -> np.ndarray:
    return np.zeros((frames, 33, 2), dtype=np.float32)


def _set_shoulders(xy, frame, width_px=200.0, y=300.0):
    xy[frame, L_SHOULDER] = (500.0 - width_px / 2, y)
    xy[frame, R_SHOULDER] = (500.0 + width_px / 2, y)


def test_head_movement_is_zero_when_head_is_still():
    xy = _blank_px(5)
    for f in range(5):
        _set_shoulders(xy, f)
        xy[f, NOSE] = (500.0, 250.0)
    assert head_movement_cm(xy, addr_i=0, impact_i=4) == pytest.approx(0.0, abs=1e-4)


def test_head_movement_converts_pixels_to_cm_via_shoulder_width():
    """어깨 너비 200px = 40cm 이므로 100px 이동은 20cm."""
    xy = _blank_px(3)
    for f in range(3):
        _set_shoulders(xy, f, width_px=200.0)
    xy[0, NOSE] = (500.0, 250.0)
    xy[1, NOSE] = (550.0, 250.0)
    xy[2, NOSE] = (600.0, 250.0)
    assert head_movement_cm(xy, addr_i=0, impact_i=2) == pytest.approx(20.0, abs=1e-3)


def test_head_movement_takes_max_not_final_displacement():
    """중간에 크게 흔들렸다 돌아오면 그 최대치를 잡아야 한다."""
    xy = _blank_px(3)
    for f in range(3):
        _set_shoulders(xy, f, width_px=200.0)
    xy[0, NOSE] = (500.0, 250.0)
    xy[1, NOSE] = (650.0, 250.0)  # 150px = 30cm
    xy[2, NOSE] = (500.0, 250.0)  # 제자리 복귀
    assert head_movement_cm(xy, addr_i=0, impact_i=2) == pytest.approx(30.0, abs=1e-3)


def test_head_movement_measures_diagonal_displacement():
    """3-4-5 삼각형: 어깨 200px=40cm 기준 100px 이동 → 20cm."""
    xy = _blank_px(2)
    for f in range(2):
        _set_shoulders(xy, f, width_px=200.0)
    xy[0, NOSE] = (500.0, 250.0)
    xy[1, NOSE] = (560.0, 330.0)  # dx=60, dy=80 → 100px
    assert head_movement_cm(xy, addr_i=0, impact_i=1) == pytest.approx(20.0, abs=1e-3)


def test_head_movement_is_nan_when_shoulders_overlap():
    """기준자가 없으면 cm 환산이 불가능하다."""
    xy = _blank_px(2)
    xy[:, NOSE] = (500.0, 250.0)
    assert math.isnan(head_movement_cm(xy, addr_i=0, impact_i=1))


def test_weight_shift_is_zero_when_pelvis_does_not_move():
    xy = _blank_px(2)
    for f in range(2):
        xy[f, L_HIP] = (480.0, 500.0)
        xy[f, R_HIP] = (520.0, 500.0)
        xy[f, L_ANKLE] = (450.0, 900.0)
        xy[f, R_ANKLE] = (550.0, 900.0)
    assert weight_shift_pct(xy, addr_i=0, impact_i=1) == pytest.approx(0.0, abs=1e-4)


def test_weight_shift_is_percentage_of_stance_width():
    """스탠스 100px, 골반이 20px 이동 → 20%."""
    xy = _blank_px(2)
    for f in range(2):
        xy[f, L_ANKLE] = (450.0, 900.0)
        xy[f, R_ANKLE] = (550.0, 900.0)
    xy[0, L_HIP] = (480.0, 500.0)
    xy[0, R_HIP] = (520.0, 500.0)
    xy[1, L_HIP] = (500.0, 500.0)
    xy[1, R_HIP] = (540.0, 500.0)
    assert weight_shift_pct(xy, addr_i=0, impact_i=1) == pytest.approx(20.0, abs=1e-3)


def test_weight_shift_ignores_direction():
    """좌타·우타에 따라 이동 방향이 반대다."""
    xy = _blank_px(2)
    for f in range(2):
        xy[f, L_ANKLE] = (450.0, 900.0)
        xy[f, R_ANKLE] = (550.0, 900.0)
    xy[0, L_HIP] = (500.0, 500.0)
    xy[0, R_HIP] = (540.0, 500.0)
    xy[1, L_HIP] = (480.0, 500.0)
    xy[1, R_HIP] = (520.0, 500.0)
    assert weight_shift_pct(xy, addr_i=0, impact_i=1) == pytest.approx(20.0, abs=1e-3)


def test_weight_shift_is_nan_when_stance_width_is_zero():
    xy = _blank_px(2)
    xy[:, L_HIP] = (500.0, 500.0)
    xy[:, R_HIP] = (540.0, 500.0)
    assert math.isnan(weight_shift_pct(xy, addr_i=0, impact_i=1))
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
cd backend && .venv/bin/pytest tests/swing/test_metrics_pixel.py -v
```

Expected: FAIL — `ImportError: cannot import name 'head_movement_cm'`

- [ ] **Step 3: 구현 추가**

`backend/app/services/swing/metrics.py` 끝에 덧붙인다:

```python
# ── 2D 픽셀 지표 ──────────────────────────────────────────────────────────
# world 좌표는 힙 중심이 원점이라 몸 전체의 공간 이동이 상쇄된다.
# 아래 두 지표는 그래서 픽셀 좌표를 쓴다.
def head_movement_cm(xy_px: np.ndarray, addr_i: int, impact_i: int) -> float:
    """어드레스~임팩트 구간에서 머리가 움직인 최대 거리(cm).

    어드레스 프레임의 어깨 너비 픽셀을 SHOULDER_WIDTH_CM 에 대응시켜 환산한다.
    기준자를 만들 수 없으면 NaN.
    """
    addr = xy_px[addr_i]
    shoulder_px = float(
        np.linalg.norm(
            np.asarray(addr[R_SHOULDER], dtype=np.float64)
            - np.asarray(addr[L_SHOULDER], dtype=np.float64)
        )
    )
    if shoulder_px < 1e-6:
        return math.nan

    lo, hi = min(addr_i, impact_i), max(addr_i, impact_i)
    segment = np.asarray(xy_px[lo : hi + 1, NOSE], dtype=np.float64)
    displacement = float(np.linalg.norm(segment - segment[0], axis=1).max())
    return displacement * (SHOULDER_WIDTH_CM / shoulder_px)


def weight_shift_pct(xy_px: np.ndarray, addr_i: int, impact_i: int) -> float:
    """골반 중심의 좌우 이동량을 스탠스 폭 대비 %로 나타낸 대리 지표.

    영상만으로 실제 체중 배분은 측정할 수 없다. 이것은 추정치이며
    화면에도 그렇게 표시해야 한다 (스펙 §3.3).
    스탠스 폭이 0이면 NaN.
    """
    addr = xy_px[addr_i]
    impact = xy_px[impact_i]
    stance_px = abs(float(addr[L_ANKLE][0]) - float(addr[R_ANKLE][0]))
    if stance_px < 1e-6:
        return math.nan

    pelvis_addr = (float(addr[L_HIP][0]) + float(addr[R_HIP][0])) / 2.0
    pelvis_impact = (float(impact[L_HIP][0]) + float(impact[R_HIP][0])) / 2.0
    return abs(pelvis_impact - pelvis_addr) / stance_px * 100.0
```

- [ ] **Step 4: 테스트 통과 확인**

```bash
cd backend && .venv/bin/pytest tests/swing/test_metrics_pixel.py -v
```

Expected: 9 passed

- [ ] **Step 5: 커밋**

```bash
git add backend/app/services/swing/metrics.py backend/tests/swing/test_metrics_pixel.py
git commit -m "feat(swing): compute head movement in cm and weight shift proxy"
```

---

## Task 6: 템포 비율

기존 구현은 `valid[]` 배열 인덱스로 계산해 프레임 스킵 간격이 섞여 있었다. **실제 초 단위**로 바꾼다.

**Files:**
- Modify: `backend/app/services/swing/metrics.py`
- Test: `backend/tests/swing/test_metrics_tempo.py`

**Interfaces:**
- Consumes: 없음
- Produces: `tempo_ratio(frame_indices, fps, addr_i, top_i, impact_i) -> float`

- [ ] **Step 1: 실패하는 테스트 작성**

`backend/tests/swing/test_metrics_tempo.py`:

```python
import math

import numpy as np
import pytest

from app.services.swing.metrics import tempo_ratio


def test_tempo_ratio_uses_real_seconds_not_array_index():
    """프레임을 건너뛰며 샘플링해도 실제 시각으로 계산해야 한다.

    원본 프레임 0, 30, 60, 90 을 60fps로 찍었다면
    백스윙 = (60-0)/60 = 1.0초, 다운스윙 = (90-60)/60 = 0.5초 → 2.0
    """
    frame_indices = np.array([0, 30, 60, 90], dtype=np.int32)
    result = tempo_ratio(frame_indices, fps=60.0, addr_i=0, top_i=2, impact_i=3)
    assert result == pytest.approx(2.0, abs=1e-6)


def test_tempo_ratio_three_to_one():
    """이상적인 3:1 템포."""
    frame_indices = np.array([0, 90, 120], dtype=np.int32)
    assert tempo_ratio(frame_indices, fps=30.0, addr_i=0, top_i=1, impact_i=2) == pytest.approx(3.0)


def test_tempo_ratio_is_nan_when_downswing_has_no_duration():
    """탑과 임팩트가 같은 프레임이면 비율이 정의되지 않는다. 3.0을 지어내지 않는다."""
    frame_indices = np.array([0, 60, 60], dtype=np.int32)
    assert math.isnan(tempo_ratio(frame_indices, fps=60.0, addr_i=0, top_i=1, impact_i=2))


def test_tempo_ratio_is_nan_when_backswing_has_no_duration():
    frame_indices = np.array([60, 60, 90], dtype=np.int32)
    assert math.isnan(tempo_ratio(frame_indices, fps=60.0, addr_i=0, top_i=1, impact_i=2))


def test_tempo_ratio_is_nan_when_fps_is_invalid():
    frame_indices = np.array([0, 60, 90], dtype=np.int32)
    assert math.isnan(tempo_ratio(frame_indices, fps=0.0, addr_i=0, top_i=1, impact_i=2))
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
cd backend && .venv/bin/pytest tests/swing/test_metrics_tempo.py -v
```

Expected: FAIL — `ImportError: cannot import name 'tempo_ratio'`

- [ ] **Step 3: 구현 추가**

`backend/app/services/swing/metrics.py` 끝에 덧붙인다:

```python
# ── 템포 ──────────────────────────────────────────────────────────────────
def tempo_ratio(
    frame_indices: np.ndarray,
    fps: float,
    addr_i: int,
    top_i: int,
    impact_i: int,
) -> float:
    """백스윙 시간 ÷ 다운스윙 시간.

    배열 인덱스가 아니라 원본 프레임 번호와 fps로 실제 초를 구한다.
    프레임을 건너뛰며 샘플링하므로 인덱스 차이는 시간에 비례하지 않는다.
    어느 구간이든 길이가 0이면 NaN.
    """
    if fps <= 0.0:
        return math.nan
    t_addr = float(frame_indices[addr_i]) / fps
    t_top = float(frame_indices[top_i]) / fps
    t_impact = float(frame_indices[impact_i]) / fps

    backswing = t_top - t_addr
    downswing = t_impact - t_top
    if backswing <= 0.0 or downswing <= 0.0:
        return math.nan
    return backswing / downswing
```

- [ ] **Step 4: 테스트 통과 확인**

```bash
cd backend && .venv/bin/pytest tests/swing/test_metrics_tempo.py -v
```

Expected: 5 passed

- [ ] **Step 5: 커밋**

```bash
git add backend/app/services/swing/metrics.py backend/tests/swing/test_metrics_tempo.py
git commit -m "feat(swing): compute tempo ratio from real elapsed seconds"
```

---

## Task 7: 통합 — 촬영 각도 게이팅과 `compute_metrics`

**이 계획의 핵심 Task다.** 여기서 "가짜 기본값 금지" 원칙이 코드로 고정된다.

각도별 계산 가능 지표 (스펙 §9.5):

| 지표 | `down_the_line` | `face_on` |
|---|---|---|
| `spine_angle` | ✓ | ✓ |
| `knee_flex` | ✓ | ✓ |
| `tempo_ratio` | ✓ | ✓ |
| `shoulder_rotation` | ✓ | ✗ |
| `hip_rotation` | ✓ | ✗ |
| `x_factor` | ✓ | ✗ |
| `head_movement` | ✗ | ✓ |
| `weight_shift` | ✗ | ✓ |

**Files:**
- Modify: `backend/app/services/swing/metrics.py`
- Test: `backend/tests/swing/test_metrics_compute.py`

**Interfaces:**
- Consumes: Task 1의 `MetricValue`·`PoseSequence`, Task 3~6의 모든 계산 함수
- Produces:
  - `METRIC_UNITS: dict[str, str]` — 지표명 → 단위
  - `METRIC_ANGLES: dict[str, frozenset[str]]` — 지표명 → 계산 가능한 촬영 각도
  - `CameraAngle = Literal["down_the_line", "face_on"]`
  - `compute_metrics(seq: PoseSequence, phases: dict[str, int], camera_angle: str) -> dict[str, MetricValue]`
  - `metrics_to_json(metrics: dict[str, MetricValue]) -> dict` — DB `JSON` 컬럼 직렬화용

- [ ] **Step 1: 실패하는 테스트 작성**

`backend/tests/swing/test_metrics_compute.py`:

```python
import numpy as np
import pytest

from app.services.swing.metrics import (
    METRIC_ANGLES,
    METRIC_UNITS,
    L_ANKLE,
    L_HIP,
    L_KNEE,
    L_SHOULDER,
    NOSE,
    R_ANKLE,
    R_HIP,
    R_KNEE,
    R_SHOULDER,
    compute_metrics,
    metrics_to_json,
)
from app.services.swing.types import PoseSequence

ALL_METRICS = {
    "spine_angle", "knee_flex", "tempo_ratio", "shoulder_rotation",
    "hip_rotation", "x_factor", "head_movement", "weight_shift",
}


def _realistic_sequence(frames: int = 7) -> PoseSequence:
    """어드레스(0) → 탑(2) → 임팩트(4) 를 가진 최소한의 그럴듯한 스윙."""
    world = np.zeros((frames, 33, 3), dtype=np.float32)
    xy = np.zeros((frames, 33, 2), dtype=np.float32)
    for f in range(frames):
        turn = 0.0 if f < 2 else 0.9  # 탑에서 어깨가 돌아간다
        world[f, L_SHOULDER] = (-0.2, -0.5, -turn * 0.2)
        world[f, R_SHOULDER] = (0.2, -0.5, turn * 0.2)
        world[f, L_HIP] = (-0.15, 0.0, 0.0)
        world[f, R_HIP] = (0.15, 0.0, 0.0)
        world[f, L_KNEE] = (-0.15, 0.45, -0.1)
        world[f, R_KNEE] = (0.15, 0.45, -0.1)
        world[f, L_ANKLE] = (-0.15, 0.90, 0.0)
        world[f, R_ANKLE] = (0.15, 0.90, 0.0)

        xy[f, L_SHOULDER] = (400.0, 300.0)
        xy[f, R_SHOULDER] = (600.0, 300.0)
        xy[f, L_HIP] = (480.0 + f * 2, 500.0)
        xy[f, R_HIP] = (520.0 + f * 2, 500.0)
        xy[f, L_ANKLE] = (450.0, 900.0)
        xy[f, R_ANKLE] = (550.0, 900.0)
        xy[f, NOSE] = (500.0 + f * 3, 250.0)

    return PoseSequence(
        world=world,
        xy_px=xy,
        visibility=np.full((frames, 33), 0.9, dtype=np.float32),
        frame_indices=np.arange(frames, dtype=np.int32) * 15,
        fps=60.0,
        resolution_wh=(1000, 1000),
    )


PHASES = {
    "address": 0, "takeaway": 1, "top": 2, "downswing": 3,
    "impact": 4, "followthrough": 5, "finish": 6,
}


def test_metric_units_cover_all_eight_metrics():
    assert set(METRIC_UNITS) == ALL_METRICS


def test_metric_angles_cover_all_eight_metrics():
    assert set(METRIC_ANGLES) == ALL_METRICS


def test_rotation_metrics_only_from_down_the_line():
    for name in ("shoulder_rotation", "hip_rotation", "x_factor"):
        assert METRIC_ANGLES[name] == frozenset({"down_the_line"})


def test_pixel_metrics_only_from_face_on():
    for name in ("head_movement", "weight_shift"):
        assert METRIC_ANGLES[name] == frozenset({"face_on"})


def test_compute_returns_all_eight_metrics_regardless_of_angle():
    """각도와 무관하게 키는 항상 8개. 없는 것은 measurable=False 로 표현한다."""
    seq = _realistic_sequence()
    for angle in ("down_the_line", "face_on"):
        result = compute_metrics(seq, PHASES, angle)
        assert set(result) == ALL_METRICS


def test_face_on_marks_rotation_metrics_unmeasurable():
    seq = _realistic_sequence()
    result = compute_metrics(seq, PHASES, "face_on")
    for name in ("shoulder_rotation", "hip_rotation", "x_factor"):
        assert result[name].measurable is False
        assert result[name].value is None


def test_down_the_line_measures_rotation():
    seq = _realistic_sequence()
    result = compute_metrics(seq, PHASES, "down_the_line")
    assert result["shoulder_rotation"].measurable is True
    assert result["shoulder_rotation"].value is not None
    assert result["shoulder_rotation"].value > 0.0


def test_down_the_line_marks_pixel_metrics_unmeasurable():
    seq = _realistic_sequence()
    result = compute_metrics(seq, PHASES, "down_the_line")
    for name in ("head_movement", "weight_shift"):
        assert result[name].measurable is False


def test_x_factor_equals_shoulder_minus_hip():
    seq = _realistic_sequence()
    r = compute_metrics(seq, PHASES, "down_the_line")
    assert r["x_factor"].value == pytest.approx(
        r["shoulder_rotation"].value - r["hip_rotation"].value, abs=1e-6
    )


def test_nan_result_becomes_failed_not_a_default_number():
    """계산이 NaN이면 값을 지어내지 않고 failed 로 남긴다."""
    seq = _realistic_sequence()
    broken = PHASES | {"top": 2, "impact": 2}  # 다운스윙 길이 0 → tempo NaN
    result = compute_metrics(seq, broken, "face_on")
    assert result["tempo_ratio"].value is None
    assert result["tempo_ratio"].measurable is True  # 각도 탓이 아니라 계산 실패


def test_confidence_reflects_lowest_landmark_visibility():
    seq = _realistic_sequence()
    seq.visibility[PHASES["address"], L_KNEE] = 0.11
    result = compute_metrics(seq, PHASES, "down_the_line")
    assert result["knee_flex"].confidence == pytest.approx(0.11, abs=1e-6)


def test_units_are_attached_to_results():
    seq = _realistic_sequence()
    r = compute_metrics(seq, PHASES, "face_on")
    assert r["head_movement"].unit == "cm"
    assert r["weight_shift"].unit == "%"
    assert r["spine_angle"].unit == "°"


def test_metrics_to_json_is_serialisable_and_keeps_none():
    import json

    seq = _realistic_sequence()
    payload = metrics_to_json(compute_metrics(seq, PHASES, "face_on"))
    encoded = json.dumps(payload)  # 예외가 나면 실패
    assert json.loads(encoded)["shoulder_rotation"]["value"] is None
    assert json.loads(encoded)["shoulder_rotation"]["measurable"] is False
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
cd backend && .venv/bin/pytest tests/swing/test_metrics_compute.py -v
```

Expected: FAIL — `ImportError: cannot import name 'METRIC_UNITS'`

- [ ] **Step 3: 구현 추가**

`backend/app/services/swing/metrics.py`의 import 구역에 추가:

```python
from typing import Literal

from app.services.swing.types import MetricValue, PoseSequence
```

그리고 파일 끝에 덧붙인다:

```python
# ── 촬영 각도별 계산 가능 지표 ─────────────────────────────────────────────
CameraAngle = Literal["down_the_line", "face_on"]

_BOTH = frozenset({"down_the_line", "face_on"})
_DTL = frozenset({"down_the_line"})
_FACE = frozenset({"face_on"})

METRIC_ANGLES: dict[str, frozenset[str]] = {
    "spine_angle": _BOTH,
    "knee_flex": _BOTH,
    "tempo_ratio": _BOTH,
    # 수평 회전은 깊이(z) 성분이 필요해 정면에서는 신뢰할 수 없다
    "shoulder_rotation": _DTL,
    "hip_rotation": _DTL,
    "x_factor": _DTL,
    # 좌우 이동은 정면에서만 화면에 드러난다
    "head_movement": _FACE,
    "weight_shift": _FACE,
}

METRIC_UNITS: dict[str, str] = {
    "spine_angle": "°",
    "knee_flex": "°",
    "tempo_ratio": ":1",
    "shoulder_rotation": "°",
    "hip_rotation": "°",
    "x_factor": "°",
    "head_movement": "cm",
    "weight_shift": "%",
}

# 각 지표가 어느 랜드마크를 쓰는지 — 신뢰도 계산에 쓴다
_METRIC_LANDMARKS: dict[str, tuple[int, ...]] = {
    "spine_angle": (L_SHOULDER, R_SHOULDER, L_HIP, R_HIP),
    "knee_flex": (L_HIP, R_HIP, L_KNEE, R_KNEE, L_ANKLE, R_ANKLE),
    "tempo_ratio": (),
    "shoulder_rotation": (L_SHOULDER, R_SHOULDER),
    "hip_rotation": (L_HIP, R_HIP),
    "x_factor": (L_SHOULDER, R_SHOULDER, L_HIP, R_HIP),
    "head_movement": (NOSE, L_SHOULDER, R_SHOULDER),
    "weight_shift": (L_HIP, R_HIP, L_ANKLE, R_ANKLE),
}

# 각 지표의 신뢰도를 어느 단계 프레임에서 잴 것인가
_METRIC_PHASES: dict[str, tuple[str, ...]] = {
    "spine_angle": ("address",),
    "knee_flex": ("address",),
    "tempo_ratio": ("address", "top", "impact"),
    "shoulder_rotation": ("address", "top"),
    "hip_rotation": ("address", "top"),
    "x_factor": ("address", "top"),
    "head_movement": ("address", "impact"),
    "weight_shift": ("address", "impact"),
}


def _confidence_for(
    name: str, seq: PoseSequence, phases: dict[str, int]
) -> float:
    """해당 지표가 쓰는 랜드마크들의 visibility 최솟값.

    랜드마크를 쓰지 않는 지표(tempo_ratio)는 1.0으로 둔다.
    """
    landmarks = _METRIC_LANDMARKS[name]
    if not landmarks:
        return 1.0
    values = [
        float(seq.visibility[phases[phase], lm])
        for phase in _METRIC_PHASES[name]
        if phase in phases
        for lm in landmarks
    ]
    return min(values) if values else 0.0


def compute_metrics(
    seq: PoseSequence,
    phases: dict[str, int],
    camera_angle: str,
) -> dict[str, MetricValue]:
    """포즈 시퀀스에서 지표 8개를 계산한다.

    반환 키는 촬영 각도와 무관하게 항상 8개다.
    계산할 수 없는 경우를 두 가지로 구분해 표현한다.
      - 촬영 각도상 불가         → MetricValue.unmeasurable
      - 각도는 맞지만 계산 실패  → MetricValue.failed

    어느 경우에도 숫자를 지어내지 않는다 (스펙 §3.4).
    """
    addr_i = phases["address"]
    top_i = phases["top"]
    impact_i = phases["impact"]

    def allowed(name: str) -> bool:
        return camera_angle in METRIC_ANGLES[name]

    raw: dict[str, float] = {}
    if allowed("shoulder_rotation"):
        raw["shoulder_rotation"] = shoulder_rotation(seq.world, addr_i, top_i)
    if allowed("hip_rotation"):
        raw["hip_rotation"] = hip_rotation(seq.world, addr_i, top_i)
    if allowed("x_factor"):
        s = raw.get("shoulder_rotation", math.nan)
        h = raw.get("hip_rotation", math.nan)
        raw["x_factor"] = (
            math.nan if math.isnan(s) or math.isnan(h) else x_factor(s, h)
        )
    if allowed("knee_flex"):
        raw["knee_flex"] = knee_flex(seq.world, addr_i)
    if allowed("spine_angle"):
        raw["spine_angle"] = spine_angle(seq.world, addr_i)
    if allowed("head_movement"):
        raw["head_movement"] = head_movement_cm(seq.xy_px, addr_i, impact_i)
    if allowed("weight_shift"):
        raw["weight_shift"] = weight_shift_pct(seq.xy_px, addr_i, impact_i)
    if allowed("tempo_ratio"):
        raw["tempo_ratio"] = tempo_ratio(
            seq.frame_indices, seq.fps, addr_i, top_i, impact_i
        )

    result: dict[str, MetricValue] = {}
    for name, unit in METRIC_UNITS.items():
        if not allowed(name):
            result[name] = MetricValue.unmeasurable(unit)
            continue
        value = raw.get(name, math.nan)
        if math.isnan(value) or math.isinf(value):
            result[name] = MetricValue.failed(unit)
            continue
        result[name] = MetricValue(
            value=round(float(value), 2),
            confidence=round(_confidence_for(name, seq, phases), 3),
            unit=unit,
            measurable=True,
        )
    return result


def metrics_to_json(metrics: dict[str, MetricValue]) -> dict:
    """DB의 JSON 컬럼과 API 응답에 쓸 직렬화 형태.

    value 가 None 인 것도 그대로 담는다. 키를 빼면 소비하는 쪽에서
    다시 기본값을 채우려는 유혹이 생긴다.
    """
    return {
        name: {
            "value": m.value,
            "confidence": m.confidence,
            "unit": m.unit,
            "measurable": m.measurable,
        }
        for name, m in metrics.items()
    }
```

- [ ] **Step 4: 테스트 통과 확인**

```bash
cd backend && .venv/bin/pytest tests/swing/ -v
```

Expected: 전체 통과 (Task 1~7 누적 48개)

- [ ] **Step 5: `metrics.py`가 순수한지 확인**

```bash
cd backend && grep -nE "^(import|from) " app/services/swing/metrics.py
```

Expected: `math`, `numpy`, `typing`, `app.services.swing.types` 만 나온다. `cv2`·`mediapipe`·`supervision`·`sqlalchemy`가 있으면 Global Constraints 위반이므로 걷어낸다.

- [ ] **Step 6: 커밋**

```bash
git add backend/app/services/swing/metrics.py backend/tests/swing/test_metrics_compute.py
git commit -m "feat(swing): gate metrics by camera angle and forbid fake defaults"
```

---

## Task 8: 포즈 추출 — `pose_world_landmarks` + supervision

기존 `analyze_swing()`은 `result.pose_landmarks`(2D 정규화)만 쓰고 **`pose_world_landmarks`를 한 번도 읽지 않는다.** 여기서 둘 다 뽑아 `PoseSequence`로 만든다.

픽셀 좌표는 `sv.KeyPoints.from_mediapipe()`로 얻는다. 직접 곱해도 되지만, 이 함수를 쓰면 나중에 다른 포즈 모델로 갈아탈 때 지표 코드를 손대지 않아도 된다 (스펙 §2.2).

**Files:**
- Create: `backend/app/services/swing/pose.py`
- Test: `backend/tests/swing/test_pose.py`

**Interfaces:**
- Consumes: Task 1의 `PoseSequence`
- Produces:
  - `get_landmarker() -> PoseLandmarker` — 싱글턴
  - `landmarks_from_result(result, resolution_wh) -> tuple[np.ndarray, np.ndarray, np.ndarray] | None` — `(world(33,3), xy_px(33,2), visibility(33,))`. 포즈 미검출 시 `None`
  - `extract_sequence(video_path, start_frame, end_frame, skip=2, proc_width=640) -> PoseSequence`

- [ ] **Step 1: 실패하는 테스트 작성**

실제 영상 없이 테스트하기 위해 MediaPipe 결과를 흉내 내는 최소 객체를 쓴다.

`backend/tests/swing/test_pose.py`:

```python
import numpy as np
import pytest

from app.services.swing.pose import landmarks_from_result


class _LM:
    """mediapipe 의 NormalizedLandmark / Landmark 를 흉내 낸다."""

    def __init__(self, x, y, z=0.0, visibility=0.9):
        self.x, self.y, self.z, self.visibility = x, y, z, visibility
        self.presence = 1.0


class _Result:
    def __init__(self, pose_landmarks, pose_world_landmarks):
        self.pose_landmarks = pose_landmarks
        self.pose_world_landmarks = pose_world_landmarks


def _make_result(n=33):
    norm = [_LM(0.5, 0.4, 0.0, 0.8) for _ in range(n)]
    world = [_LM(0.1, -0.2, 0.3, 0.8) for _ in range(n)]
    return _Result([norm], [world])


def test_returns_none_when_no_pose_detected():
    assert landmarks_from_result(_Result([], []), (1280, 720)) is None


def test_returns_none_when_world_landmarks_missing():
    """world 좌표가 없으면 지표 6개를 계산할 수 없으므로 실패로 본다."""
    norm = [_LM(0.5, 0.4) for _ in range(33)]
    assert landmarks_from_result(_Result([norm], []), (1280, 720)) is None


def test_world_landmarks_are_kept_in_metres():
    world, _, _ = landmarks_from_result(_make_result(), (1280, 720))
    assert world.shape == (33, 3)
    assert world[0] == pytest.approx([0.1, -0.2, 0.3], abs=1e-5)


def test_pixel_coordinates_are_scaled_by_resolution():
    """0.5 × 1280 = 640,  0.4 × 720 = 288"""
    _, xy_px, _ = landmarks_from_result(_make_result(), (1280, 720))
    assert xy_px.shape == (33, 2)
    assert xy_px[0] == pytest.approx([640.0, 288.0], abs=1e-3)


def test_visibility_is_extracted():
    _, _, vis = landmarks_from_result(_make_result(), (1280, 720))
    assert vis.shape == (33,)
    assert vis[0] == pytest.approx(0.8, abs=1e-5)
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
cd backend && .venv/bin/pytest tests/swing/test_pose.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'app.services.swing.pose'`

- [ ] **Step 3: 구현**

`backend/app/services/swing/pose.py`:

```python
"""
swing/pose.py — 영상에서 프레임별 3D/2D 포즈를 추출한다.

기존 pose_estimator.py 와 달리 pose_world_landmarks(미터 단위 3D)를 함께 뽑는다.
회전 지표는 이것 없이 계산할 수 없다.
"""
from __future__ import annotations

import os

import cv2
import numpy as np
import supervision as sv
from mediapipe import Image, ImageFormat
from mediapipe.tasks.python.core.base_options import BaseOptions
from mediapipe.tasks.python.vision import PoseLandmarker, PoseLandmarkerOptions

from app.services.swing.types import PoseSequence

MODEL_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "pose_landmarker_lite.task"
)

_landmarker: PoseLandmarker | None = None


def get_landmarker() -> PoseLandmarker:
    """PoseLandmarker 싱글턴. 재로딩에 2~3초가 들므로 한 번만 만든다."""
    global _landmarker
    if _landmarker is None:
        _landmarker = PoseLandmarker.create_from_options(
            PoseLandmarkerOptions(
                base_options=BaseOptions(model_asset_path=MODEL_PATH),
                output_segmentation_masks=False,
                min_pose_detection_confidence=0.25,
                min_pose_presence_confidence=0.25,
                min_tracking_confidence=0.25,
            )
        )
    return _landmarker


def landmarks_from_result(
    result, resolution_wh: tuple[int, int]
) -> tuple[np.ndarray, np.ndarray, np.ndarray] | None:
    """MediaPipe 결과에서 (world, xy_px, visibility) 를 뽑는다.

    포즈가 없거나 world 좌표가 빠져 있으면 None.
    world 가 없으면 회전 지표를 낼 수 없으므로 실패로 취급한다.
    """
    if not getattr(result, "pose_landmarks", None):
        return None
    if not getattr(result, "pose_world_landmarks", None):
        return None

    world_lms = result.pose_world_landmarks[0]
    world = np.array(
        [[lm.x, lm.y, lm.z] for lm in world_lms], dtype=np.float32
    )

    # supervision 이 정규화 좌표를 픽셀로 바꿔 준다.
    # 직접 곱하지 않는 이유는 나중에 다른 포즈 모델로 갈아타기 위해서다.
    key_points = sv.KeyPoints.from_mediapipe(result, resolution_wh)
    xy_px = np.asarray(key_points.xy[0], dtype=np.float32)

    visibility = np.array(
        [getattr(lm, "visibility", 0.0) or 0.0 for lm in result.pose_landmarks[0]],
        dtype=np.float32,
    )
    return world, xy_px, visibility


def extract_sequence(
    video_path: str,
    start_frame: int,
    end_frame: int,
    skip: int = 2,
    proc_width: int = 640,
) -> PoseSequence:
    """스윙 구간을 훑어 PoseSequence 를 만든다.

    포즈가 검출되지 않은 프레임은 시퀀스에서 빠진다.
    frame_indices 가 원본 프레임 번호를 보존하므로 템포 계산에 지장이 없다.
    """
    cap = cv2.VideoCapture(video_path)
    landmarker = get_landmarker()

    worlds: list[np.ndarray] = []
    pixels: list[np.ndarray] = []
    visibilities: list[np.ndarray] = []
    indices: list[int] = []

    try:
        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
        current = start_frame
        counter = 0
        width = height = 0

        while current <= end_frame:
            ok, frame = cap.read()
            if not ok:
                break
            counter += 1
            frame_index = current
            current += 1
            if counter % skip != 0:
                continue

            h0, w0 = frame.shape[:2]
            if w0 > proc_width:
                scaled = cv2.resize(frame, (proc_width, int(h0 * proc_width / w0)))
            else:
                scaled = frame
            height, width = scaled.shape[:2]

            mp_image = Image(
                image_format=ImageFormat.SRGB,
                data=cv2.cvtColor(scaled, cv2.COLOR_BGR2RGB),
            )
            extracted = landmarks_from_result(
                landmarker.detect(mp_image), (width, height)
            )
            if extracted is None:
                continue

            world, xy_px, visibility = extracted
            worlds.append(world)
            pixels.append(xy_px)
            visibilities.append(visibility)
            indices.append(frame_index)
    finally:
        cap.release()

    if len(worlds) < 3:
        raise ValueError(
            f"포즈 인식에 실패했습니다 (인식된 프레임 {len(worlds)}개). "
            "측면 또는 정면에서 전신이 보이도록 촬영해 주세요."
        )

    return PoseSequence(
        world=np.stack(worlds),
        xy_px=np.stack(pixels),
        visibility=np.stack(visibilities),
        frame_indices=np.array(indices, dtype=np.int32),
        fps=float(fps),
        resolution_wh=(width, height),
    )
```

- [ ] **Step 4: 테스트 통과 확인**

```bash
cd backend && .venv/bin/pytest tests/swing/test_pose.py -v
```

Expected: 5 passed

- [ ] **Step 5: 모델 파일 경로 확인**

```bash
cd backend && .venv/bin/python -c "from app.services.swing.pose import MODEL_PATH; import os; print(MODEL_PATH, os.path.exists(MODEL_PATH))"
```

Expected: `.../app/services/pose_landmarker_lite.task True`

`False`면 `MODEL_PATH`를 실제 파일 위치에 맞게 고친다.

- [ ] **Step 6: 커밋**

```bash
git add backend/app/services/swing/pose.py backend/tests/swing/test_pose.py
git commit -m "feat(swing): extract 3D world landmarks via MediaPipe and supervision"
```

---

## Task 9: 축 방향 실측 검증 — 스펙 §6 최상위 리스크

**스펙이 "문서만 보고 확정하지 말라"고 못 박은 지점이다.** MediaPipe world 좌표의 y·z 축 방향을 실제 영상으로 확인한다. 부호가 반대면 회전 지표가 통째로 뒤집힌다.

이 Task는 코드를 남기는 것이 아니라 **사실을 확인하고 기록하는 것**이 목적이다.

**Files:**
- Create: `backend/scripts/verify_axes.py`
- Modify: `docs/superpowers/specs/2026-09-16-supervision-metrics-upgrade-design.md` (§6 리스크 표에 검증 결과 기록)

**Interfaces:**
- Consumes: Task 8의 `extract_sequence`
- Produces: 검증된 축 방향 사실. 이후 Task 들이 이 가정 위에서 동작한다.

- [ ] **Step 1: 검증 스크립트 작성**

`backend/scripts/verify_axes.py`:

```python
"""
MediaPipe world landmark 축 방향 검증 (스펙 §6 최상위 리스크).

사용법:
    .venv/bin/python scripts/verify_axes.py <영상경로>

코드가 세운 가정:
  - y축은 아래가 양수  → 어깨의 y 가 힙의 y 보다 작아야 한다
  - 원점은 힙 중심     → 힙 중점의 좌표가 0에 가까워야 한다
  - z축은 깊이         → 몸이 돌면 어깨의 z 차이가 커져야 한다
"""
import sys

import numpy as np

from app.services.swing.metrics import (
    L_HIP, L_SHOULDER, R_HIP, R_SHOULDER, horizontal_angle,
)
from app.services.swing.pose import extract_sequence


def main(video_path: str) -> int:
    seq = extract_sequence(video_path, start_frame=0, end_frame=10_000)
    print(f"인식 프레임 수: {len(seq)}, fps={seq.fps}, 해상도={seq.resolution_wh}")

    first = seq.world[0]
    shoulder_y = (first[L_SHOULDER][1] + first[R_SHOULDER][1]) / 2
    hip_y = (first[L_HIP][1] + first[R_HIP][1]) / 2
    hip_centre = (first[L_HIP] + first[R_HIP]) / 2

    print(f"\n[가정 1] y축 아래가 양수 → 어깨 y < 힙 y")
    print(f"  어깨 y = {shoulder_y:+.4f}, 힙 y = {hip_y:+.4f}")
    print(f"  판정: {'통과' if shoulder_y < hip_y else '실패 — 부호 반전 필요'}")

    print(f"\n[가정 2] 원점은 힙 중심 → 힙 중점 ≈ (0, 0, 0)")
    print(f"  힙 중점 = {np.round(hip_centre, 4)}")
    print(f"  판정: {'통과' if float(np.linalg.norm(hip_centre)) < 0.05 else '실패'}")

    angles = [
        horizontal_angle(f[L_SHOULDER], f[R_SHOULDER]) for f in seq.world
    ]
    span = max(angles) - min(angles)
    print(f"\n[가정 3] z축이 깊이 → 스윙 중 어깨 수평각이 크게 변한다")
    print(f"  최소 {min(angles):+.1f}°, 최대 {max(angles):+.1f}°, 변화폭 {span:.1f}°")
    print(f"  판정: {'통과' if span > 30.0 else '실패 — 축 해석 재검토'}")
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("사용법: python scripts/verify_axes.py <영상경로>")
        raise SystemExit(2)
    raise SystemExit(main(sys.argv[1]))
```

- [ ] **Step 2: 실제 스윙 영상으로 실행**

```bash
cd backend && .venv/bin/python scripts/verify_axes.py <실제_스윙_영상.mp4>
```

측면(down-the-line)에서 찍은 영상을 쓴다. 없으면 진행하지 말고 사람에게 요청한다. **합성 데이터로는 이 검증을 대신할 수 없다.**

- [ ] **Step 3: 결과 판정**

세 가정이 모두 "통과"면 다음 Task로 넘어간다.

**실패한 경우 — 지어내지 말고 고친다:**

| 실패 항목 | 조치 |
|---|---|
| 가정 1 (y축) | `metrics.spine_angle` 의 `abs(v[1])` 는 이미 부호에 안전하다. 주석만 사실에 맞게 고친다 |
| 가정 2 (원점) | world 좌표가 힙 중심이 아니라는 뜻. `head_movement`·`weight_shift` 외의 지표도 2D 검토가 필요하므로 **작업을 멈추고 사람에게 보고한다** |
| 가정 3 (z축) | `horizontal_angle` 의 투영면을 x-y 로 바꿔 재측정한 뒤, 변화폭이 큰 쪽을 채택한다 |

- [ ] **Step 4: 검증 결과를 스펙에 기록**

스펙 §6 리스크 표의 첫 행 "MediaPipe world landmark 축 방향 미확인" 의 대응 칸을 실제 결과로 교체한다. 예:

```
| ~~MediaPipe world landmark 축 방향 미확인~~ **검증 완료 (YYYY-MM-DD)** | — | y축 아래 양수·원점 힙 중심·z축 깊이 확인. `scripts/verify_axes.py` 로 재현 가능 |
```

- [ ] **Step 5: 커밋**

```bash
git add backend/scripts/verify_axes.py docs/superpowers/specs/
git commit -m "test(swing): verify MediaPipe world landmark axis orientation"
```

---

## Task 10: 단계 탐지 이관

기존 `motion_mag` 휴리스틱을 **알고리즘 변경 없이** `phases.py`로 옮긴다 (스펙 §1 비목표). 다만 인터페이스는 `PoseSequence` 기반으로 바꾼다.

**Files:**
- Create: `backend/app/services/swing/phases.py`
- Test: `backend/tests/swing/test_phases.py`
- Reference: `backend/app/services/pose_estimator.py:56-105` (`detect_swing_window`), `:185-247` (7단계 배정)

**Interfaces:**
- Consumes: Task 1의 `PHASE_KEYS`·`PoseSequence`, Task 2의 랜드마크 상수
- Produces:
  - `detect_swing_window(video_path: str) -> tuple[int, int, float]` — `(start_frame, end_frame, fps)`. 기존 함수를 그대로 옮긴 것
  - `detect_phases(seq: PoseSequence) -> dict[str, int]` — 7단계 키 → 시퀀스 인덱스

- [ ] **Step 1: `metrics.py`에 팔·손목 상수 추가**

`backend/app/services/swing/metrics.py`의 랜드마크 상수 구역
(`L_SHOULDER, R_SHOULDER = 11, 12` 바로 아래)에 두 줄 추가한다.
Task 10은 손목을, Task 11은 팔꿈치를 쓴다.

```python
L_ELBOW, R_ELBOW = 13, 14
L_WRIST, R_WRIST = 15, 16
```

- [ ] **Step 2: 실패하는 테스트 작성**

`backend/tests/swing/test_phases.py`:

```python
import numpy as np
import pytest

from app.services.swing.metrics import L_WRIST, R_WRIST
from app.services.swing.phases import detect_phases
from app.services.swing.types import PHASE_KEYS, PoseSequence


def _swing_sequence(frames: int = 40) -> PoseSequence:
    """손목이 내려갔다(어드레스) 올라갔다(탑) 다시 내려오는(임팩트) 궤적."""
    xy = np.zeros((frames, 33, 2), dtype=np.float32)
    world = np.zeros((frames, 33, 3), dtype=np.float32)
    for f in range(frames):
        t = f / (frames - 1)
        if t < 0.5:
            wrist_y = 700.0 - (t / 0.5) * 400.0      # 700 → 300 (올라감)
        else:
            wrist_y = 300.0 + ((t - 0.5) / 0.5) * 400.0  # 300 → 700 (내려옴)
        xy[f, L_WRIST] = (500.0, wrist_y)
        xy[f, R_WRIST] = (510.0, wrist_y)
        xy[f, 11] = (450.0, 400.0)
        xy[f, 12] = (550.0, 400.0)
    return PoseSequence(
        world=world, xy_px=xy,
        visibility=np.full((frames, 33), 0.9, dtype=np.float32),
        frame_indices=np.arange(frames, dtype=np.int32),
        fps=60.0, resolution_wh=(1000, 1000),
    )


def test_detect_phases_returns_all_seven_keys():
    assert set(detect_phases(_swing_sequence())) == set(PHASE_KEYS)


def test_phases_are_in_chronological_order():
    phases = detect_phases(_swing_sequence())
    order = [phases[k] for k in PHASE_KEYS]
    assert order == sorted(order), f"단계가 시간 순이 아니다: {phases}"


def test_phase_indices_are_within_sequence():
    seq = _swing_sequence(40)
    for key, idx in detect_phases(seq).items():
        assert 0 <= idx < len(seq), f"{key} 인덱스 {idx} 가 범위를 벗어났다"


def test_top_is_where_wrist_is_highest():
    """탑에서 손목 y(픽셀)가 가장 작아야 한다."""
    seq = _swing_sequence(40)
    phases = detect_phases(seq)
    wrist_y = seq.xy_px[:, R_WRIST, 1]
    assert abs(phases["top"] - int(np.argmin(wrist_y))) <= 3


def test_raises_when_sequence_too_short():
    with pytest.raises(ValueError, match="프레임"):
        detect_phases(_swing_sequence(2))
```

- [ ] **Step 3: 테스트 실패 확인**

```bash
cd backend && .venv/bin/pytest tests/swing/test_phases.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'app.services.swing.phases'`

- [ ] **Step 4: 구현**

`backend/app/services/swing/phases.py`를 만든다.

`detect_swing_window()`는 `pose_estimator.py:56-105`를 **그대로 복사**한다 (알고리즘 변경 금지).

`detect_phases()`는 `pose_estimator.py:185-247`의 `motion_mag` 앵커 로직을 옮기되, 입력을 `PoseSequence`로 바꾼다:

```python
"""
swing/phases.py — 스윙 구간 탐지와 7단계 분할.

알고리즘은 기존 pose_estimator.py 를 그대로 옮긴 것이다.
정확도 개선은 이번 범위 밖이다 (스펙 §1 비목표).
"""
from __future__ import annotations

import numpy as np

from app.services.swing.metrics import L_SHOULDER, L_WRIST, R_SHOULDER, R_WRIST
from app.services.swing.types import PHASE_KEYS, PoseSequence

_SMOOTH_WINDOW = 3


def _smooth(values: np.ndarray, window: int = _SMOOTH_WINDOW) -> np.ndarray:
    """이동 평균. 경계에서는 있는 만큼만 평균낸다."""
    n = len(values)
    return np.array(
        [values[max(0, i - window) : min(n, i + window + 1)].mean() for i in range(n)],
        dtype=np.float64,
    )


def detect_phases(seq: PoseSequence) -> dict[str, int]:
    """손목 궤적과 이동량으로 7단계 프레임 인덱스를 찾는다.

    ① 임팩트  = 이동량 최댓값 (클럽과 손목이 가장 빠른 순간)
    ② 탑      = 임팩트 이전 이동량 최솟값 (잠시 멈추는 지점)
    ③ 어드레스 = 유의미한 움직임이 시작되기 직전
    ④ 피니시   = 움직임이 잦아든 뒤 마지막 지점
    ⑤ 나머지 3단계 = 위 네 지점 사이의 비율 보간
    """
    n = len(seq)
    if n < 4:
        raise ValueError(
            f"포즈가 인식된 프레임이 부족합니다 ({n}개). "
            "전신이 보이도록 다시 촬영해 주세요."
        )

    wrist_y = seq.xy_px[:, R_WRIST, 1]
    wrist_x = seq.xy_px[:, R_WRIST, 0]
    shoulder_x = (seq.xy_px[:, L_SHOULDER, 0] + seq.xy_px[:, R_SHOULDER, 0]) / 2.0

    motion = np.abs(np.diff(wrist_y)) + np.abs(np.diff(wrist_x)) + np.abs(
        np.diff(shoulder_x)
    )
    if len(motion) == 0:
        motion = np.zeros(1, dtype=np.float64)
    smoothed = _smooth(motion)

    def clamp(i: int) -> int:
        return max(0, min(n - 1, int(i)))

    impact_m = int(np.argmax(smoothed))
    impact = clamp(impact_m + 1)

    search_end = max(1, impact_m * 2 // 3)
    top = clamp(int(np.argmin(smoothed[1 : search_end + 1])) + 1) if search_end >= 1 else clamp(impact * 4 // 10)

    onset_threshold = float(smoothed.mean()) * 0.5
    onset = next((k for k in range(len(smoothed)) if smoothed[k] > onset_threshold), 0)
    address = max(0, clamp(onset) - 1)

    quiet_threshold = float(smoothed.mean()) * 0.4
    finish = n - 1
    for k in range(len(smoothed) - 1, impact_m, -1):
        if smoothed[k] > quiet_threshold:
            finish = clamp(k + 1)
            break

    # 단조 증가를 보장한다. 어긋나면 지표 전부가 틀어진다.
    address = min(address, n - 4)
    top = max(address + 1, min(top, n - 3))
    impact = max(top + 1, min(impact, n - 2))
    finish = max(impact + 1, min(finish, n - 1))

    phases = {
        "address": address,
        "takeaway": clamp(address + max(1, (top - address) * 35 // 100)),
        "top": top,
        "downswing": clamp(top + max(1, (impact - top) * 45 // 100)),
        "impact": impact,
        "followthrough": clamp(impact + max(1, (finish - impact) * 40 // 100)),
        "finish": finish,
    }
    assert set(phases) == set(PHASE_KEYS)
    return phases
```

`detect_swing_window()`는 같은 파일에 `pose_estimator.py:56-105`를 복사해 넣는다.

- [ ] **Step 5: 전체 테스트 통과 확인**

```bash
cd backend && .venv/bin/pytest tests/swing/ -v
```

Expected: 전체 통과

- [ ] **Step 6: 커밋**

```bash
git add backend/app/services/swing/ backend/tests/swing/
git commit -m "refactor(swing): move phase detection into swing.phases"
```

---

## Task 11: supervision 오버레이

`pose_estimator.py:250-300`의 `make_overlay()`는 cv2로 선과 원을 직접 그린다. supervision의 어노테이터로 교체한다.

**Files:**
- Create: `backend/app/services/swing/overlay.py`
- Test: `backend/tests/swing/test_overlay.py`

**Interfaces:**
- Consumes: Task 2의 랜드마크 상수
- Produces:
  - `GOLF_EDGES: list[tuple[int, int]]` — 골프에 의미 있는 뼈대 연결
  - `render_overlay(frame: np.ndarray, xy_px: np.ndarray, label: str) -> bytes | None` — JPEG 바이트. 크롭이 불가능하면 `None`

- [ ] **Step 1: 실패하는 테스트 작성**

`backend/tests/swing/test_overlay.py`:

```python
import cv2
import numpy as np
import pytest

from app.services.swing.overlay import GOLF_EDGES, render_overlay
from app.services.swing.metrics import L_HIP, L_SHOULDER, R_HIP, R_SHOULDER


def _frame(w=1000, h=1000):
    return np.full((h, w, 3), 30, dtype=np.uint8)


def _body(w=1000, h=1000):
    xy = np.zeros((33, 2), dtype=np.float32)
    xy[L_SHOULDER] = (400.0, 300.0)
    xy[R_SHOULDER] = (600.0, 300.0)
    xy[L_HIP] = (430.0, 550.0)
    xy[R_HIP] = (570.0, 550.0)
    for i in (25, 26):
        xy[i] = (430.0 + (i - 25) * 140, 750.0)
    for i in (27, 28):
        xy[i] = (430.0 + (i - 27) * 140, 930.0)
    xy[0] = (500.0, 220.0)
    return xy


def test_golf_edges_connect_shoulders_and_hips():
    assert (L_SHOULDER, R_SHOULDER) in GOLF_EDGES
    assert (L_HIP, R_HIP) in GOLF_EDGES


def test_golf_edges_reference_valid_landmarks():
    for a, b in GOLF_EDGES:
        assert 0 <= a < 33 and 0 <= b < 33


def test_render_returns_decodable_jpeg():
    data = render_overlay(_frame(), _body(), "5.임팩트")
    assert data is not None
    decoded = cv2.imdecode(np.frombuffer(data, dtype=np.uint8), cv2.IMREAD_COLOR)
    assert decoded is not None
    assert decoded.shape[0] > 0 and decoded.shape[1] > 0


def test_render_draws_something_on_the_frame():
    """빈 배경 그대로면 스켈레톤이 안 그려진 것이다."""
    blank = _frame()
    data = render_overlay(blank, _body(), "5.임팩트")
    decoded = cv2.imdecode(np.frombuffer(data, dtype=np.uint8), cv2.IMREAD_COLOR)
    assert decoded.std() > 5.0


def test_render_returns_none_when_no_valid_landmarks():
    """전부 0이면 크롭 영역을 만들 수 없다."""
    assert render_overlay(_frame(), np.zeros((33, 2), dtype=np.float32), "1.어드레스") is None
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
cd backend && .venv/bin/pytest tests/swing/test_overlay.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'app.services.swing.overlay'`

- [ ] **Step 3: 구현**

`backend/app/services/swing/overlay.py`:

```python
"""
swing/overlay.py — supervision 으로 스켈레톤 오버레이를 그린다.

기존 pose_estimator.make_overlay() 의 cv2 수작업을 대체한다.
"""
from __future__ import annotations

import cv2
import numpy as np
import supervision as sv

from app.services.swing.metrics import (
    L_ANKLE,
    L_ELBOW,
    L_HIP,
    L_KNEE,
    L_SHOULDER,
    L_WRIST,
    R_ANKLE,
    R_ELBOW,
    R_HIP,
    R_KNEE,
    R_SHOULDER,
    R_WRIST,
)

# 골프에서 의미 있는 뼈대만 그린다. 손가락·얼굴은 빼서 화면을 비운다.
GOLF_EDGES: list[tuple[int, int]] = [
    (L_SHOULDER, R_SHOULDER),   # 어깨선
    (L_HIP, R_HIP),             # 힙선
    (L_SHOULDER, L_ELBOW), (L_ELBOW, L_WRIST),
    (R_SHOULDER, R_ELBOW), (R_ELBOW, R_WRIST),
    (L_HIP, L_KNEE), (L_KNEE, L_ANKLE),
    (R_HIP, R_KNEE), (R_KNEE, R_ANKLE),
    (L_SHOULDER, L_HIP), (R_SHOULDER, R_HIP),
]

_EDGE_ANNOTATOR = sv.EdgeAnnotator(
    color=sv.Color(r=0, g=200, b=255), thickness=3, edges=GOLF_EDGES
)
_VERTEX_ANNOTATOR = sv.VertexAnnotator(color=sv.Color(r=255, g=220, b=0), radius=5)

_PAD_X, _PAD_TOP, _PAD_BOTTOM = 0.35, 0.60, 0.25


def render_overlay(
    frame: np.ndarray, xy_px: np.ndarray, label: str
) -> bytes | None:
    """골퍼를 크롭하고 스켈레톤과 단계 라벨을 그려 JPEG 로 인코딩한다.

    유효한 랜드마크가 없어 크롭 영역을 정할 수 없으면 None.
    """
    h, w = frame.shape[:2]
    valid = xy_px[(xy_px[:, 0] > 0) & (xy_px[:, 1] > 0)]
    if len(valid) == 0:
        return None

    key_points = sv.KeyPoints(xy=xy_px[np.newaxis, ...].astype(np.float32))
    scene = _EDGE_ANNOTATOR.annotate(scene=frame.copy(), key_points=key_points)
    scene = _VERTEX_ANNOTATOR.annotate(scene=scene, key_points=key_points)

    x_min, y_min = valid.min(axis=0)
    x_max, y_max = valid.max(axis=0)
    box_w, box_h = x_max - x_min, y_max - y_min

    x1 = max(0, int(x_min - max(box_w * _PAD_X, w * 0.06)))
    x2 = min(w, int(x_max + max(box_w * _PAD_X, w * 0.06)))
    y1 = max(0, int(y_min - max(box_h * _PAD_TOP, h * 0.10)))
    y2 = min(h, int(y_max + max(box_h * _PAD_BOTTOM, h * 0.05)))

    crop = scene[y1:y2, x1:x2]
    if crop.shape[0] < 10 or crop.shape[1] < 10:
        return None

    ch, cw = crop.shape[:2]
    cv2.rectangle(crop, (0, ch - 28), (cw, ch), (0, 0, 0), -1)
    cv2.putText(
        crop, label, (4, ch - 8), cv2.FONT_HERSHEY_SIMPLEX,
        0.5, (255, 255, 255), 1, cv2.LINE_AA,
    )

    ok, buffer = cv2.imencode(".jpg", crop, [cv2.IMWRITE_JPEG_QUALITY, 90])
    return buffer.tobytes() if ok else None
```

`L_ELBOW`·`R_ELBOW`는 Task 10 Step 1에서 이미 추가했으므로 그대로 쓴다.

- [ ] **Step 4: 테스트 통과 확인**

```bash
cd backend && .venv/bin/pytest tests/swing/test_overlay.py -v
```

Expected: 5 passed

`sv.EdgeAnnotator`·`sv.VertexAnnotator`의 인자 이름이 다르면 다음으로 실제 시그니처를 확인해 맞춘다:

```bash
cd backend && .venv/bin/python -c "import supervision as sv, inspect; print(inspect.signature(sv.EdgeAnnotator.__init__)); print(inspect.signature(sv.EdgeAnnotator.annotate))"
```

- [ ] **Step 5: 커밋**

```bash
git add backend/app/services/swing/ backend/tests/swing/test_overlay.py
git commit -m "refactor(swing): render skeleton overlay with supervision annotators"
```

---

## Task 12: 파이프라인 배선

`pose_estimator.py`의 오케스트레이션(다운로드·DB·R2·asyncio)을 `pipeline.py`로 옮기고, 지표 계산을 새 모듈로 갈아 끼운다. **여기서 가짜 기본값이 DB에서 사라진다.**

**Files:**
- Create: `backend/app/services/swing/pipeline.py`
- Modify: `backend/app/services/pose_estimator.py` (호환 래퍼만 남긴다)
- Modify: `backend/app/api/endpoints/upload.py:81` (import 경로)
- Test: `backend/tests/swing/test_pipeline.py`

**Interfaces:**
- Consumes: Task 7 `compute_metrics`·`metrics_to_json`, Task 8 `extract_sequence`, Task 10 `detect_swing_window`·`detect_phases`, Task 11 `render_overlay`
- Produces: `async def process_pose_estimation(upload_id: uuid.UUID) -> None`

- [ ] **Step 1: 실패하는 테스트 작성**

DB와 R2를 타지 않는 순수 부분만 검증한다.

`backend/tests/swing/test_pipeline.py`:

```python
import numpy as np

from app.services.swing.metrics import compute_metrics, metrics_to_json
from app.services.swing.pipeline import PHASE_LABELS, summarise_metrics
from app.services.swing.types import PHASE_KEYS


def test_phase_labels_cover_all_seven_phases_in_korean():
    assert set(PHASE_LABELS) == set(PHASE_KEYS)
    assert PHASE_LABELS["impact"] == "5.임팩트"
    assert PHASE_LABELS["address"] == "1.어드레스"


def test_summarise_counts_only_measured_metrics():
    payload = {
        "spine_angle": {"value": 35.0, "confidence": 0.9, "unit": "°", "measurable": True},
        "knee_flex": {"value": None, "confidence": 0.0, "unit": "°", "measurable": True},
        "x_factor": {"value": None, "confidence": 0.0, "unit": "°", "measurable": False},
    }
    summary = summarise_metrics(payload)
    assert summary["measured_count"] == 1
    assert summary["total_count"] == 3


def test_summarise_reports_zero_when_nothing_measured():
    payload = {
        "spine_angle": {"value": None, "confidence": 0.0, "unit": "°", "measurable": True},
    }
    assert summarise_metrics(payload)["measured_count"] == 0
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
cd backend && .venv/bin/pytest tests/swing/test_pipeline.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'app.services.swing.pipeline'`

- [ ] **Step 3: 구현**

`backend/app/services/swing/pipeline.py`를 만든다. `pose_estimator.py:340-439`의 `process_pose_estimation()`을 옮기되, 지표 부분을 다음으로 바꾼다:

```python
PHASE_LABELS: dict[str, str] = {
    "address": "1.어드레스",
    "takeaway": "2.테이크백",
    "top": "3.탑",
    "downswing": "4.다운스윙",
    "impact": "5.임팩트",
    "followthrough": "6.팔로우스루",
    "finish": "7.피니시",
}


def summarise_metrics(payload: dict) -> dict:
    """히스토리 목록에서 촬영이 잘 됐는지 가늠할 요약값."""
    measured = sum(
        1 for m in payload.values() if m.get("value") is not None
    )
    return {"measured_count": measured, "total_count": len(payload)}
```

그리고 기존 `metrics = {...}` 블록(하드코딩 `head_movement: 1.7` 포함)을 통째로 다음으로 대체한다:

```python
start_f, end_f, fps = await loop.run_in_executor(
    None, detect_swing_window, video_path
)
seq = await loop.run_in_executor(
    None, extract_sequence, video_path, start_f, end_f
)
phases = detect_phases(seq)
camera_angle = upload.camera_angle or "down_the_line"
metrics = compute_metrics(seq, phases, camera_angle)
metrics_payload = metrics_to_json(metrics)
metrics_payload["_meta"] = {
    "camera_angle": camera_angle,
    "swing_start_sec": round(start_f / fps, 2),
    "swing_end_sec": round(end_f / fps, 2),
    **summarise_metrics(
        {k: v for k, v in metrics_payload.items() if k != "_meta"}
    ),
}
```

> `upload.camera_angle` 컬럼은 Plan 2에서 추가한다. 그 전까지는
> `getattr(upload, "camera_angle", None) or "down_the_line"` 으로 읽어
> Plan 2 없이도 이 계획이 단독으로 동작하게 한다.

- [ ] **Step 4: 기존 모듈을 호환 래퍼로 축소**

`backend/app/services/pose_estimator.py`의 내용을 전부 지우고 다음만 남긴다:

```python
"""
pose_estimator.py — 하위 호환 래퍼.

실제 구현은 app.services.swing 패키지로 옮겼다.
새 코드는 app.services.swing.pipeline 을 직접 import 할 것.
"""
from app.services.swing.pipeline import process_pose_estimation

__all__ = ["process_pose_estimation"]
```

- [ ] **Step 5: 전체 테스트 실행**

```bash
cd backend && .venv/bin/pytest tests/ -v
```

Expected: 전체 통과

- [ ] **Step 6: 하드코딩된 가짜 값이 사라졌는지 확인**

```bash
cd backend && grep -rnE "head_movement.*1\.7|\"hip_rotation\", *32|\"shoulder_rotation\", *88|\"knee_flex\", *22|weight_transfer.*55" app/ || echo "✓ 가짜 기본값 없음"
```

Expected: `✓ 가짜 기본값 없음`

- [ ] **Step 7: 커밋**

```bash
git add backend/app/services/ backend/tests/swing/test_pipeline.py
git commit -m "refactor(swing): wire pipeline to measured metrics, drop fake defaults"
```

---

## Task 13: 규칙 엔진 — 진단과 드릴

지금은 LLM이 진단·점수·드릴을 **전부** 만들고, 실패하면 빈 껍데기와 "혼잡합니다" 메시지가 나간다. 관계를 뒤집는다: 규칙이 확정하고 LLM은 문장만 다듬는다 (스펙 §4.3).

`_calculate_score()`의 기준값들이 지금 프롬프트 문자열에 박혀 있다. 여기로 옮긴다.

**Files:**
- Create: `backend/app/services/feedback/__init__.py`
- Create: `backend/app/services/feedback/rules.py`
- Create: `backend/app/services/feedback/drills.py`
- Test: `backend/tests/feedback/__init__.py`, `backend/tests/feedback/test_rules.py`

**Interfaces:**
- Consumes: Task 7의 `metrics_to_json` 출력 형태
- Produces:
  - `MetricRule(key, label_ko, ideal, tolerance, low_msg, high_msg)`
  - `RULES: dict[str, MetricRule]`
  - `score_metric(key, value) -> int` — 0~100
  - `evaluate(payload: dict) -> dict` — `{overall_score, grade, top_issues, drills, encouragement}`
  - `DRILLS: dict[str, dict]` — 지표별 드릴

- [ ] **Step 1: 실패하는 테스트 작성**

`backend/tests/feedback/__init__.py` (빈 파일)과 `backend/tests/feedback/test_rules.py`:

```python
import pytest

from app.services.feedback.drills import DRILLS
from app.services.feedback.rules import RULES, evaluate, score_metric


def _payload(**values):
    """지표 페이로드를 만든다. 값이 None 이면 측정 실패."""
    out = {}
    for key, value in values.items():
        out[key] = {
            "value": value,
            "confidence": 0.9 if value is not None else 0.0,
            "unit": RULES[key].unit if key in RULES else "°",
            "measurable": True,
        }
    return out


def test_every_rule_has_a_drill():
    """진단만 하고 처방이 없으면 사용자가 할 수 있는 일이 없다."""
    for key in RULES:
        assert key in DRILLS, f"{key} 에 대응하는 드릴이 없다"


def test_drill_has_korean_steps():
    for key, drill in DRILLS.items():
        assert drill["drill_name"], key
        assert len(drill["steps"]) >= 2, key
        assert drill["repetitions"], key


def test_perfect_value_scores_one_hundred():
    assert score_metric("spine_angle", RULES["spine_angle"].ideal) == 100


def test_score_decreases_as_value_deviates():
    ideal = RULES["spine_angle"].ideal
    near = score_metric("spine_angle", ideal + 3.0)
    far = score_metric("spine_angle", ideal + 20.0)
    assert 100 > near > far >= 0


def test_score_is_clamped_to_zero():
    assert score_metric("spine_angle", 1000.0) == 0


def test_evaluate_ignores_unmeasured_metrics():
    """측정 실패한 지표가 점수를 끌어내리면 안 된다."""
    result = evaluate(_payload(spine_angle=37.0, knee_flex=None))
    assert result["overall_score"] == 100


def test_evaluate_returns_grade_for_score():
    assert evaluate(_payload(spine_angle=37.0))["grade"] == "A"
    assert evaluate(_payload(spine_angle=1000.0))["grade"] == "D"


def test_evaluate_ranks_worst_issues_first():
    result = evaluate(_payload(spine_angle=37.0, knee_flex=90.0, tempo_ratio=0.2))
    severities = [i["severity"] for i in result["top_issues"]]
    assert severities == sorted(severities, key=lambda s: {"high": 0, "medium": 1, "low": 2}[s])


def test_evaluate_returns_at_most_three_issues():
    payload = _payload(
        spine_angle=1000.0, knee_flex=1000.0, tempo_ratio=0.01,
        head_movement=90.0, weight_shift=0.0,
    )
    assert len(evaluate(payload)["top_issues"]) <= 3


def test_evaluate_with_nothing_measured_says_so_in_korean():
    result = evaluate(_payload(spine_angle=None))
    assert result["overall_score"] is None
    assert "측정" in result["encouragement"]


def test_issue_feedback_is_korean_and_specific():
    result = evaluate(_payload(spine_angle=80.0))
    issue = result["top_issues"][0]
    assert issue["metric"] == "spine_angle"
    assert len(issue["feedback"]) > 10
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
cd backend && .venv/bin/pytest tests/feedback/test_rules.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'app.services.feedback'`

- [ ] **Step 3: 드릴 라이브러리 구현**

`backend/app/services/feedback/__init__.py` (빈 파일).

`backend/app/services/feedback/drills.py`:

```python
"""
feedback/drills.py — 지표별 교정 드릴.

LLM이 아니라 여기서 확정한다. LLM이 죽어도 사용자는 할 일을 받는다.
"""
from __future__ import annotations

DRILLS: dict[str, dict] = {
    "spine_angle": {
        "drill_name": "벽 기대기 어드레스",
        "steps": [
            "엉덩이를 벽에 살짝 댄 채 어드레스 자세를 잡습니다.",
            "가슴을 앞으로 숙여 척추가 30~45도 기울도록 만듭니다.",
            "그 각도를 유지한 채 10초간 멈춥니다.",
        ],
        "repetitions": "10회 × 3세트",
        "tip": "허리를 굽히지 말고 고관절에서 접으세요.",
    },
    "knee_flex": {
        "drill_name": "의자 터치 스쿼트",
        "steps": [
            "의자 앞에 서서 어드레스 자세를 잡습니다.",
            "엉덩이가 의자에 닿을 듯 말 듯 무릎을 20~30도 굽힙니다.",
            "그 자세에서 좌우로 가볍게 체중을 옮겨 봅니다.",
        ],
        "repetitions": "15회 × 3세트",
        "tip": "무릎이 발끝보다 앞으로 나가지 않게 합니다.",
    },
    "shoulder_rotation": {
        "drill_name": "클럽 크로스 백스윙",
        "steps": [
            "클럽을 양 어깨에 가로로 걸칩니다.",
            "하체를 고정한 채 상체만 오른쪽으로 끝까지 돌립니다.",
            "어깨가 90도 돌아간 지점에서 3초간 멈춥니다.",
        ],
        "repetitions": "12회 × 3세트",
        "tip": "고개가 따라 돌지 않도록 공 위치를 계속 봅니다.",
    },
    "hip_rotation": {
        "drill_name": "골반 분리 회전",
        "steps": [
            "어드레스 자세에서 양손을 골반에 올립니다.",
            "상체는 그대로 두고 골반만 오른쪽으로 45도 돌립니다.",
            "천천히 제자리로 돌아옵니다.",
        ],
        "repetitions": "15회 × 3세트",
        "tip": "무릎이 같이 돌아가면 회전이 새는 것입니다.",
    },
    "x_factor": {
        "drill_name": "상하체 분리 스트레치",
        "steps": [
            "무릎 사이에 공을 끼우고 어드레스 자세를 잡습니다.",
            "공이 움직이지 않게 고정한 채 어깨만 최대한 돌립니다.",
            "가장 돌아간 지점에서 5초간 버팁니다.",
        ],
        "repetitions": "10회 × 3세트",
        "tip": "어깨와 골반의 각도 차이가 클수록 비거리가 늘어납니다.",
    },
    "head_movement": {
        "drill_name": "벽 헤드 고정 스윙",
        "steps": [
            "머리 옆쪽이 벽에 살짝 닿도록 서서 어드레스합니다.",
            "머리가 벽에서 떨어지지 않게 백스윙합니다.",
            "임팩트까지 같은 접촉을 유지합니다.",
        ],
        "repetitions": "20회 × 2세트",
        "tip": "머리를 누르지 말고 '제자리에 두는' 느낌으로 합니다.",
    },
    "weight_shift": {
        "drill_name": "스텝 스루 드릴",
        "steps": [
            "두 발을 모으고 어드레스 자세를 잡습니다.",
            "백스윙하면서 앞발을 타겟 쪽으로 한 걸음 내딛습니다.",
            "그 발에 체중을 실으며 다운스윙합니다.",
        ],
        "repetitions": "15회 × 3세트",
        "tip": "체중이 먼저 가고 팔이 뒤따라오는 순서를 익힙니다.",
    },
    "tempo_ratio": {
        "drill_name": "하나-둘-셋 카운트 스윙",
        "steps": [
            "'하나, 둘, 셋'을 세며 백스윙을 올립니다.",
            "'넷'에 맞춰 한 박자로 내려칩니다.",
            "메트로놈이 있으면 60bpm에 맞춥니다.",
        ],
        "repetitions": "20회 × 2세트",
        "tip": "빠르게 치려 하지 말고 리듬을 일정하게 만드세요.",
    },
}
```

- [ ] **Step 4: 규칙 엔진 구현**

`backend/app/services/feedback/rules.py`:

```python
"""
feedback/rules.py — 지표에서 진단·점수·등급을 확정한다.

LLM 없이 완결된다. LLM은 이 결과의 문장을 다듬을 뿐이다 (스펙 §4.3).
"""
from __future__ import annotations

from dataclasses import dataclass

from app.services.feedback.drills import DRILLS

_SEVERITY_ORDER = {"high": 0, "medium": 1, "low": 2}


@dataclass(frozen=True)
class MetricRule:
    key: str
    label_ko: str
    unit: str
    ideal: float
    tolerance: float   # 이 폭만큼 벗어나면 100점에서 0점이 된다
    low_msg: str       # 기준보다 낮을 때
    high_msg: str      # 기준보다 높을 때


RULES: dict[str, MetricRule] = {
    "spine_angle": MetricRule(
        "spine_angle", "척추 각도", "°", 37.0, 25.0,
        "상체가 너무 서 있습니다. 고관절에서 조금 더 숙여 주세요.",
        "상체를 과하게 숙였습니다. 조금 더 세워서 시야를 확보하세요.",
    ),
    "knee_flex": MetricRule(
        "knee_flex", "무릎 굴곡", "°", 25.0, 20.0,
        "무릎이 거의 펴져 있어 하체가 버텨 주지 못합니다.",
        "무릎을 너무 굽혀 회전이 막힙니다. 살짝만 굽히세요.",
    ),
    "shoulder_rotation": MetricRule(
        "shoulder_rotation", "어깨 회전", "°", 90.0, 45.0,
        "어깨 회전이 부족해 비거리가 손해를 봅니다.",
        "어깨가 과하게 돌아 임팩트에서 정확도가 떨어집니다.",
    ),
    "hip_rotation": MetricRule(
        "hip_rotation", "힙 회전", "°", 45.0, 30.0,
        "골반 회전이 부족합니다. 하체가 멈춰 있습니다.",
        "골반이 과하게 돌아 상하체 분리가 사라졌습니다.",
    ),
    "x_factor": MetricRule(
        "x_factor", "X-팩터", "°", 45.0, 35.0,
        "상하체 분리가 부족해 파워가 새고 있습니다.",
        "분리가 과해 몸에 무리가 갈 수 있습니다.",
    ),
    "head_movement": MetricRule(
        "head_movement", "헤드 무브먼트", "cm", 2.0, 10.0,
        "",  # 0에 가까울수록 좋으므로 낮을 때 지적할 것이 없다
        "머리가 많이 움직여 임팩트가 불안정합니다.",
    ),
    "weight_shift": MetricRule(
        "weight_shift", "체중 이동(추정)", "%", 15.0, 15.0,
        "체중이 뒤에 남아 있습니다. 타겟 쪽으로 밀어 주세요.",
        "체중이 과하게 앞으로 쏠려 균형이 무너집니다.",
    ),
    "tempo_ratio": MetricRule(
        "tempo_ratio", "템포 비율", ":1", 3.0, 2.0,
        "백스윙이 너무 빠릅니다. 조금 더 여유 있게 올리세요.",
        "백스윙이 너무 느려 리듬이 끊깁니다.",
    ),
}


def score_metric(key: str, value: float) -> int:
    """기준값에서 벗어난 정도를 0~100 점수로 바꾼다."""
    rule = RULES[key]
    deviation = abs(value - rule.ideal)
    score = 100.0 * (1.0 - deviation / rule.tolerance)
    return int(max(0.0, min(100.0, score)))


def _severity(score: int) -> str:
    if score < 50:
        return "high"
    if score < 75:
        return "medium"
    return "low"


def _grade(score: int) -> str:
    if score >= 85:
        return "A"
    if score >= 70:
        return "B"
    if score >= 55:
        return "C"
    return "D"


def evaluate(payload: dict) -> dict:
    """지표 페이로드에서 진단·점수·드릴을 만든다.

    측정되지 않은 지표는 점수 계산에서 제외한다.
    측정된 것이 하나도 없으면 overall_score 는 None 이다.
    없는 점수를 지어내지 않는다 (스펙 §3.4).
    """
    scored: list[tuple[str, float, int]] = []
    for key, rule in RULES.items():
        entry = payload.get(key)
        if not entry or entry.get("value") is None:
            continue
        value = float(entry["value"])
        scored.append((key, value, score_metric(key, value)))

    if not scored:
        return {
            "overall_score": None,
            "grade": None,
            "top_issues": [],
            "drills": [],
            "encouragement": (
                "이번 영상에서는 지표를 측정하지 못했습니다. "
                "전신이 화면에 들어오도록 조금 더 멀리서 다시 촬영해 주세요."
            ),
        }

    overall = int(round(sum(s for _, _, s in scored) / len(scored)))

    issues = []
    for key, value, score in sorted(scored, key=lambda t: t[2]):
        if score >= 75:
            continue
        rule = RULES[key]
        message = rule.high_msg if value > rule.ideal else rule.low_msg
        if not message:
            message = rule.high_msg or rule.low_msg
        issues.append({
            "metric": key,
            "label": rule.label_ko,
            "severity": _severity(score),
            "score": score,
            "feedback": (
                f"{rule.label_ko}가 {value}{rule.unit}로 측정됐습니다"
                f"(기준 {rule.ideal}{rule.unit}). {message}"
            ),
        })
    issues = sorted(issues, key=lambda i: _SEVERITY_ORDER[i["severity"]])[:3]

    drills = [
        {"issue_metric": i["metric"], **DRILLS[i["metric"]]} for i in issues
    ]

    if overall >= 85:
        encouragement = "안정적인 스윙입니다. 지금 감각을 유지하세요."
    elif overall >= 70:
        encouragement = "기본기는 잡혀 있습니다. 위 드릴로 한 단계 더 올려 보세요."
    else:
        encouragement = "고칠 지점이 뚜렷합니다. 드릴 하나씩만 집중해 보세요."

    return {
        "overall_score": overall,
        "grade": _grade(overall),
        "top_issues": issues,
        "drills": drills,
        "encouragement": encouragement,
    }
```

- [ ] **Step 5: 테스트 통과 확인**

```bash
cd backend && .venv/bin/pytest tests/feedback/ -v
```

Expected: 11 passed

- [ ] **Step 6: 커밋**

```bash
git add backend/app/services/feedback/ backend/tests/feedback/
git commit -m "feat(feedback): add rule engine and drill library independent of LLM"
```

---

## Task 14: LLM을 윤문 역할로 축소

**Files:**
- Create: `backend/app/services/feedback/llm.py`
- Modify: `backend/app/services/llm_feedback.py` (호환 래퍼로 축소)
- Modify: `backend/app/services/swing/pipeline.py` (호출부 교체)
- Test: `backend/tests/feedback/test_llm.py`

**Interfaces:**
- Consumes: Task 13의 `evaluate()` 출력
- Produces: `async def polish(rule_result: dict) -> dict` — 실패 시 입력을 그대로 반환

- [ ] **Step 1: 실패하는 테스트 작성**

`backend/tests/feedback/test_llm.py`:

```python
from unittest.mock import AsyncMock, patch

import pytest

from app.services.feedback.llm import polish

_RULE_RESULT = {
    "overall_score": 68,
    "grade": "C",
    "top_issues": [{
        "metric": "spine_angle", "label": "척추 각도",
        "severity": "medium", "score": 62,
        "feedback": "척추 각도가 55.0°로 측정됐습니다(기준 37.0°).",
    }],
    "drills": [{"issue_metric": "spine_angle", "drill_name": "벽 기대기 어드레스",
                "steps": ["1", "2"], "repetitions": "10회", "tip": "고관절에서 접으세요."}],
    "encouragement": "기본기는 잡혀 있습니다.",
}


async def test_returns_rule_result_when_api_key_missing(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    assert await polish(_RULE_RESULT) == _RULE_RESULT


async def test_returns_rule_result_when_request_fails(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    with patch("app.services.feedback.llm._request", new=AsyncMock(side_effect=RuntimeError("boom"))):
        assert await polish(_RULE_RESULT) == _RULE_RESULT


async def test_scores_are_never_overwritten_by_llm(monkeypatch):
    """LLM이 점수를 바꿔도 규칙 엔진 결과가 이긴다."""
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    tampered = {"overall_score": 99, "grade": "A", "encouragement": "다듬은 문장"}
    with patch("app.services.feedback.llm._request", new=AsyncMock(return_value=tampered)):
        result = await polish(_RULE_RESULT)
    assert result["overall_score"] == 68
    assert result["grade"] == "C"
    assert result["encouragement"] == "다듬은 문장"


async def test_drill_list_length_is_preserved(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    with patch("app.services.feedback.llm._request", new=AsyncMock(return_value={"drills": []})):
        result = await polish(_RULE_RESULT)
    assert len(result["drills"]) == 1
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
cd backend && .venv/bin/pytest tests/feedback/test_llm.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'app.services.feedback.llm'`

- [ ] **Step 3: 구현**

`backend/app/services/feedback/llm.py`:

```python
"""
feedback/llm.py — 규칙 엔진 결과의 한국어 문장만 다듬는다.

점수·등급·드릴 구성은 규칙 엔진이 확정한 것을 쓴다.
LLM이 죽어도 입력이 그대로 나가므로 서비스가 멈추지 않는다.
"""
from __future__ import annotations

import json
import logging
import os

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

_MODELS = [
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite",
    "gemini-2.0-flash-lite-001",
]
_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

_SYSTEM = (
    "당신은 한국의 아마추어 골퍼를 20년간 가르쳐 온 프로 골프 코치입니다. "
    "주어진 진단 결과의 숫자와 판단은 그대로 두고, 문장만 따뜻하고 자연스러운 "
    "한국어로 다듬으세요. 새로운 진단이나 드릴을 만들지 마세요."
)


def _api_key() -> str:
    """설정 경로를 한 곳으로 모은다.

    기존 llm_feedback.py 는 os.getenv 로 따로 읽어 설정이 이원화돼 있었다.
    """
    return settings.GEMINI_API_KEY or os.getenv("GEMINI_API_KEY", "")


async def _request(prompt: str, api_key: str) -> dict:
    """Gemini 호출. 모델 목록을 순서대로 시도한다."""
    payload = {
        "system_instruction": {"parts": [{"text": _SYSTEM}]},
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"responseMimeType": "application/json", "temperature": 0.7},
    }
    headers = {"x-goog-api-key": api_key, "Content-Type": "application/json"}

    last_error: Exception | None = None
    async with httpx.AsyncClient(timeout=20.0) as client:
        for model in _MODELS:
            try:
                response = await client.post(
                    _URL.format(model=model), json=payload, headers=headers
                )
                if response.status_code in (429, 503):
                    continue
                response.raise_for_status()
                text = response.json()["candidates"][0]["content"]["parts"][0]["text"]
                return json.loads(text)
            except Exception as exc:  # noqa: BLE001 - 다음 모델로 넘어간다
                last_error = exc
    raise RuntimeError(f"모든 모델 실패: {last_error}")


async def polish(rule_result: dict) -> dict:
    """문장만 다듬은 결과를 돌려준다. 실패하면 입력 그대로."""
    api_key = _api_key()
    if not api_key:
        logger.info("GEMINI_API_KEY 없음 — 규칙 엔진 결과를 그대로 사용")
        return rule_result

    prompt = (
        "아래 골프 스윙 진단 결과의 feedback·tip·encouragement 문장만 "
        "자연스러운 한국어로 다듬어 같은 JSON 구조로 돌려주세요. "
        "숫자·점수·등급·드릴 이름은 바꾸지 마세요.\n\n"
        + json.dumps(rule_result, ensure_ascii=False)
    )

    try:
        polished = await _request(prompt, api_key)
    except Exception as exc:  # noqa: BLE001
        logger.warning("LLM 윤문 실패 — 규칙 결과 사용: %s", exc)
        return rule_result

    # 규칙 엔진이 확정한 값은 LLM이 덮어쓸 수 없다.
    result = dict(rule_result)
    if isinstance(polished.get("encouragement"), str):
        result["encouragement"] = polished["encouragement"]

    for target, source in zip(result["top_issues"], polished.get("top_issues", [])):
        if isinstance(source, dict) and isinstance(source.get("feedback"), str):
            target["feedback"] = source["feedback"]

    for target, source in zip(result["drills"], polished.get("drills", [])):
        if isinstance(source, dict) and isinstance(source.get("tip"), str):
            target["tip"] = source["tip"]

    return result
```

- [ ] **Step 4: 기존 모듈을 호환 래퍼로 축소**

`backend/app/services/llm_feedback.py`의 내용을 전부 지우고:

```python
"""
llm_feedback.py — 하위 호환 래퍼.

진단·점수·드릴은 app.services.feedback.rules 가 확정하고,
app.services.feedback.llm 은 문장만 다듬는다.
"""
from app.services.feedback.llm import polish
from app.services.feedback.rules import evaluate

__all__ = ["evaluate", "polish"]
```

- [ ] **Step 5: 파이프라인 호출부 교체**

`pipeline.py`에서 `generate_feedback(metrics)` 를 다음으로 바꾼다:

```python
from app.services.feedback.llm import polish
from app.services.feedback.rules import evaluate

metrics_only = {k: v for k, v in metrics_payload.items() if k != "_meta"}
feedback_data = await polish(evaluate(metrics_only))
```

`asyncio.gather` 에 넘기던 `generate_feedback(metrics)` 자리에 위 코루틴을 넣는다.

- [ ] **Step 6: 키 없이 동작하는지 확인 — 완료 기준 항목**

```bash
cd backend && GEMINI_API_KEY= .venv/bin/pytest tests/ -v
```

Expected: 전체 통과

- [ ] **Step 7: 커밋**

```bash
git add backend/app/services/ backend/tests/feedback/test_llm.py
git commit -m "refactor(feedback): reduce LLM to polishing rule engine output"
```

---

## Task 15: 프론트엔드 8개 지표 표시

`frontend/src/app/analysis/[id]/page.tsx`는 지금 3개 지표만 보여준다 (80~82행, 194~196행). 8개로 늘리고, 측정 실패와 각도상 측정 불가를 **다르게** 표시한다.

**Files:**
- Create: `frontend/src/lib/metrics.ts`
- Modify: `frontend/src/app/analysis/[id]/page.tsx:80-82`, `:194-196`

**Interfaces:**
- Consumes: Task 7의 `metrics_to_json` 출력 (`{value, confidence, unit, measurable}`)
- Produces:
  - `type MetricEntry = { value: number | null; confidence: number; unit: string; measurable: boolean }`
  - `METRIC_META: Record<string, { label: string; ideal: number; range: number; note?: string }>`
  - `formatMetric(entry: MetricEntry | undefined): string`

- [ ] **Step 1: 지표 메타데이터 모듈 작성**

`frontend/src/lib/metrics.ts`:

```typescript
export type MetricEntry = {
  value: number | null;
  confidence: number;
  unit: string;
  measurable: boolean;
};

export const METRIC_META: Record<
  string,
  { label: string; ideal: number; range: number; note?: string }
> = {
  spine_angle: { label: "척추 각도", ideal: 37, range: 25 },
  knee_flex: { label: "무릎 굴곡", ideal: 25, range: 20 },
  shoulder_rotation: { label: "어깨 회전", ideal: 90, range: 45 },
  hip_rotation: { label: "힙 회전", ideal: 45, range: 30 },
  x_factor: { label: "X-팩터", ideal: 45, range: 35 },
  head_movement: { label: "헤드 무브먼트", ideal: 2, range: 10 },
  weight_shift: { label: "체중 이동", ideal: 15, range: 15, note: "추정치" },
  tempo_ratio: { label: "템포 비율", ideal: 3, range: 2 },
};

export const METRIC_ORDER = Object.keys(METRIC_META);

/** 측정값을 화면 문자열로 바꾼다. 없는 값을 지어내지 않는다. */
export function formatMetric(entry: MetricEntry | undefined): string {
  if (!entry) return "—";
  if (!entry.measurable) return "이 각도에서는 측정 불가";
  if (entry.value === null) return "측정 실패";
  return `${entry.value}${entry.unit}`;
}

/** 신뢰도가 낮으면 화면에서 경고를 띄운다. */
export function isLowConfidence(entry: MetricEntry | undefined): boolean {
  return Boolean(entry && entry.value !== null && entry.confidence < 0.5);
}
```

- [ ] **Step 2: 분석 화면의 지표 목록 교체**

`frontend/src/app/analysis/[id]/page.tsx:80-82`의 3개짜리 배열을 지우고 `METRIC_ORDER`·`METRIC_META`를 import 해 쓴다. `:194-196`의 `{ label, unit }` 매핑도 `METRIC_META`로 대체한다.

값 표시는 `formatMetric(metrics[key])`을 쓴다. `weight_shift`는 `METRIC_META.weight_shift.note`("추정치")를 라벨 옆에 작은 글씨로 함께 보여 준다. `isLowConfidence(...)`가 참이면 값 옆에 "인식 불안정" 표시를 붙인다.

- [ ] **Step 3: 타입 검사**

```bash
cd frontend && pnpm tsc --noEmit
```

Expected: 오류 없음. (`AGENTS.md` 절대 규칙 — `any` 금지, strict 모드)

- [ ] **Step 4: 모바일 뷰포트에서 확인**

```bash
cd frontend && pnpm dev
```

브라우저를 375px 폭으로 줄여 지표 8개가 겹치지 않고 읽히는지 확인한다.

- [ ] **Step 5: 커밋**

```bash
git add frontend/src/lib/metrics.ts frontend/src/app/analysis/
git commit -m "feat(ui): display all eight metrics with unmeasurable states"
```

---

## Task 16: 문서 갱신

**Files:**
- Modify: `docs/02_tech_stack.md` (AI 스택이 GPT-4o로 잘못 기재됨 — 실제는 Gemini)
- Modify: `docs/01_architecture.md` (데이터 흐름)
- Modify: `docs/06_data_schema.md` (지표 스키마)
- Modify: `docs/04_roadmap_7days.md` (체크박스 + 사실과 다른 항목 정정)
- Modify: `AGENTS.md` (TODO 두 건 해소 기록)

- [ ] **Step 1: 로드맵의 사실 오류 정정**

`docs/04_roadmap_7days.md`에서 다음 두 항목이 코드와 어긋난다 (스펙 §9.4):

| 기재 | 실제 |
|---|---|
| "6프레임 스킵 (기존 3프레임 → 2배 추가 단축)" | `SKIP = 2` |
| "최대 150프레임 처리 후 조기 종료" | 해당 로직이 존재하지 않음 |

전자는 "2프레임 스킵"으로 고치고, 후자는 체크박스를 `[ ]`로 되돌린다.

- [ ] **Step 2: 기술 스택 문서 정정**

`docs/02_tech_stack.md`의 "AI / ML" 표에서 `OpenAI API | GPT-4o` 행을 실제 사용 중인 Gemini로 바꾸고, `supervision 0.30.3` 행을 추가한다. "선택하지 않은 스택" 표의 `YOLOv8 Pose | 모델 용량 크고 MediaPipe 대비 추가 이점 없음` 행은 스펙 §2.2의 결정(ROI 탐지용으로 채택, 로컬 전용)에 맞게 고친다.

- [ ] **Step 3: 데이터 스키마 문서 갱신**

`docs/06_data_schema.md`에 지표 8개의 새 형태를 적는다:

```json
{
  "spine_angle": { "value": 35.2, "confidence": 0.91, "unit": "°", "measurable": true },
  "shoulder_rotation": { "value": null, "confidence": 0.0, "unit": "°", "measurable": false },
  "_meta": { "camera_angle": "face_on", "measured_count": 5, "total_count": 8 }
}
```

- [ ] **Step 4: 아키텍처 문서 갱신**

`docs/01_architecture.md`의 데이터 흐름에 `swing/` 패키지 분할과 규칙 엔진 → LLM 윤문 순서를 반영한다.

- [ ] **Step 5: `AGENTS.md`의 TODO 두 건 해소**

"포즈 추정 위치"는 **서버 유지로 확정**(스펙 §1), "LLM 호출 추상화"는 **`feedback/llm.py`가 `settings.GEMINI_API_KEY`를 먼저 읽도록 통일**(Task 14)되었다. 두 항목을 해소 상태로 고쳐 쓴다.

- [ ] **Step 6: 로드맵 체크박스 갱신**

Plan 1에서 완료한 항목에 `[x]`를 표시한다.

- [ ] **Step 7: 커밋**

```bash
git add docs/ AGENTS.md
git commit -m "docs: update stack, schema and roadmap for measured metrics"
```

---

## 자체 검토 결과

**1. 스펙 커버리지**

| 스펙 항목 | 담당 Task |
|---|---|
| §2.1 supervision 2D 제약 | Task 8 (world는 MediaPipe 직접, 픽셀은 supervision) |
| §2.2 모델 역할 분담 | Task 8, 11 |
| §2.3 YOLO ROI 크롭 | **Plan 1 범위 밖** — 아래 "이월" 참조 |
| §2.4 배포 경로 이원화 | **Plan 1 범위 밖** — 아래 "이월" 참조 |
| §3 지표 8개 계산 | Task 3, 4, 5, 6 |
| §3.1 2D 좌표 사용 이유 | Task 5 |
| §3.2 X-factor | Task 3 |
| §3.3 체중 이동 대리 지표 | Task 5, 13(라벨 "추정치"), 15 |
| §3.4 가짜 기본값 금지 | Task 7, 12 Step 6, 13 |
| §3.5 신뢰도 기록 | Task 7 `_confidence_for`, 15 `isLowConfidence` |
| §4.2 모듈 구조 | Task 1, 8, 10, 11, 12, 13, 14 |
| §4.3 규칙 엔진과 LLM 역전 | Task 13, 14 |
| §5 따라오는 변경 | Task 15, 16 |
| §6 축 방향 리스크 | Task 9 |
| §8 완료 기준(지표 실측화) | Task 7, 12, 14 Step 6 |

**이월 — Plan 1에 넣지 않은 것과 그 이유**

- **§2.3·§2.4 YOLO ROI 크롭**: torch 121MB를 끌어오는 선택적 최적화다. 지표가 실측으로 맞는지 먼저 확인하는 것이 순서이고, 이것 없이도 Plan 1은 완결된다. 스펙 §7의 5단계에 해당하며 **Plan 1이 끝난 뒤 별도 Task로 진행**한다.
- **§9 기기 간 흐름 전체**: Plan 2로 분리했다.
- **§9.4 `SKIP = 2` 가변 샘플링 재검토**: 스펙이 "§7 4단계에서 측정한 뒤 확정"이라고 정한 사항이다. Task 9의 실측 검증에서 프레임율 영향을 함께 재고, 값 변경은 Plan 2에서 다룬다.

**2. 플레이스홀더 점검** — "TBD"·"적절히 처리"·"위와 유사" 없음. 모든 코드 단계에 실제 코드가 들어 있다.

**3. 타입 일관성** — `MetricValue`·`PoseSequence`(Task 1)가 Task 7·8·12에서 같은 필드명으로 쓰인다. `metrics_to_json`(Task 7)의 출력 형태 `{value, confidence, unit, measurable}`가 Task 13 `evaluate`의 입력, Task 15 `MetricEntry`와 일치한다. `L_ELBOW`·`L_WRIST` 상수는 Task 10 Step 1에서 한 번만 추가하고 Task 11이 재사용한다.

