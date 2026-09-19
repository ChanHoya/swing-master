"""
swing/tracks.py — 프레임별 궤적.

지표(metrics)가 "한 순간의 각도"라면 궤적은 "시간에 따른 경로"다.
영상 위에 겹쳐 그리려고 만드는 것이라 좌표를 0~1 로 정규화해 내보낸다.
그래야 프론트가 재생 화면 크기·레터박스를 모르는 채로도 픽셀로 환산할 수 있다.

측정하지 못한 프레임에 값을 채우지 않는 것은 metrics 와 같은 규칙이다.
보이지 않은 프레임은 점을 찍지 않고 건너뛴다.
"""
from __future__ import annotations

import math

from app.services.swing.types import PoseSequence

L_WRIST, R_WRIST = 15, 16

# 이 값 아래면 랜드마크를 믿을 수 없다.
MIN_VISIBILITY = 0.3


def build_tracks(seq: PoseSequence) -> dict[str, list[list[float]]]:
    """손 궤적을 [[초, x, y], ...] 로 만든다. x·y 는 0~1 정규화 좌표.

    양손은 그립에서 붙어 있으므로 두 손목의 중점을 쓴다. 한쪽만 보이면
    보이는 쪽을 쓰고, 둘 다 안 보이면 그 프레임은 통째로 건너뛴다.
    """
    width, height = seq.resolution_wh
    if width <= 0 or height <= 0:
        return {"hands": []}

    hands: list[list[float]] = []
    for i in range(len(seq)):
        vis = seq.visibility[i]
        usable = [j for j in (L_WRIST, R_WRIST) if float(vis[j]) >= MIN_VISIBILITY]
        if not usable:
            continue

        point = seq.xy_px[i][usable].mean(axis=0)
        x = float(point[0]) / width
        y = float(point[1]) / height
        if not (math.isfinite(x) and math.isfinite(y)):
            continue
        # 화면 밖으로 튄 좌표는 오검출이다. 궤적에 넣으면 선이 화면을 가로지른다.
        if not (-0.1 <= x <= 1.1 and -0.1 <= y <= 1.1):
            continue

        sec = float(seq.frame_indices[i]) / seq.fps
        hands.append([round(sec, 3), round(x, 4), round(y, 4)])

    return {"hands": hands}
