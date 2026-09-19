"""손 궤적 추출 테스트.

핵심 규칙은 metrics 와 같다 — 보이지 않은 프레임에 값을 지어내지 않는다.
"""
from __future__ import annotations

import numpy as np
import pytest

from app.services.swing.tracks import L_WRIST, R_WRIST, build_tracks
from app.services.swing.types import PoseSequence


def make_seq(
    xy: np.ndarray,
    visibility: np.ndarray,
    resolution_wh: tuple[int, int] = (640, 360),
    fps: float = 30.0,
) -> PoseSequence:
    frames = xy.shape[0]
    return PoseSequence(
        world=np.zeros((frames, 33, 3), dtype=np.float32),
        xy_px=xy,
        visibility=visibility,
        frame_indices=np.arange(frames, dtype=np.int32) * 2,
        fps=fps,
        resolution_wh=resolution_wh,
    )


def base_xy(frames: int) -> np.ndarray:
    return np.zeros((frames, 33, 2), dtype=np.float32)


def test_두_손목의_중점을_정규화해_돌려준다():
    xy = base_xy(2)
    xy[:, L_WRIST] = [100.0, 90.0]
    xy[:, R_WRIST] = [220.0, 90.0]
    vis = np.ones((2, 33), dtype=np.float32)

    hands = build_tracks(make_seq(xy, vis))["hands"]

    assert len(hands) == 2
    # 중점 x=160 → 160/640=0.25, y=90 → 90/360=0.25
    assert hands[0][1] == pytest.approx(0.25)
    assert hands[0][2] == pytest.approx(0.25)
    # frame_indices 가 0,2 이고 fps=30 이므로 두 번째 점은 2/30초다.
    assert hands[0][0] == pytest.approx(0.0)
    assert hands[1][0] == pytest.approx(2 / 30, abs=1e-3)


def test_한쪽만_보이면_보이는_쪽을_쓴다():
    xy = base_xy(1)
    xy[:, L_WRIST] = [64.0, 36.0]
    xy[:, R_WRIST] = [576.0, 324.0]  # 가려진 쪽. 섞이면 중점이 한가운데로 간다.
    vis = np.zeros((1, 33), dtype=np.float32)
    vis[:, L_WRIST] = 0.9

    hands = build_tracks(make_seq(xy, vis))["hands"]

    assert len(hands) == 1
    assert hands[0][1] == pytest.approx(0.1)
    assert hands[0][2] == pytest.approx(0.1)


def test_양손_모두_안_보이는_프레임은_건너뛴다():
    xy = base_xy(3)
    xy[:, L_WRIST] = [320.0, 180.0]
    xy[:, R_WRIST] = [320.0, 180.0]
    vis = np.ones((3, 33), dtype=np.float32)
    vis[1, L_WRIST] = 0.0
    vis[1, R_WRIST] = 0.0

    hands = build_tracks(make_seq(xy, vis))["hands"]

    # 가운데 프레임이 빠지고 앞뒤만 남는다. 값을 채워 메우지 않는다.
    assert len(hands) == 2
    assert [h[0] for h in hands] == pytest.approx([0.0, 4 / 30], abs=1e-3)


def test_화면_밖으로_튄_좌표는_버린다():
    xy = base_xy(2)
    xy[0, L_WRIST] = xy[0, R_WRIST] = [320.0, 180.0]
    xy[1, L_WRIST] = xy[1, R_WRIST] = [5000.0, 180.0]  # 오검출
    vis = np.ones((2, 33), dtype=np.float32)

    hands = build_tracks(make_seq(xy, vis))["hands"]

    assert len(hands) == 1


def test_해상도가_비어_있으면_빈_궤적():
    xy = base_xy(1)
    vis = np.ones((1, 33), dtype=np.float32)

    assert build_tracks(make_seq(xy, vis, resolution_wh=(0, 0)))["hands"] == []


def test_NaN_좌표는_버린다():
    xy = base_xy(2)
    xy[0, L_WRIST] = xy[0, R_WRIST] = [320.0, 180.0]
    xy[1, L_WRIST] = xy[1, R_WRIST] = [np.nan, np.nan]
    vis = np.ones((2, 33), dtype=np.float32)

    assert len(build_tracks(make_seq(xy, vis))["hands"]) == 1
