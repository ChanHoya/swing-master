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
