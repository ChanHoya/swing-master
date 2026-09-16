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
