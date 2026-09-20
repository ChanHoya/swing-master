"""손 궤적 추출 테스트.

이 모듈의 존재 이유는 "손목 좌표를 그대로 쓰면 안 된다" 이므로,
테스트도 대부분 망가진 랜드마크를 걸러내는지를 본다.
"""
from __future__ import annotations

import numpy as np
import pytest

from app.services.swing import tracks
from app.services.swing.tracks import (
    L_ELBOW,
    L_SHOULDER,
    L_WRIST,
    R_ELBOW,
    R_SHOULDER,
    R_WRIST,
    build_tracks,
)
from app.services.swing.types import PoseSequence

# 기준 체격. 어깨폭 80px, 팔뚝 50px 로 둔다.
SHOULDER_W = 80.0
FOREARM = 50.0


def make_seq(
    hand_xy: list[tuple[float, float]],
    *,
    visibility: np.ndarray | None = None,
    overrides: dict[int, dict[int, tuple[float, float]]] | None = None,
    resolution_wh: tuple[int, int] = (640, 640),
    fps: float = 30.0,
    skip: int = 2,
) -> PoseSequence:
    """양손이 그립 위에 나란히 있는 정상 시퀀스를 만든다.

    overrides 로 특정 프레임의 특정 랜드마크만 망가뜨릴 수 있다.
    """
    frames = len(hand_xy)
    xy = np.zeros((frames, 33, 2), dtype=np.float32)
    for i, (hx, hy) in enumerate(hand_xy):
        xy[i, L_SHOULDER] = [hx - SHOULDER_W / 2, hy - 100.0]
        xy[i, R_SHOULDER] = [hx + SHOULDER_W / 2, hy - 100.0]
        # 양 손목은 그립에서 10px 간격, 팔꿈치는 그 위로 팔뚝 길이만큼.
        xy[i, L_WRIST] = [hx - 5.0, hy]
        xy[i, R_WRIST] = [hx + 5.0, hy]
        xy[i, L_ELBOW] = [hx - 5.0, hy - FOREARM]
        xy[i, R_ELBOW] = [hx + 5.0, hy - FOREARM]
    for frame, items in (overrides or {}).items():
        for landmark, value in items.items():
            xy[frame, landmark] = value

    vis = np.ones((frames, 33), dtype=np.float32) if visibility is None else visibility
    return PoseSequence(
        world=np.zeros((frames, 33, 3), dtype=np.float32),
        xy_px=xy,
        visibility=vis,
        frame_indices=np.arange(frames, dtype=np.int32) * skip,
        fps=fps,
        resolution_wh=resolution_wh,
    )


def straight_line(frames: int) -> list[tuple[float, float]]:
    """오른쪽 아래에서 왼쪽 위로 곧게 올라가는 손 경로."""
    return [(300.0 - i * 4.0, 400.0 - i * 4.0) for i in range(frames)]


def test_정상_시퀀스는_매끄러운_궤적을_돌려준다():
    hands = build_tracks(make_seq(straight_line(20)))["hands"]

    assert len(hands) > 0
    # 재표본화 주기대로 촘촘해진다. 원본 20프레임보다 점이 많다.
    assert len(hands) > 20
    # 시간은 단조 증가한다.
    assert all(hands[i][0] < hands[i + 1][0] for i in range(len(hands) - 1))
    # 좌표는 0~1 정규화다.
    assert all(0.0 <= p[1] <= 1.0 and 0.0 <= p[2] <= 1.0 for p in hands)


def test_손목이_팔꿈치에_붙은_프레임은_버린다():
    # 실측에서 나온 고장 — 정상 팔뚝 50px 인데 10px 로 잡혔다.
    frames = 20
    broken = 10
    seq = make_seq(
        straight_line(frames),
        overrides={
            broken: {
                L_WRIST: (300.0 - broken * 4.0 - 5.0, 400.0 - broken * 4.0 - FOREARM + 10.0),
                R_WRIST: (300.0 - broken * 4.0 + 5.0, 400.0 - broken * 4.0 - FOREARM + 10.0),
            }
        },
    )
    hands = build_tracks(seq)["hands"]

    # 그 프레임이 버려져도 앞뒤가 이어지므로 궤적 자체는 남는다.
    assert len(hands) > 0
    # 팔꿈치 높이로 튀어오른 점이 궤적에 없다. 버려진 프레임의 손 y 는 366,
    # 팔꿈치로 붙으면 326 이 된다. 보간된 값은 그 사이로 가지 않는다.
    ys = [p[2] * 640 for p in hands]
    assert min(ys) > 400.0 - (frames - 1) * 4.0 - 5.0


