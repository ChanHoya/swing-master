import numpy as np
import pytest

from app.services.swing.metrics import L_SHOULDER, L_WRIST, R_SHOULDER, R_WRIST
from app.services.swing.phases import detect_phases
from app.services.swing.types import PHASE_KEYS, PoseSequence


def _wrist_height(f: int, frames: int) -> float:
    """실제 스윙에 가까운 손목 높이(픽셀, 작을수록 위).

    어드레스에서 잠시 멈추고, 천천히 올라가 탑에서 다시 멈추고,
    빠르게 내려와 임팩트를 지나 감속한다.
    """
    t = f / max(1, frames - 1)
    if t < 0.12:  # 어드레스 — 정지
        return 700.0
    if t < 0.45:  # 백스윙 — 느리게 상승
        return 700.0 - (t - 0.12) / 0.33 * 400.0
    if t < 0.55:  # 탑 — 전환 구간의 정지
        return 300.0
    if t < 0.70:  # 다운스윙 — 빠르게 하강
        return 300.0 + (t - 0.55) / 0.15 * 400.0
    return 700.0 - (t - 0.70) / 0.30 * 250.0  # 팔로우스루 — 감속


def _swing_sequence(frames: int = 40) -> PoseSequence:
    """어드레스 정지 → 백스윙 → 탑 정지 → 다운스윙 → 피니시."""
    xy = np.zeros((frames, 33, 2), dtype=np.float32)
    world = np.zeros((frames, 33, 3), dtype=np.float32)
    for f in range(frames):
        wrist_y = _wrist_height(f, frames)
        xy[f, L_WRIST] = (500.0, wrist_y)
        xy[f, R_WRIST] = (510.0, wrist_y)
        xy[f, L_SHOULDER] = (450.0, 400.0)
        xy[f, R_SHOULDER] = (550.0, 400.0)
    return PoseSequence(
        world=world,
        xy_px=xy,
        visibility=np.full((frames, 33), 0.9, dtype=np.float32),
        frame_indices=np.arange(frames, dtype=np.int32),
        fps=60.0,
        resolution_wh=(1000, 1000),
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


def test_top_is_near_where_wrist_is_highest():
    """탑에서 손목 y(픽셀)가 가장 작아야 한다."""
    seq = _swing_sequence(40)
    phases = detect_phases(seq)
    wrist_y = seq.xy_px[:, R_WRIST, 1]
    assert abs(phases["top"] - int(np.argmin(wrist_y))) <= 5


def test_raises_when_sequence_too_short():
    with pytest.raises(ValueError, match="프레임"):
        detect_phases(_swing_sequence(2))


def test_minimum_viable_sequence_still_yields_ordered_phases():
    """4프레임은 하한선이다. 여기서도 단조 증가가 깨지면 안 된다."""
    phases = detect_phases(_swing_sequence(4))
    order = [phases[k] for k in PHASE_KEYS]
    assert order == sorted(order)
    assert max(order) <= 3


def _sequence_with_preamble(frames: int = 60, preamble: int = 20) -> PoseSequence:
    """스윙 앞에 잡움직임(걸어 들어오기·연습 스윙)이 붙은 시퀀스.

    실제 영상 3개가 이 모양 때문에 실패했다. address 를 앞에서부터 찾으면
    그 잡움직임을 스윙 시작으로 오인해 스윙 길이가 6~13초로 부풀었다.
    """
    xy = np.zeros((frames, 33, 2), dtype=np.float32)
    swing_len = frames - preamble
    for f in range(frames):
        if f < preamble:
            # 잡움직임: 손목이 오르내리지만 스윙은 아니다
            wrist_y = 650.0 + (30.0 if f % 4 < 2 else -30.0)
        else:
            wrist_y = _wrist_height(f - preamble, swing_len)
        xy[f, L_WRIST] = (500.0, wrist_y)
        xy[f, R_WRIST] = (510.0, wrist_y)
        xy[f, L_SHOULDER] = (450.0, 400.0)
        xy[f, R_SHOULDER] = (550.0, 400.0)
    return PoseSequence(
        world=np.zeros((frames, 33, 3), dtype=np.float32),
        xy_px=xy,
        visibility=np.full((frames, 33), 0.9, dtype=np.float32),
        frame_indices=np.arange(frames, dtype=np.int32),
        fps=30.0,
        resolution_wh=(1000, 1000),
    )


def test_address_is_not_dragged_to_the_start_by_preamble_motion():
    """스윙 앞의 잡움직임을 어드레스로 오인하면 안 된다.

    어드레스는 백스윙 직전의 마지막 정지다. 영상 맨 앞이 아니다.
    """
    seq = _sequence_with_preamble(frames=60, preamble=20)
    phases = detect_phases(seq)
    assert phases["address"] >= 12, (
        f"어드레스가 {phases['address']} 로 잡혔다 — 잡움직임 구간(0~19)에 끌려갔다"
    )


def test_swing_duration_stays_physically_plausible():
    """어드레스~피니시가 실제 스윙 길이여야 한다.

    골프 스윙은 1~3초다. 6초가 넘으면 스윙이 아닌 구간을 포함한 것이다.
    """
    seq = _sequence_with_preamble(frames=60, preamble=20)
    phases = detect_phases(seq)
    fi = seq.frame_indices
    duration = (fi[phases["finish"]] - fi[phases["address"]]) / seq.fps
    assert 0.5 <= duration <= 3.5, f"스윙 길이 {duration:.2f}초 — 물리적으로 부적절"
