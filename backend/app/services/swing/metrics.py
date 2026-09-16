"""
swing/metrics.py — 포즈 좌표에서 골프 스윙 지표를 계산한다.

순수 함수만 둔다. numpy 외의 의존성을 추가하지 말 것.
그래야 실제 영상 없이 합성 좌표로 테스트할 수 있다.
"""
from __future__ import annotations

import math

import numpy as np

# ── MediaPipe BlazePose 33점 인덱스 ────────────────────────────────────────
NOSE = 0
L_SHOULDER, R_SHOULDER = 11, 12
L_ELBOW, R_ELBOW = 13, 14
L_WRIST, R_WRIST = 15, 16
L_HIP, R_HIP = 23, 24
L_KNEE, R_KNEE = 25, 26
L_ANKLE, R_ANKLE = 27, 28

# 성인 평균 어깨 너비. 픽셀 → cm 환산의 기준자로 쓴다.
SHOULDER_WIDTH_CM: float = 40.0


def wrap_deg(deg: float) -> float:
    """각도를 [-180, 180] 범위로 정규화한다.

    나머지 연산만 쓰면 180도가 -180도로 떨어진다. 같은 각도이긴 하지만
    계약이 180을 포함한다고 해 놓고 못 돌려주면 읽는 쪽이 헷갈리므로
    경계값만 양수로 맞춘다.
    """
    wrapped = (deg + 180.0) % 360.0 - 180.0
    return 180.0 if wrapped == -180.0 else wrapped


def horizontal_angle(p_left: np.ndarray, p_right: np.ndarray) -> float:
    """두 3D 점을 잇는 벡터를 수평면(x-z)에 투영한 각도(도).

    y(상하) 성분은 무시한다. 몸통의 좌우 회전만 보기 위해서다.
    """
    dx = float(p_right[0] - p_left[0])
    dz = float(p_right[2] - p_left[2])
    return math.degrees(math.atan2(dz, dx))


def angle_at(a: np.ndarray, b: np.ndarray, c: np.ndarray) -> float:
    """b를 꼭짓점으로 하는 a-b-c 사이각(도), 0~180.

    벡터 길이가 0이면 각도가 정의되지 않으므로 NaN을 반환한다.
    0을 반환하면 "완전히 접힌 관절"로 오독되므로 그렇게 하지 않는다.
    """
    v1 = np.asarray(a, dtype=np.float64) - np.asarray(b, dtype=np.float64)
    v2 = np.asarray(c, dtype=np.float64) - np.asarray(b, dtype=np.float64)
    n1 = float(np.linalg.norm(v1))
    n2 = float(np.linalg.norm(v2))
    if n1 == 0.0 or n2 == 0.0:
        return math.nan
    cos = float(np.dot(v1, v2)) / (n1 * n2)
    return math.degrees(math.acos(max(-1.0, min(1.0, cos))))


# ── 회전 지표 ──────────────────────────────────────────────────────────────
def _is_degenerate_pair(frame: np.ndarray, idx_left: int, idx_right: int) -> bool:
    """좌우 랜드마크가 사실상 겹쳐 방향을 정의할 수 없는가."""
    v = np.asarray(frame[idx_right], dtype=np.float64) - np.asarray(
        frame[idx_left], dtype=np.float64
    )
    return float(math.hypot(v[0], v[2])) < 1e-9


def rotation_between(
    world_ref: np.ndarray,
    world_target: np.ndarray,
    idx_left: int,
    idx_right: int,
) -> float:
    """기준 프레임 대비 목표 프레임의 수평 회전량(도), 0~180.

    좌타·우타에 따라 부호가 반대이므로 크기만 돌려준다.
    방향을 정의할 수 없으면 NaN.
    """
    if _is_degenerate_pair(world_ref, idx_left, idx_right) or _is_degenerate_pair(
        world_target, idx_left, idx_right
    ):
        return math.nan
    a0 = horizontal_angle(world_ref[idx_left], world_ref[idx_right])
    a1 = horizontal_angle(world_target[idx_left], world_target[idx_right])
    return abs(wrap_deg(a1 - a0))


def shoulder_rotation(world: np.ndarray, addr_i: int, top_i: int) -> float:
    """어드레스 대비 탑에서의 어깨 회전량(도)."""
    return rotation_between(world[addr_i], world[top_i], L_SHOULDER, R_SHOULDER)


def hip_rotation(world: np.ndarray, addr_i: int, top_i: int) -> float:
    """어드레스 대비 탑에서의 힙 회전량(도)."""
    return rotation_between(world[addr_i], world[top_i], L_HIP, R_HIP)


def x_factor(shoulder_deg: float, hip_deg: float) -> float:
    """어깨와 힙 회전의 차이. 골프에서 비거리를 결정하는 핵심 지표.

    힙이 어깨보다 더 돌아간 비정상 스윙에서는 음수가 나온다.
    실제로 일어나는 일이므로 0으로 깎지 않는다.
    """
    return shoulder_deg - hip_deg


# ── 자세 지표 ──────────────────────────────────────────────────────────────
def knee_flex(world: np.ndarray, addr_i: int) -> float:
    """어드레스에서의 무릎 굴곡각(도), 좌우 평균. 곧게 펴면 0.

    힙-무릎-발목 사이각의 여각이다. 한쪽이라도 계산 불가면 NaN.
    """
    frame = world[addr_i]
    left = angle_at(frame[L_HIP], frame[L_KNEE], frame[L_ANKLE])
    right = angle_at(frame[R_HIP], frame[R_KNEE], frame[R_ANKLE])
    if math.isnan(left) or math.isnan(right):
        return math.nan
    return ((180.0 - left) + (180.0 - right)) / 2.0


def spine_angle(world: np.ndarray, addr_i: int) -> float:
    """어드레스에서 척추가 수직 대비 앞으로 기운 각도(도).

    MediaPipe world 좌표는 y축 아래가 양수라 어깨는 힙보다 y가 작다.
    부호에 의존하지 않도록 수직 성분은 절댓값으로 쓴다.
    """
    frame = world[addr_i]
    shoulder_c = (
        np.asarray(frame[L_SHOULDER], dtype=np.float64)
        + np.asarray(frame[R_SHOULDER], dtype=np.float64)
    ) / 2.0
    hip_c = (
        np.asarray(frame[L_HIP], dtype=np.float64)
        + np.asarray(frame[R_HIP], dtype=np.float64)
    ) / 2.0
    v = shoulder_c - hip_c
    if float(np.linalg.norm(v)) < 1e-9:
        return math.nan
    horizontal = math.hypot(float(v[0]), float(v[2]))
    return math.degrees(math.atan2(horizontal, abs(float(v[1]))))