def test_양_손목이_멀면_중점을_쓰지_않는다():
    # 한쪽 손목만 엉뚱한 곳으로 날아간 경우. 중점을 쓰면 아무 데도 아닌
    # 한가운데가 되므로 잘 보이는 쪽 하나만 써야 한다.
    frames = 12
    bad = 6
    vis = np.ones((frames, 33), dtype=np.float32)
    vis[bad, R_WRIST] = 0.4  # 왼쪽(1.0)보다 낮으므로 왼쪽이 선택돼야 한다
    seq = make_seq(
        straight_line(frames),
        visibility=vis,
        overrides={bad: {R_WRIST: (300.0 - bad * 4.0 + 200.0, 400.0 - bad * 4.0)}},
    )
    hands = build_tracks(seq)["hands"]

    # 오른쪽으로 크게 끌려간 점이 없다. 정상 경로의 최대 x 는 300 근처다.
    xs = [p[1] * 640 for p in hands]
    assert max(xs) < 320.0


def test_양손_모두_안_보이는_프레임은_건너뛴다():
    frames = 20
    vis = np.ones((frames, 33), dtype=np.float32)
    vis[10, L_WRIST] = 0.0
    vis[10, R_WRIST] = 0.0

    hands = build_tracks(make_seq(straight_line(frames), visibility=vis))["hands"]

    # 공백이 짧으므로 이어 붙는다. 궤적은 끊기지 않는다.
    assert len(hands) > 0
    gaps = [hands[i + 1][0] - hands[i][0] for i in range(len(hands) - 1)]
    assert max(gaps) < tracks.MAX_GAP_SEC


def test_공백이_길면_궤적을_끊는다():
    # 가운데를 통째로 못 본 경우. 없는 구간을 직선으로 메우면 창작이다.
    frames = 30
    vis = np.ones((frames, 33), dtype=np.float32)
    for f in range(10, 22):  # 12프레임 = 0.8초 공백
        vis[f, L_WRIST] = 0.0
        vis[f, R_WRIST] = 0.0

    hands = build_tracks(make_seq(straight_line(frames), visibility=vis))["hands"]

    gaps = [hands[i + 1][0] - hands[i][0] for i in range(len(hands) - 1)]
    assert max(gaps) > tracks.MAX_GAP_SEC  # 끊긴 자리가 남아 있다


def test_화면_밖으로_튄_좌표는_버린다():
    frames = 12
    seq = make_seq(
        straight_line(frames),
        overrides={5: {L_WRIST: (5000.0, 180.0), R_WRIST: (5010.0, 180.0)}},
    )
    xs = [p[1] for p in build_tracks(seq)["hands"]]

    assert xs and max(xs) <= 1.1


def test_해상도가_비어_있으면_빈_궤적():
    seq = make_seq(straight_line(10), resolution_wh=(0, 0))

    assert build_tracks(seq)["hands"] == []


def test_점이_모자라면_빈_궤적():
    assert build_tracks(make_seq(straight_line(1)))["hands"] == []


def test_NaN_좌표는_버린다():
    frames = 12
    seq = make_seq(
        straight_line(frames),
        overrides={5: {L_WRIST: (np.nan, np.nan), R_WRIST: (np.nan, np.nan)}},
    )
    hands = build_tracks(seq)["hands"]

    assert hands
    assert all(np.isfinite(p[1]) and np.isfinite(p[2]) for p in hands)


# ── 빠른 원호 구간의 보간 ──────────────────────────────────────────────────
#
# 임팩트 부근은 모션 블러로 손목 랜드마크가 무너져 프레임이 버려진다. 그
# 판단 자체는 옳지만, 버린 자리를 직선으로 이으면 원호의 현을 가로질러
# 안쪽으로 파고든다. 스윙에서 가장 빠르고 가장 많이 휘는 구간이라 이탈이
# 크고, 원호 안쪽에는 팔꿈치가 있어 "궤적이 팔꿈치로 올라간다"로 보인다.
#
# 실측: 채택된 프레임 위의 점은 손목에서 평균 4px, 보간으로 만든 점은 12.5px.
import math as _math

import numpy as _np

from app.services.swing.tracks import resample_path


def _arc(n: int, start: float = _math.pi, end: float = 0.0):
    """반지름 1, 중심 원점인 반원 위의 점 n개와 그 시각."""
    angles = _np.linspace(start, end, n)
    times = _np.linspace(0.0, 1.0, n)
    return list(times), [(float(_math.cos(a)), float(_math.sin(a))) for a in angles]


