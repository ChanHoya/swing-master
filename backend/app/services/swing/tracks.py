"""
swing/tracks.py — 프레임별 손 궤적.

지표(metrics)가 "한 순간의 각도"라면 궤적은 "시간에 따른 경로"다.
영상 위에 겹쳐 그리려고 만드는 것이라 좌표를 0~1 로 정규화해 내보낸다.
그래야 프론트가 재생 화면 크기·레터박스를 모르는 채로도 픽셀로 환산할 수 있다.

## 왜 그냥 손목 좌표를 쓰지 않는가

MediaPipe 의 손목 랜드마크는 스윙 중에 두 가지로 무너진다.

1. **손목이 팔꿈치에 붙는다.** 실측한 영상에서 정상 팔뚝이 50px 인데
   다운스윙·임팩트 구간에서 10~17px 로 잡혔다. 모션 블러가 심한 구간에서
   손목 랜드마크가 팔꿈치 위로 미끄러진 것이다.
2. **좌우 손목 사이를 건너뛴다.** 가시성만 보고 "양손 중점 / 한쪽 손목"을
   고르면, 가시성이 임계값을 오갈 때마다 점이 튄다. 실측에서 이 전환이
   5회 일어났고 한 번에 최대 87px(어깨폭 78.5px 보다 크다) 움직였다.

그래서 좌표를 그대로 쓰지 않고 세 단계로 거른다.

- **팔뚝 길이 검사** — 그 사람의 팔뚝 길이 중앙값보다 크게 짧으면 버린다.
- **그립 간격 검사** — 양손은 한 그립을 잡고 있으니 서로 가까워야 한다.
  멀리 떨어져 있으면 둘 중 하나가 틀린 것이므로 중점을 쓰지 않는다.
- **재표본화 + 이동평균** — 남은 점을 균일한 시간 격자로 옮기고 완만하게 한다.

## 지어내지 않는 선

빠진 구간을 이어 붙이는 것은 측정값 사이를 잇는 보간이지 없는 값을 만드는
것이 아니다. 다만 공백이 길면 그건 보간이 아니라 창작이므로, MAX_GAP_SEC
보다 긴 공백에서는 선을 잇지 않고 끊는다.
"""
from __future__ import annotations

import math

import numpy as np

from app.services.swing.types import PoseSequence

L_SHOULDER, R_SHOULDER = 11, 12
L_ELBOW, R_ELBOW = 13, 14
L_WRIST, R_WRIST = 15, 16

# 이 값 아래면 랜드마크를 믿을 수 없다.
MIN_VISIBILITY = 0.3
# 양 손목이 어깨폭의 이 비율보다 멀면 한 그립을 잡고 있을 수 없다.
GRIP_GAP_RATIO = 0.5
# 팔뚝이 자기 중앙값의 이 비율보다 짧게 잡히면 손목이 팔꿈치에 붙은 것이다.
FOREARM_MIN_RATIO = 0.55
# 재표본화 주기와 이동평균 창. 창이 클수록 완만해지지만 탑이 뭉개진다.
RESAMPLE_HZ = 30.0
SMOOTH_WINDOW = 7
# 이보다 긴 공백은 잇지 않고 궤적을 끊는다.
MAX_GAP_SEC = 0.3


def _safe_stat(values: np.ndarray, percentile: float) -> float:
    """NaN 을 무시한 백분위수. 쓸 값이 하나도 없으면 0.0."""
    if values.size == 0 or not bool(np.isfinite(values).any()):
        return 0.0
    result = float(np.percentile(values[np.isfinite(values)], percentile))
    return result if math.isfinite(result) else 0.0


def _moving_average(values: np.ndarray, window: int) -> np.ndarray:
    """가장자리를 잃지 않는 이동평균. 양끝은 끝값으로 메워 길이를 보존한다."""
    if window <= 1 or values.size < window:
        return values
    pad = window // 2
    padded = np.pad(values, pad, mode="edge")
    kernel = np.ones(window, dtype=float) / float(window)
    return np.convolve(padded, kernel, mode="valid")


