import numpy as np
import pytest

from app.services.swing.pose import landmarks_from_result


class _LM:
    """mediapipe 의 NormalizedLandmark / Landmark 를 흉내 낸다."""

    def __init__(self, x, y, z=0.0, visibility=0.9):
        self.x, self.y, self.z, self.visibility = x, y, z, visibility
        self.presence = 1.0


class _Result:
    def __init__(self, pose_landmarks, pose_world_landmarks):
        self.pose_landmarks = pose_landmarks
        self.pose_world_landmarks = pose_world_landmarks


def _make_result(n=33):
    norm = [_LM(0.5, 0.4, 0.0, 0.8) for _ in range(n)]
    world = [_LM(0.1, -0.2, 0.3, 0.8) for _ in range(n)]
    return _Result([norm], [world])


def test_returns_none_when_no_pose_detected():
    assert landmarks_from_result(_Result([], []), (1280, 720)) is None


def test_returns_none_when_world_landmarks_missing():
    """world 좌표가 없으면 지표 6개를 계산할 수 없으므로 실패로 본다."""
    norm = [_LM(0.5, 0.4) for _ in range(33)]
    assert landmarks_from_result(_Result([norm], []), (1280, 720)) is None


def test_world_landmarks_are_kept_in_metres():
    world, _, _ = landmarks_from_result(_make_result(), (1280, 720))
    assert world.shape == (33, 3)
    assert world[0] == pytest.approx([0.1, -0.2, 0.3], abs=1e-5)


def test_pixel_coordinates_are_scaled_by_resolution():
    """0.5 × 1280 = 640,  0.4 × 720 = 288"""
    _, xy_px, _ = landmarks_from_result(_make_result(), (1280, 720))
    assert xy_px.shape == (33, 2)
    assert xy_px[0] == pytest.approx([640.0, 288.0], abs=1e-3)


def test_visibility_is_extracted():
    _, _, vis = landmarks_from_result(_make_result(), (1280, 720))
    assert vis.shape == (33,)
    assert vis[0] == pytest.approx(0.8, abs=1e-5)
