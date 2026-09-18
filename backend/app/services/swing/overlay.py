"""
swing/overlay.py — supervision 으로 스켈레톤 오버레이를 그린다.

기존 pose_estimator.make_overlay() 의 cv2 수작업(선·원을 일일이 그리던 40줄)을
대체한다. 어노테이터를 쓰면 뼈대 정의가 데이터(GOLF_EDGES)로 분리돼
나중에 클럽 탐지를 붙이거나 포즈 모델을 바꿀 때 그리기 코드를 안 고쳐도 된다.
"""
from __future__ import annotations

import os
from functools import lru_cache

import cv2
import numpy as np
import supervision as sv
from PIL import Image, ImageDraw, ImageFont

from app.services.swing.metrics import (
    L_ANKLE,
    L_ELBOW,
    L_HIP,
    L_KNEE,
    L_SHOULDER,
    L_WRIST,
    R_ANKLE,
    R_ELBOW,
    R_HIP,
    R_KNEE,
    R_SHOULDER,
    R_WRIST,
)

# 골프에서 의미 있는 뼈대만 그린다. 얼굴·손가락은 빼서 화면을 비운다.
# 어깨선과 힙선은 회전을 눈으로 확인하는 기준선이라 특히 중요하다.
GOLF_EDGES: list[tuple[int, int]] = [
    (L_SHOULDER, R_SHOULDER),  # 어깨선
    (L_HIP, R_HIP),  # 힙선
    (L_SHOULDER, L_ELBOW),
    (L_ELBOW, L_WRIST),
    (R_SHOULDER, R_ELBOW),
    (R_ELBOW, R_WRIST),
    (L_HIP, L_KNEE),
    (L_KNEE, L_ANKLE),
    (R_HIP, R_KNEE),
    (R_KNEE, R_ANKLE),
    (L_SHOULDER, L_HIP),  # 몸통 좌측
    (R_SHOULDER, R_HIP),  # 몸통 우측
]

_EDGE_ANNOTATOR = sv.EdgeAnnotator(
    color=sv.Color(r=0, g=200, b=255), thickness=3, edges=GOLF_EDGES
)
_VERTEX_ANNOTATOR = sv.VertexAnnotator(color=sv.Color(r=255, g=220, b=0), radius=5)

# 크롭 여백. 위를 넉넉히 주는 건 백스윙에서 손이 머리 위로 올라가기 때문이다.
_PAD_X, _PAD_TOP, _PAD_BOTTOM = 0.35, 0.60, 0.25
_LABEL_BAR_HEIGHT = 28


# 한글 폰트 후보. cv2.putText 는 한글을 못 그려 "1.??????" 가 되므로 Pillow 를 쓴다.
# macOS(로컬 개발)와 Linux(Railway 배포) 양쪽 경로를 순서대로 찾는다.
_FONT_CANDIDATES = (
    "/System/Library/Fonts/AppleSDGothicNeo.ttc",
    "/System/Library/Fonts/Supplemental/AppleGothic.ttf",
    "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
)
_LABEL_FONT_SIZE = 16


@lru_cache(maxsize=1)
def _label_font() -> ImageFont.FreeTypeFont | None:
    """한글을 그릴 수 있는 폰트를 찾는다. 없으면 None."""
    for path in _FONT_CANDIDATES:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, _LABEL_FONT_SIZE)
            except OSError:
                continue
    return None


def _draw_label(crop: np.ndarray, label: str) -> np.ndarray:
    """크롭 하단에 검은 띠를 깔고 단계 라벨을 얹는다.

    한글 폰트를 못 찾으면 글자가 깨지느니 숫자 접두사만 남긴다
    ("3.탑" → "3"). 깨진 물음표를 사용자에게 보여주지 않는다.
    """
    ch, cw = crop.shape[:2]
    cv2.rectangle(crop, (0, ch - _LABEL_BAR_HEIGHT), (cw, ch), (0, 0, 0), -1)

    font = _label_font()
    if font is None:
        fallback = label.split(".", 1)[0]
        cv2.putText(
            crop, fallback, (6, ch - 8), cv2.FONT_HERSHEY_SIMPLEX,
            0.5, (255, 255, 255), 1, cv2.LINE_AA,
        )
        return crop

    pil = Image.fromarray(cv2.cvtColor(crop, cv2.COLOR_BGR2RGB))
    ImageDraw.Draw(pil).text(
        (6, ch - _LABEL_BAR_HEIGHT + 4), label, font=font, fill=(255, 255, 255)
    )
    return cv2.cvtColor(np.array(pil), cv2.COLOR_RGB2BGR)


def render_overlay(frame: np.ndarray, xy_px: np.ndarray, label: str) -> bytes | None:
    """골퍼를 크롭하고 스켈레톤과 단계 라벨을 그려 JPEG 로 인코딩한다.

    유효한 랜드마크가 없어 크롭 영역을 정할 수 없으면 None 을 돌려준다.
    빈 이미지를 지어내지 않는다.
    입력 frame 은 변경하지 않는다.
    """
    h, w = frame.shape[:2]
    valid = xy_px[(xy_px[:, 0] > 0) & (xy_px[:, 1] > 0)]
    if len(valid) == 0:
        return None

    key_points = sv.KeyPoints(xy=xy_px[np.newaxis, ...].astype(np.float32))
    scene = _EDGE_ANNOTATOR.annotate(scene=frame.copy(), key_points=key_points)
    scene = _VERTEX_ANNOTATOR.annotate(scene=scene, key_points=key_points)

    x_min, y_min = valid.min(axis=0)
    x_max, y_max = valid.max(axis=0)
    box_w, box_h = x_max - x_min, y_max - y_min

    x1 = max(0, int(x_min - max(box_w * _PAD_X, w * 0.06)))
    x2 = min(w, int(x_max + max(box_w * _PAD_X, w * 0.06)))
    y1 = max(0, int(y_min - max(box_h * _PAD_TOP, h * 0.10)))
    y2 = min(h, int(y_max + max(box_h * _PAD_BOTTOM, h * 0.05)))

    crop = scene[y1:y2, x1:x2]
    if crop.shape[0] < 10 or crop.shape[1] < 10:
        return None

    crop = _draw_label(crop, label)

    ok, buffer = cv2.imencode(".jpg", crop, [cv2.IMWRITE_JPEG_QUALITY, 90])
    return buffer.tobytes() if ok else None
