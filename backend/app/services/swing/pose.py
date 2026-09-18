"""
swing/pose.py — 영상에서 프레임별 3D/2D 포즈를 추출한다.

기존 pose_estimator.py 와 달리 pose_world_landmarks(미터 단위 3D)를 함께 뽑는다.
회전 지표는 이것 없이 계산할 수 없다.
"""
from __future__ import annotations

import os

import cv2
import numpy as np
import supervision as sv
from mediapipe import Image, ImageFormat
from mediapipe.tasks.python.core.base_options import BaseOptions
from mediapipe.tasks.python.vision import PoseLandmarker, PoseLandmarkerOptions

from app.services.swing.types import PoseSequence

MODEL_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "pose_landmarker_lite.task"
)

_landmarker: PoseLandmarker | None = None


def get_landmarker() -> PoseLandmarker:
    """PoseLandmarker 싱글턴. 재로딩에 2~3초가 들므로 한 번만 만든다."""
    global _landmarker
    if _landmarker is None:
        _landmarker = PoseLandmarker.create_from_options(
            PoseLandmarkerOptions(
                base_options=BaseOptions(model_asset_path=MODEL_PATH),
                output_segmentation_masks=False,
                min_pose_detection_confidence=0.25,
                min_pose_presence_confidence=0.25,
                min_tracking_confidence=0.25,
            )
        )
    return _landmarker


def landmarks_from_result(
    result, resolution_wh: tuple[int, int]
) -> tuple[np.ndarray, np.ndarray, np.ndarray] | None:
    """MediaPipe 결과에서 (world, xy_px, visibility) 를 뽑는다.

    포즈가 없거나 world 좌표가 빠져 있으면 None.
    world 가 없으면 회전 지표를 낼 수 없으므로 실패로 취급한다.
    """
    if not getattr(result, "pose_landmarks", None):
        return None
    if not getattr(result, "pose_world_landmarks", None):
        return None

    world_lms = result.pose_world_landmarks[0]
    world = np.array([[lm.x, lm.y, lm.z] for lm in world_lms], dtype=np.float32)

    # supervision 이 정규화 좌표를 픽셀로 바꿔 준다.
    # 직접 곱하지 않는 이유는 나중에 다른 포즈 모델로 갈아타기 위해서다.
    key_points = sv.KeyPoints.from_mediapipe(result, resolution_wh)
    xy_px = np.asarray(key_points.xy[0], dtype=np.float32)

    visibility = np.array(
        [getattr(lm, "visibility", 0.0) or 0.0 for lm in result.pose_landmarks[0]],
        dtype=np.float32,
    )
    return world, xy_px, visibility


def extract_sequence(
    video_path: str,
    start_frame: int,
    end_frame: int,
    skip: int = 2,
    proc_width: int = 640,
) -> PoseSequence:
    """스윙 구간을 훑어 PoseSequence 를 만든다.

    포즈가 검출되지 않은 프레임은 시퀀스에서 빠진다.
    frame_indices 가 원본 프레임 번호를 보존하므로 템포 계산에 지장이 없다.
    """
    cap = cv2.VideoCapture(video_path)
    landmarker = get_landmarker()

    worlds: list[np.ndarray] = []
    pixels: list[np.ndarray] = []
    visibilities: list[np.ndarray] = []
    indices: list[int] = []

    try:
        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
        current = start_frame
        counter = 0
        width = height = 0

        while current <= end_frame:
            ok, frame = cap.read()
            if not ok:
                break
            counter += 1
            frame_index = current
            current += 1
            if counter % skip != 0:
                continue

            h0, w0 = frame.shape[:2]
            if w0 > proc_width:
                scaled = cv2.resize(frame, (proc_width, int(h0 * proc_width / w0)))
            else:
                scaled = frame
            height, width = scaled.shape[:2]

            mp_image = Image(
                image_format=ImageFormat.SRGB,
                data=cv2.cvtColor(scaled, cv2.COLOR_BGR2RGB),
            )
            extracted = landmarks_from_result(
                landmarker.detect(mp_image), (width, height)
            )
            if extracted is None:
                continue

            world, xy_px, visibility = extracted
            worlds.append(world)
            pixels.append(xy_px)
            visibilities.append(visibility)
            indices.append(frame_index)
    finally:
        cap.release()

    if len(worlds) < 3:
        raise ValueError(
            f"포즈 인식에 실패했습니다 (인식된 프레임 {len(worlds)}개). "
            "측면 또는 정면에서 전신이 보이도록 촬영해 주세요."
        )

    return PoseSequence(
        world=np.stack(worlds),
        xy_px=np.stack(pixels),
        visibility=np.stack(visibilities),
        frame_indices=np.array(indices, dtype=np.int32),
        fps=float(fps),
        resolution_wh=(width, height),
    )
