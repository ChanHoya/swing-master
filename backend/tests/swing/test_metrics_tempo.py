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
    assert tempo_ratio(
        frame_indices, fps=30.0, addr_i=0, top_i=1, impact_i=2
    ) == pytest.approx(3.0)


def test_tempo_ratio_is_nan_when_downswing_has_no_duration():
    """탑과 임팩트가 같은 프레임이면 비율이 정의되지 않는다. 3.0을 지어내지 않는다."""
    frame_indices = np.array([0, 60, 60], dtype=np.int32)
    assert math.isnan(
        tempo_ratio(frame_indices, fps=60.0, addr_i=0, top_i=1, impact_i=2)
    )


def test_tempo_ratio_is_nan_when_backswing_has_no_duration():
    frame_indices = np.array([60, 60, 90], dtype=np.int32)
    assert math.isnan(
        tempo_ratio(frame_indices, fps=60.0, addr_i=0, top_i=1, impact_i=2)
    )


def test_tempo_ratio_is_nan_when_fps_is_invalid():
    frame_indices = np.array([0, 60, 90], dtype=np.int32)
    assert math.isnan(
        tempo_ratio(frame_indices, fps=0.0, addr_i=0, top_i=1, impact_i=2)
    )
