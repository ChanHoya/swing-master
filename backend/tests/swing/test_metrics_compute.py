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