def _pick_hand(
    index: int,
    xy: np.ndarray,
    visibility: np.ndarray,
    forearm_l: np.ndarray,
    forearm_r: np.ndarray,
    median_l: float,
    median_r: float,
    shoulder_w: float,
) -> np.ndarray | None:
    """한 프레임의 손 위치를 고른다. 믿을 만한 쪽이 없으면 None."""
    left_ok = (
        float(visibility[index, L_WRIST]) >= MIN_VISIBILITY
        and forearm_l[index] >= median_l * FOREARM_MIN_RATIO
    )
    right_ok = (
        float(visibility[index, R_WRIST]) >= MIN_VISIBILITY
        and forearm_r[index] >= median_r * FOREARM_MIN_RATIO
    )

    left = xy[index, L_WRIST]
    right = xy[index, R_WRIST]

    if left_ok and right_ok:
        gap = float(np.linalg.norm(left - right))
        if gap <= shoulder_w * GRIP_GAP_RATIO:
            # 둘 다 그립 위에 있다. 중점이 한쪽 손목보다 흔들림이 적다.
            return (left + right) / 2.0
        # 떨어져 있으면 하나는 틀렸다. 중점을 쓰면 둘의 한가운데 — 아무 데도
        # 아닌 지점 — 가 되므로, 더 잘 보이는 쪽 하나만 쓴다.
        return left if visibility[index, L_WRIST] >= visibility[index, R_WRIST] else right
    if left_ok:
        return left
    if right_ok:
        return right
    return None


def _smooth_segment(times: list[float], points: list[tuple[float, float]]) -> list[list[float]]:
    """한 토막을 균일 격자로 재표본화하고 완만하게 만든다."""
    start, end = times[0], times[-1]
    step = 1.0 / RESAMPLE_HZ
    if end - start < step:
        return []
    grid = np.arange(start, end + step * 0.5, step)

    arr = np.asarray(points, dtype=float)
    xs = _moving_average(np.interp(grid, times, arr[:, 0]), SMOOTH_WINDOW)
    ys = _moving_average(np.interp(grid, times, arr[:, 1]), SMOOTH_WINDOW)

    return [
        [round(float(t), 3), round(float(x), 4), round(float(y), 4)]
        for t, x, y in zip(grid, xs, ys)
    ]


def build_tracks(seq: PoseSequence) -> dict[str, list[list[float]]]:
    """손 궤적을 [[초, x, y], ...] 로 만든다. x·y 는 0~1 정규화 좌표."""
    width, height = seq.resolution_wh
    if width <= 0 or height <= 0 or len(seq) < 2:
        return {"hands": []}

    xy = seq.xy_px
    visibility = seq.visibility

    # 이 사람의 치수. 스윙 내내 크게 변하지 않으므로 중앙값을 기준으로 삼는다.
    # 사람마다 체격이 다르므로 절대 픽셀값으로 기준을 잡으면 안 된다.
    #
    # nanmedian 을 쓰는 이유: 한 프레임만 NaN 이어도 median 은 NaN 이 되고,
    # 그러면 이후의 모든 비교가 False 가 되어 궤적이 통째로 사라진다.
    # 어깨폭은 중앙값이 아니라 상위값을 쓴다. 후면 촬영에서는 어깨가 카메라를
    # 향해 접혀 보여 2D 폭이 실제의 1/4 까지 줄어든다. 스윙 중 어느 순간에는
    # 어깨가 카메라와 나란해지므로, 그때의 폭이 실제 어깨폭에 가깝다.
    shoulder_w = _safe_stat(
        np.linalg.norm(xy[:, L_SHOULDER] - xy[:, R_SHOULDER], axis=1), 90.0
    )
    forearm_l = np.linalg.norm(xy[:, L_WRIST] - xy[:, L_ELBOW], axis=1)
    forearm_r = np.linalg.norm(xy[:, R_WRIST] - xy[:, R_ELBOW], axis=1)
    # 기준을 못 구하면 0 이 되고, 그러면 팔뚝 검사는 통과로 처리된다.
    # 기준이 없다는 이유로 멀쩡한 프레임까지 버리지는 않는다.
    median_l = _safe_stat(forearm_l, 50.0)
    median_r = _safe_stat(forearm_r, 50.0)
    if shoulder_w <= 0:
        return {"hands": []}

    times: list[float] = []
    points: list[tuple[float, float]] = []
    for i in range(len(seq)):
        picked = _pick_hand(
            i, xy, visibility, forearm_l, forearm_r, median_l, median_r, shoulder_w
        )
        if picked is None:
            continue
        x = float(picked[0]) / width
        y = float(picked[1]) / height
        if not (math.isfinite(x) and math.isfinite(y)):
            continue
        # 화면 밖으로 튄 좌표는 오검출이다.
        if not (-0.1 <= x <= 1.1 and -0.1 <= y <= 1.1):
            continue
        times.append(float(seq.frame_indices[i]) / seq.fps)
        points.append((x, y))

    if len(times) < 2:
        return {"hands": []}

    # 공백이 긴 곳에서 토막을 낸다. 토막 안에서만 잇고 다듬는다.
    hands: list[list[float]] = []
    seg_start = 0
    for i in range(1, len(times) + 1):
        breaks = i == len(times) or (times[i] - times[i - 1]) > MAX_GAP_SEC
        if not breaks:
            continue
        if i - seg_start >= 2:
            hands.extend(_smooth_segment(times[seg_start:i], points[seg_start:i]))
        seg_start = i

    return {"hands": hands}
