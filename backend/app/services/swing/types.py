"""
swing/types.py — 스윙 분석 파이프라인의 공용 자료구조.

의존성은 numpy 뿐이다. 이 모듈은 DB·파일·네트워크를 알지 못한다.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

# 스윙 7단계 — 시간 순서
PHASE_KEYS: tuple[str, ...] = (
    "address", "takeaway", "top", "downswing",
    "impact", "followthrough", "finish",
)


@dataclass(frozen=True)
class MetricValue:
    """지표 하나의 측정 결과.

    value 가 None 인 경우는 두 가지다.
      - measurable=False : 촬영 각도상 애초에 측정할 수 없다.
      - measurable=True  : 측정 대상이지만 랜드마크가 부족해 실패했다.
    두 경우를 화면에서 다르게 안내해야 하므로 구분해 둔다.
    """

    value: float | None
    confidence: float
    unit: str
    measurable: bool

    @classmethod
    def unmeasurable(cls, unit: str) -> MetricValue:
        """이 촬영 각도에서는 측정할 수 없는 지표."""
        return cls(value=None, confidence=0.0, unit=unit, measurable=False)

    @classmethod
    def failed(cls, unit: str) -> MetricValue:
        """측정 대상이지만 랜드마크 부족으로 계산하지 못한 지표."""
        return cls(value=None, confidence=0.0, unit=unit, measurable=True)


@dataclass(frozen=True)
class PoseSequence:
    """스윙 구간에서 추출한 프레임별 포즈.

    world        : (F, 33, 3) 힙 중심 원점, 미터 단위 3D
    xy_px        : (F, 33, 2) 이미지 픽셀 좌표
    visibility   : (F, 33)    0.0~1.0
    frame_indices: (F,)       원본 영상에서의 프레임 번호
    fps          : 원본 영상의 초당 프레임 수
    resolution_wh: 원본 영상 해상도 (width, height)
    """

    world: np.ndarray
    xy_px: np.ndarray
    visibility: np.ndarray
    frame_indices: np.ndarray
    fps: float
    resolution_wh: tuple[int, int]

    def __len__(self) -> int:
        return int(self.world.shape[0])
