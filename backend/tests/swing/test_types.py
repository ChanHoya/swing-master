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
