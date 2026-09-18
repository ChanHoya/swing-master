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
