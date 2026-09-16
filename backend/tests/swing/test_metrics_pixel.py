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