def _max_radius_error(points) -> float:
    """원호에서 얼마나 벗어났는가. 현을 가로지르면 반지름이 1보다 작아진다."""
    return max(abs(_math.hypot(x, y) - 1.0) for _, x, y in points)


def test_interpolation_follows_the_arc_across_a_gap():
    """구멍이 뚫린 원호를 이을 때 현을 가로지르면 안 된다."""
    times, pts = _arc(13)
    # 한가운데 세 점을 지운다 — 임팩트 부근에서 프레임이 버려지는 상황.
    keep = [i for i in range(13) if i not in (5, 6, 7)]
    gapped_t = [times[i] for i in keep]
    gapped_p = [pts[i] for i in keep]

    filled = resample_path(gapped_t, gapped_p, hz=60.0)

    # 같은 구멍을 직선으로 이었을 때와 견준다. 절대값을 못박으면 기준이
    # 임의가 되므로, 실제로 고친 성질 — 현이 아니라 호를 따르는가 — 을 본다.
    grid = _np.arange(gapped_t[0], gapped_t[-1], 1.0 / 60.0)
    arr = _np.asarray(gapped_p)
    linear = [
        (0.0, float(x), float(y))
        for x, y in zip(
            _np.interp(grid, gapped_t, arr[:, 0]),
            _np.interp(grid, gapped_t, arr[:, 1]),
        )
    ]
    assert _max_radius_error(filled) < _max_radius_error(linear) * 0.7


def test_interpolation_is_exact_when_nothing_is_missing():
    """구멍이 없으면 원래 점을 충실히 따라야 한다."""
    times, pts = _arc(25)
    filled = resample_path(times, pts, hz=60.0)
    assert _max_radius_error(filled) < 0.02


def test_interpolation_does_not_overshoot_a_straight_line():
    """곡선 보간이 직선 구간에서 출렁이면 안 된다."""
    times = [i / 10.0 for i in range(11)]
    pts = [(t, 0.0) for t in times]
    filled = resample_path(times, pts, hz=60.0)
    assert max(abs(y) for _, _, y in filled) < 1e-6


def test_two_points_still_produce_a_path():
    """점이 둘뿐이면 직선 말고는 그릴 것이 없다. 죽지는 말아야 한다."""
    assert len(resample_path([0.0, 0.5], [(0.0, 0.0), (1.0, 1.0)], hz=30.0)) >= 2


# ── 손목 붕괴와 단축(foreshortening) 구분 ─────────────────────────────────
#
# 팔뚝의 절대 픽셀 길이로는 둘을 못 가른다. 팔이 카메라 쪽을 향하면 팔뚝이
# 짧게 보이지만 손목은 제자리에 있고, 손목이 팔꿈치로 미끄러지면 역시 짧게
# 보인다. 실측에서 이 혼동으로 멀쩡한 프레임이 버려졌고(비율 0.64인데 절대
# 길이가 임계값에 1px 모자람), 그 구멍을 보간이 메우며 궤적이 원호 안쪽으로
# 파고들었다.
#
# 위팔(어깨→팔꿈치)은 함께 단축되므로 비율은 유지된다. 실측 팔뚝/위팔
# 중앙값은 어깨폭 59px 영상에서 0.92, 17px 영상에서 0.88 이었다.
from app.services.swing.tracks import forearm_is_collapsed


def test_collapsed_wrist_is_rejected():
    """손목이 팔꿈치에 붙으면 팔뚝만 짧아지고 위팔은 그대로다."""
    assert forearm_is_collapsed(forearm=3.0, upper_arm=45.0) is True
    assert forearm_is_collapsed(forearm=18.0, upper_arm=42.0) is True


def test_foreshortened_arm_is_kept():
    """팔 전체가 카메라를 향하면 둘 다 짧아진다. 손목은 멀쩡하다."""
    assert forearm_is_collapsed(forearm=16.0, upper_arm=18.0) is False
    assert forearm_is_collapsed(forearm=25.0, upper_arm=39.0) is False


def test_normal_arm_is_kept():
    assert forearm_is_collapsed(forearm=42.0, upper_arm=46.0) is False


def test_unusable_measurements_are_not_treated_as_collapse():
    """위팔을 못 재면 판단 근거가 없다. 멀쩡한 프레임을 버리지 않는다."""
    assert forearm_is_collapsed(forearm=40.0, upper_arm=0.0) is False
    assert forearm_is_collapsed(forearm=float("nan"), upper_arm=45.0) is False
