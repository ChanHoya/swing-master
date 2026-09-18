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
    assert rotation_between(
        world[0], world[1], L_SHOULDER, R_SHOULDER
    ) == pytest.approx(80.0, abs=1e-3)


def test_rotation_between_wraps_past_half_turn():
    """170도에서 -170도로 간 것은 20도 회전이지 340도가 아니다."""
    world = _blank_world()
    _set_pair(world, 0, L_SHOULDER, R_SHOULDER, 170.0)
    _set_pair(world, 1, L_SHOULDER, R_SHOULDER, -170.0)
    assert rotation_between(
        world[0], world[1], L_SHOULDER, R_SHOULDER
    ) == pytest.approx(20.0, abs=1e-3)


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
