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
# 팔뚝이 같은 프레임의 위팔보다 이 비율 아래로 짧으면 손목이 팔꿈치에 붙은 것이다.
#
# 자기 중앙값과 비교하던 것을 위팔과 비교하도록 바꿨다. 중앙값 기준은 두 가지로
# 무너진다. 첫째, 검사하려는 그 측정값의 중앙값이라 붕괴가 만연하면 기준도 함께
# 내려가 검사가 무력해진다. 둘째, 절대 길이로는 "팔이 카메라를 향해 단축된 것"과
# "손목이 팔꿈치로 미끄러진 것"을 구분하지 못해 멀쩡한 프레임까지 버린다.
#
# 위팔은 팔뚝과 함께 단축되므로 비율은 유지된다. 실측 팔뚝/위팔 중앙값은
# 어깨폭 59px 영상에서 0.92, 17px 영상에서 0.88 이었다.
FOREARM_TO_UPPER_ARM_MIN = 0.5
# 재표본화 주기와 이동평균 창.
#
# 창을 0.10초(3샘플)로 줄였다가 0.23초(7샘플)로 되돌렸다. 줄이면 원호를 덜
# 깎지만 눈에 띄게 삐뚤어지고, 실사용에서는 그쪽이 더 거슬린다.
#
# 떨림과 편향은 하나의 절충선 위에 있고, 필터를 바꾸는 것으로는 그 선을
# 벗어나지 못했다. 영상 3개 실측 (떨림 / 반지름 편향, 음수는 원호 안쪽):
#
#     이동평균 0.23초    1.11px           매끄럽다, 원호를 깎는다
#     이동평균 0.10초    2.16px           덜 깎지만 삐뚤다
#     Savitzky-Golay     1.04~1.90px      이동평균을 이기지 못했다
#     3차 벌점 tau=0.03  2.90px / -1.1px  편향은 거의 없지만 가장 삐뚤다
#     3차 벌점 tau=0.10  1.73px / -18.6px
#
# 선을 정하는 것은 필터가 아니라 측정점의 밀도다. pose.py 가 skip=2 로 두
# 프레임에 하나만 추론해 스윙 전체에 점이 30개 남짓이다. 점이 성글면 잡음을
# 누르는 데 긴 창이 필요하고, 긴 창은 반드시 원호를 깎는다. 근본 해결은
# 프레임 수와 골퍼에게 할당된 해상도를 늘리는 것이지 필터가 아니다.
RESAMPLE_HZ = 30.0
SMOOTH_WINDOW = 7
# 이보다 긴 공백은 잇지 않고 궤적을 끊는다.
MAX_GAP_SEC = 0.3


