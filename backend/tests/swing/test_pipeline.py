import numpy as np

from app.services.swing.pipeline import PHASE_LABELS, summarise_metrics
from app.services.swing.types import PHASE_KEYS


def test_phase_labels_cover_all_seven_phases_in_korean():
    assert set(PHASE_LABELS) == set(PHASE_KEYS)
    assert PHASE_LABELS["impact"] == "5.임팩트"
    assert PHASE_LABELS["address"] == "1.어드레스"


def test_summarise_counts_only_measured_metrics():
    payload = {
        "spine_angle": {"value": 35.0, "confidence": 0.9, "unit": "°", "measurable": True},
        "knee_flex": {"value": None, "confidence": 0.0, "unit": "°", "measurable": True},
        "x_factor": {"value": None, "confidence": 0.0, "unit": "°", "measurable": False},
    }
    summary = summarise_metrics(payload)
    assert summary["measured_count"] == 1
    assert summary["total_count"] == 3


def test_summarise_reports_zero_when_nothing_measured():
    payload = {
        "spine_angle": {"value": None, "confidence": 0.0, "unit": "°", "measurable": True},
    }
    assert summarise_metrics(payload)["measured_count"] == 0


def _write_synthetic_video(path, frames=20, w=1280, h=720):
    """cv2 로 읽을 수 있는 최소 영상을 만든다."""
    import cv2

    writer = cv2.VideoWriter(
        str(path), cv2.VideoWriter_fourcc(*"mp4v"), 30.0, (w, h)
    )
    for i in range(frames):
        frame = np.full((h, w, 3), 20 + i * 5, dtype=np.uint8)
        cv2.circle(frame, (w // 2, h // 2), 40, (0, 0, 255), -1)
        writer.write(frame)
    writer.release()
    return str(path)


def _sequence_for(frames=20, w=1280, h=720, proc_width=640):
    """extract_sequence 와 같은 proc_width 기준 좌표계를 가진 시퀀스."""
    from app.services.swing.metrics import (
        L_ANKLE, L_HIP, L_KNEE, L_SHOULDER, R_ANKLE, R_HIP, R_KNEE, R_SHOULDER,
    )
    from app.services.swing.types import PoseSequence

    sh = int(h * proc_width / w)
    xy = np.zeros((frames, 33, 2), dtype=np.float32)
    for f in range(frames):
        xy[f, L_SHOULDER] = (proc_width * 0.40, sh * 0.30)
        xy[f, R_SHOULDER] = (proc_width * 0.60, sh * 0.30)
        xy[f, L_HIP] = (proc_width * 0.43, sh * 0.55)
        xy[f, R_HIP] = (proc_width * 0.57, sh * 0.55)
        xy[f, L_KNEE] = (proc_width * 0.43, sh * 0.75)
        xy[f, R_KNEE] = (proc_width * 0.57, sh * 0.75)
        xy[f, L_ANKLE] = (proc_width * 0.43, sh * 0.92)
        xy[f, R_ANKLE] = (proc_width * 0.57, sh * 0.92)
    return PoseSequence(
        world=np.zeros((frames, 33, 3), dtype=np.float32),
        xy_px=xy,
        visibility=np.full((frames, 33), 0.9, dtype=np.float32),
        frame_indices=np.arange(frames, dtype=np.int32),
        fps=30.0,
        resolution_wh=(proc_width, sh),
    )


def test_render_phase_overlays_produces_all_seven(tmp_path):
    """seek 으로 다시 읽은 프레임에 7단계 오버레이가 모두 만들어져야 한다."""
    from app.services.swing.pipeline import _render_phase_overlays

    video = _write_synthetic_video(tmp_path / "s.mp4")
    seq = _sequence_for()
    phases = {k: i * 2 for i, k in enumerate(PHASE_KEYS)}
    images = _render_phase_overlays(video, seq, phases)

    assert set(images) == set(PHASE_KEYS)
    for phase, data in images.items():
        assert len(data) > 100, f"{phase} 이미지가 비어 있다"


def test_render_phase_overlays_scales_frame_to_match_coordinates(tmp_path):
    """프레임 리사이즈를 빠뜨리면 좌표가 어긋나 크롭이 엉뚱해진다.

    xy_px 는 proc_width=640 기준이므로, 1280 폭 원본을 그대로 쓰면
    스켈레톤이 화면 왼쪽 절반에 몰린다. 크롭 폭으로 그 차이를 잡는다.
    """
    import cv2
    from app.services.swing.pipeline import _render_phase_overlays

    video = _write_synthetic_video(tmp_path / "s.mp4", w=1280, h=720)
    seq = _sequence_for(w=1280, h=720, proc_width=640)
    images = _render_phase_overlays(video, seq, {k: 2 for k in PHASE_KEYS})

    decoded = cv2.imdecode(
        np.frombuffer(images["impact"], dtype=np.uint8), cv2.IMREAD_COLOR
    )
    # 640 으로 줄인 뒤 크롭했으므로 결과 폭은 640 을 넘을 수 없다
    assert decoded.shape[1] <= 640
