"""
swing/metrics.py — 포즈 좌표에서 골프 스윙 지표를 계산한다.

순수 함수만 둔다. numpy 외의 의존성을 추가하지 말 것.
그래야 실제 영상 없이 합성 좌표로 테스트할 수 있다.
"""
from __future__ import annotations

import math
from typing import Literal

import numpy as np

from app.services.swing.types import MetricValue, PoseSequence

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


# ── 2D 픽셀 지표 ──────────────────────────────────────────────────────────
# world 좌표는 힙 중심이 원점이라 몸 전체의 공간 이동이 상쇄된다.
# 아래 두 지표는 그래서 픽셀 좌표를 쓴다.
def head_movement_cm(xy_px: np.ndarray, addr_i: int, impact_i: int) -> float:
    """어드레스~임팩트 구간에서 머리가 움직인 최대 거리(cm).

    어드레스 프레임의 어깨 너비 픽셀을 SHOULDER_WIDTH_CM 에 대응시켜 환산한다.
    기준자를 만들 수 없으면 NaN.
    """
    addr = xy_px[addr_i]
    shoulder_px = float(
        np.linalg.norm(
            np.asarray(addr[R_SHOULDER], dtype=np.float64)
            - np.asarray(addr[L_SHOULDER], dtype=np.float64)
        )
    )
    if shoulder_px < 1e-6:
        return math.nan

    lo, hi = min(addr_i, impact_i), max(addr_i, impact_i)
    segment = np.asarray(xy_px[lo : hi + 1, NOSE], dtype=np.float64)
    displacement = float(np.linalg.norm(segment - segment[0], axis=1).max())
    return displacement * (SHOULDER_WIDTH_CM / shoulder_px)


def weight_shift_pct(xy_px: np.ndarray, addr_i: int, impact_i: int) -> float:
    """골반 중심의 좌우 이동량을 스탠스 폭 대비 %로 나타낸 대리 지표.

    영상만으로 실제 체중 배분은 측정할 수 없다. 이것은 추정치이며
    화면에도 그렇게 표시해야 한다.
    스탠스 폭이 0이면 NaN.
    """
    addr = xy_px[addr_i]
    impact = xy_px[impact_i]
    stance_px = abs(float(addr[L_ANKLE][0]) - float(addr[R_ANKLE][0]))
    if stance_px < 1e-6:
        return math.nan

    pelvis_addr = (float(addr[L_HIP][0]) + float(addr[R_HIP][0])) / 2.0
    pelvis_impact = (float(impact[L_HIP][0]) + float(impact[R_HIP][0])) / 2.0
    return abs(pelvis_impact - pelvis_addr) / stance_px * 100.0


# ── 템포 ──────────────────────────────────────────────────────────────────
def tempo_ratio(
    frame_indices: np.ndarray,
    fps: float,
    addr_i: int,
    top_i: int,
    impact_i: int,
) -> float:
    """백스윙 시간 ÷ 다운스윙 시간.

    배열 인덱스가 아니라 원본 프레임 번호와 fps로 실제 초를 구한다.
    프레임을 건너뛰며 샘플링하므로 인덱스 차이는 시간에 비례하지 않는다.
    어느 구간이든 길이가 0이면 NaN.
    """
    if fps <= 0.0:
        return math.nan
    t_addr = float(frame_indices[addr_i]) / fps
    t_top = float(frame_indices[top_i]) / fps
    t_impact = float(frame_indices[impact_i]) / fps

    backswing = t_top - t_addr
    downswing = t_impact - t_top
    if backswing <= 0.0 or downswing <= 0.0:
        return math.nan
    return backswing / downswing


# ── 촬영 각도별 계산 가능 지표 ─────────────────────────────────────────────
CameraAngle = Literal["down_the_line", "face_on"]

_BOTH = frozenset({"down_the_line", "face_on"})
_DTL = frozenset({"down_the_line"})
_FACE = frozenset({"face_on"})