def forearm_is_collapsed(forearm: float, upper_arm: float) -> bool:
    """손목이 팔꿈치 위로 미끄러졌는가.

    위팔을 못 재면(0 이거나 NaN) 판단할 근거가 없다. 근거가 없다는 이유로
    멀쩡한 프레임을 버리지는 않는다 — 버린 자리는 보간이 메우고, 그 보간이
    원호를 가로질러 궤적을 망친다.
    """
    if not (math.isfinite(forearm) and math.isfinite(upper_arm)) or upper_arm <= 0.0:
        return False
    return forearm < upper_arm * FOREARM_TO_UPPER_ARM_MIN


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
    upper_l: np.ndarray,
    upper_r: np.ndarray,
    shoulder_w: float,
) -> np.ndarray | None:
    """한 프레임의 손 위치를 고른다. 믿을 만한 쪽이 없으면 None."""
    left_ok = (
        float(visibility[index, L_WRIST]) >= MIN_VISIBILITY
        and not forearm_is_collapsed(float(forearm_l[index]), float(upper_l[index]))
    )
    right_ok = (
        float(visibility[index, R_WRIST]) >= MIN_VISIBILITY
        and not forearm_is_collapsed(float(forearm_r[index]), float(upper_r[index]))
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


def _catmull_rom(p0, p1, p2, p3, t: np.ndarray, alpha: float = 0.5) -> np.ndarray:
    """p1~p2 구간을 중심구심 Catmull-Rom 으로 보간한다.

    alpha=0.5(중심구심)를 쓰는 이유는 첨점과 과도한 출렁임을 막기 때문이다.
    균일 매개변수(alpha=0)는 점 간격이 고르지 않을 때 고리를 만든다.
    """
    def tj(ti: float, a, b) -> float:
        d = float(np.linalg.norm(np.asarray(b) - np.asarray(a)))
        return ti + (d ** alpha if d > 0 else 1e-9)

    t0 = 0.0
    t1 = tj(t0, p0, p1)
    t2 = tj(t1, p1, p2)
    t3 = tj(t2, p2, p3)
    # t 는 0~1 → t1~t2 구간으로 옮긴다
    tt = (t1 + (t2 - t1) * t)[:, None]

    a1 = (t1 - tt) / (t1 - t0) * p0 + (tt - t0) / (t1 - t0) * p1
    a2 = (t2 - tt) / (t2 - t1) * p1 + (tt - t1) / (t2 - t1) * p2
    a3 = (t3 - tt) / (t3 - t2) * p2 + (tt - t2) / (t3 - t2) * p3
    b1 = (t2 - tt) / (t2 - t0) * a1 + (tt - t0) / (t2 - t0) * a2
    b2 = (t3 - tt) / (t3 - t1) * a2 + (tt - t1) / (t3 - t1) * a3
    return (t2 - tt) / (t2 - t1) * b1 + (tt - t1) / (t2 - t1) * b2


def resample_path(
    times: list[float], points: list[tuple[float, float]], hz: float = RESAMPLE_HZ
) -> list[list[float]]:
    """측정점을 균일한 시간 격자로 다시 뽑는다. [[초, x, y], ...]

    직선 보간을 쓰지 않는다. 임팩트 부근은 모션 블러로 손목이 무너져
    프레임이 버려지는데, 그 구멍을 직선으로 이으면 원호의 현을 가로질러
    안쪽으로 파고든다. 스윙에서 가장 빠르고 가장 많이 휘는 구간이라
    이탈이 크고, 원호 안쪽에는 팔꿈치가 있어 "궤적이 팔꿈치로 올라간다"로
    보인다. 실측에서 채택된 프레임 위의 점은 손목에서 평균 4px 였지만
    보간으로 만든 점은 12.5px 였다.

    이웃 점의 곡률을 반영하는 Catmull-Rom 으로 이으면 현 대신 호를 따른다.
    없는 값을 지어내는 것이 아니라, 측정점 사이를 더 정직하게 잇는 것이다.
    """
    if len(times) < 2:
        return []
    step = 1.0 / hz
    if times[-1] - times[0] < step:
        return []

    pts = np.asarray(points, dtype=float)
    ts = np.asarray(times, dtype=float)
    # 양 끝은 이웃이 없으므로 끝점을 한 번 더 둔다(자연스러운 끝맺음).
    padded = np.vstack([pts[0], pts, pts[-1]])

    grid = np.arange(ts[0], ts[-1] + step * 0.5, step)
    out: list[list[float]] = []
    for t in grid:
        # t 가 속한 측정 구간 i..i+1 을 찾는다
        i = int(np.searchsorted(ts, t, side="right") - 1)
        i = max(0, min(i, len(ts) - 2))
        span = ts[i + 1] - ts[i]
        local = 0.0 if span <= 0 else float((t - ts[i]) / span)
        xy = _catmull_rom(
            padded[i], padded[i + 1], padded[i + 2], padded[i + 3],
            np.array([local]),
        )[0]
        out.append([round(float(t), 3), round(float(xy[0]), 4), round(float(xy[1]), 4)])
    return out


def _smooth_segment(times: list[float], points: list[tuple[float, float]]) -> list[list[float]]:
    """한 토막을 균일 격자로 재표본화하고 완만하게 만든다."""
    filled = resample_path(times, points, RESAMPLE_HZ)
    if not filled:
        return []

    arr = np.asarray(filled, dtype=float)
    xs = _moving_average(arr[:, 1], SMOOTH_WINDOW)
    ys = _moving_average(arr[:, 2], SMOOTH_WINDOW)

    return [
        [round(float(t), 3), round(float(x), 4), round(float(y), 4)]
        for t, x, y in zip(arr[:, 0], xs, ys)
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
    # 같은 프레임의 위팔과 견준다. 프레임마다 비교하므로 중앙값을 미리
    # 구할 필요가 없고, 영상 규모(어깨폭 17px~59px)에도 영향받지 않는다.
    upper_l = np.linalg.norm(xy[:, L_ELBOW] - xy[:, L_SHOULDER], axis=1)
    upper_r = np.linalg.norm(xy[:, R_ELBOW] - xy[:, R_SHOULDER], axis=1)
    if shoulder_w <= 0:
        return {"hands": []}

    times: list[float] = []
    points: list[tuple[float, float]] = []
    for i in range(len(seq)):
        picked = _pick_hand(
            i, xy, visibility, forearm_l, forearm_r, upper_l, upper_r, shoulder_w
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
