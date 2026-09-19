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