METRIC_ANGLES: dict[str, frozenset[str]] = {
    "spine_angle": _BOTH,
    "knee_flex": _BOTH,
    "tempo_ratio": _BOTH,
    # 수평 회전은 깊이(z) 성분이 필요해 정면에서는 신뢰할 수 없다
    "shoulder_rotation": _DTL,
    "hip_rotation": _DTL,
    "x_factor": _DTL,
    # 좌우 이동은 정면에서만 화면에 드러난다
    "head_movement": _FACE,
    "weight_shift": _FACE,
}

# 물리적으로 말이 되는 범위. 벗어나면 값을 버리고 측정 실패로 돌린다.
#
# 촬영 각도를 잘못 고르면 게이팅을 통과해도 쓰레기 값이 나온다. 측면 영상에
# face_on 을 적용하면 어깨·발목이 화면상 겹쳐 분모(픽셀 거리)가 0에 가까워지고
# 환산 배율이 폭발한다. 실측에서 head_movement 141cm, weight_shift 281% 가 나왔다.
# 믿을 수 없는 값은 보여주지 않는 편이 낫다 — 가짜 기본값 금지와 같은 원칙이다.
# 상한은 사람 몸이 실제로 낼 수 있는 값을 기준으로 잡는다. 처음에 회전 상한을
# 180도로 뒀더니 어깨 148도·힙 105도짜리 결과가 그대로 통과했다. 사람 어깨는
# 최대 110도쯤 돌아간다. 상한이 헐거우면 검사가 있으나 마나다.
METRIC_LIMITS: dict[str, tuple[float, float]] = {
    "spine_angle": (0.0, 70.0),
    "knee_flex": (0.0, 70.0),
    "shoulder_rotation": (0.0, 120.0),  # 프로도 100도 안팎이다
    "hip_rotation": (0.0, 90.0),
    "x_factor": (-30.0, 90.0),
    "head_movement": (0.0, 30.0),  # 30cm 넘게 움직였다면 환산이 깨진 것이다
    "weight_shift": (0.0, 100.0),  # 골반이 스탠스 폭보다 더 갈 수는 없다
    "tempo_ratio": (0.5, 6.0),
}

METRIC_UNITS: dict[str, str] = {
    "spine_angle": "°",
    "knee_flex": "°",
    "tempo_ratio": ":1",
    "shoulder_rotation": "°",
    "hip_rotation": "°",
    "x_factor": "°",
    "head_movement": "cm",
    "weight_shift": "%",
}

# 각 지표가 어느 랜드마크를 쓰는지 — 신뢰도 계산에 쓴다
_METRIC_LANDMARKS: dict[str, tuple[int, ...]] = {
    "spine_angle": (L_SHOULDER, R_SHOULDER, L_HIP, R_HIP),
    "knee_flex": (L_HIP, R_HIP, L_KNEE, R_KNEE, L_ANKLE, R_ANKLE),
    "tempo_ratio": (),
    "shoulder_rotation": (L_SHOULDER, R_SHOULDER),
    "hip_rotation": (L_HIP, R_HIP),
    "x_factor": (L_SHOULDER, R_SHOULDER, L_HIP, R_HIP),
    "head_movement": (NOSE, L_SHOULDER, R_SHOULDER),
    "weight_shift": (L_HIP, R_HIP, L_ANKLE, R_ANKLE),
}

# 각 지표의 신뢰도를 어느 단계 프레임에서 잴 것인가
_METRIC_PHASES: dict[str, tuple[str, ...]] = {
    "spine_angle": ("address",),
    "knee_flex": ("address",),
    "tempo_ratio": ("address", "top", "impact"),
    "shoulder_rotation": ("address", "top"),
    "hip_rotation": ("address", "top"),
    "x_factor": ("address", "top"),
    "head_movement": ("address", "impact"),
    "weight_shift": ("address", "impact"),
}


def _confidence_for(
    name: str, seq: PoseSequence, phases: dict[str, int]
) -> float:
    """해당 지표가 쓰는 랜드마크들의 visibility 최솟값.

    랜드마크를 쓰지 않는 지표(tempo_ratio)는 1.0으로 둔다.
    """
    landmarks = _METRIC_LANDMARKS[name]
    if not landmarks:
        return 1.0
    values = [
        float(seq.visibility[phases[phase], lm])
        for phase in _METRIC_PHASES[name]
        if phase in phases
        for lm in landmarks
    ]
    return min(values) if values else 0.0


def compute_metrics(
    seq: PoseSequence,
    phases: dict[str, int],
    camera_angle: str,
) -> dict[str, MetricValue]:
    """포즈 시퀀스에서 지표 8개를 계산한다.

    반환 키는 촬영 각도와 무관하게 항상 8개다.
    계산할 수 없는 경우를 두 가지로 구분해 표현한다.
      - 촬영 각도상 불가         → MetricValue.unmeasurable
      - 각도는 맞지만 계산 실패  → MetricValue.failed

    어느 경우에도 숫자를 지어내지 않는다 (스펙 §3.4).
    """
    addr_i = phases["address"]
    top_i = phases["top"]
    impact_i = phases["impact"]

    def allowed(name: str) -> bool:
        return camera_angle in METRIC_ANGLES[name]

    raw: dict[str, float] = {}
    if allowed("shoulder_rotation"):
        raw["shoulder_rotation"] = shoulder_rotation(seq.world, addr_i, top_i)
    if allowed("hip_rotation"):
        raw["hip_rotation"] = hip_rotation(seq.world, addr_i, top_i)
    if allowed("x_factor"):
        s = raw.get("shoulder_rotation", math.nan)
        h = raw.get("hip_rotation", math.nan)
        raw["x_factor"] = (
            math.nan if math.isnan(s) or math.isnan(h) else x_factor(s, h)
        )
    if allowed("knee_flex"):
        raw["knee_flex"] = knee_flex(seq.world, addr_i)
    if allowed("spine_angle"):
        raw["spine_angle"] = spine_angle(seq.world, addr_i)
    if allowed("head_movement"):
        raw["head_movement"] = head_movement_cm(seq.xy_px, addr_i, impact_i)
    if allowed("weight_shift"):
        raw["weight_shift"] = weight_shift_pct(seq.xy_px, addr_i, impact_i)
    if allowed("tempo_ratio"):
        raw["tempo_ratio"] = tempo_ratio(
            seq.frame_indices, seq.fps, addr_i, top_i, impact_i
        )

    result: dict[str, MetricValue] = {}
    for name, unit in METRIC_UNITS.items():
        if not allowed(name):
            result[name] = MetricValue.unmeasurable(unit)
            continue
        value = raw.get(name, math.nan)
        if math.isnan(value) or math.isinf(value):
            result[name] = MetricValue.failed(unit)
            continue
        low, high = METRIC_LIMITS[name]
        if not (low <= value <= high):
            # 계산은 됐지만 물리적으로 불가능한 값이다. 믿을 수 없으므로 버린다.
            result[name] = MetricValue.failed(unit)
            continue
        result[name] = MetricValue(
            value=round(float(value), 2),
            confidence=round(_confidence_for(name, seq, phases), 3),
            unit=unit,
            measurable=True,
        )
    return result


def metrics_to_json(metrics: dict[str, MetricValue]) -> dict:
    """DB의 JSON 컬럼과 API 응답에 쓸 직렬화 형태.

    value 가 None 인 것도 그대로 담는다. 키를 빼면 소비하는 쪽에서
    다시 기본값을 채우려는 유혹이 생긴다.
    """
    return {
        name: {
            "value": m.value,
            "confidence": m.confidence,
            "unit": m.unit,
            "measurable": m.measurable,
        }
        for name, m in metrics.items()
    }
