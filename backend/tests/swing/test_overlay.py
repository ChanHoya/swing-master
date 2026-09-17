import cv2
import numpy as np

from app.services.swing.metrics import (
    L_ANKLE,
    L_ELBOW,
    L_HIP,
    L_KNEE,
    L_SHOULDER,
    L_WRIST,
    NOSE,
    R_ANKLE,
    R_ELBOW,
    R_HIP,
    R_KNEE,
    R_SHOULDER,
    R_WRIST,
)
from app.services.swing.overlay import GOLF_EDGES, render_overlay


def _frame(w=1000, h=1000):
    return np.full((h, w, 3), 30, dtype=np.uint8)


def _body():
    """전신이 프레임 안에 들어온 어드레스 자세."""
    xy = np.zeros((33, 2), dtype=np.float32)
    xy[NOSE] = (500.0, 220.0)
    xy[L_SHOULDER] = (400.0, 300.0)
    xy[R_SHOULDER] = (600.0, 300.0)
    xy[L_ELBOW] = (380.0, 420.0)
    xy[R_ELBOW] = (620.0, 420.0)
    xy[L_WRIST] = (480.0, 520.0)
    xy[R_WRIST] = (520.0, 520.0)
    xy[L_HIP] = (430.0, 550.0)
    xy[R_HIP] = (570.0, 550.0)
    xy[L_KNEE] = (430.0, 750.0)
    xy[R_KNEE] = (570.0, 750.0)
    xy[L_ANKLE] = (430.0, 930.0)
    xy[R_ANKLE] = (570.0, 930.0)
    return xy


def test_golf_edges_connect_shoulders_and_hips():
    """어깨선과 힙선은 회전을 눈으로 보는 기준선이라 반드시 있어야 한다."""
    assert (L_SHOULDER, R_SHOULDER) in GOLF_EDGES
    assert (L_HIP, R_HIP) in GOLF_EDGES


def test_golf_edges_reference_valid_landmarks():
    for a, b in GOLF_EDGES:
        assert 0 <= a < 33 and 0 <= b < 33


def test_golf_edges_exclude_face_and_fingers():
    """얼굴·손가락 랜드마크(1~10, 17~22)는 화면을 어지럽히므로 뺀다."""
    noisy = set(range(1, 11)) | set(range(17, 23))
    for a, b in GOLF_EDGES:
        assert a not in noisy and b not in noisy


def test_render_returns_decodable_jpeg():
    data = render_overlay(_frame(), _body(), "5.임팩트")
    assert data is not None
    decoded = cv2.imdecode(np.frombuffer(data, dtype=np.uint8), cv2.IMREAD_COLOR)
    assert decoded is not None
    assert decoded.shape[0] > 0 and decoded.shape[1] > 0


def test_render_draws_something_on_the_frame():
    """빈 배경 그대로면 스켈레톤이 안 그려진 것이다."""
    data = render_overlay(_frame(), _body(), "5.임팩트")
    decoded = cv2.imdecode(np.frombuffer(data, dtype=np.uint8), cv2.IMREAD_COLOR)
    assert decoded.std() > 5.0


def test_render_crops_to_the_golfer():
    """전신이 프레임의 일부만 차지하면 잘라내 크게 보여줘야 한다."""
    data = render_overlay(_frame(2000, 2000), _body(), "1.어드레스")
    decoded = cv2.imdecode(np.frombuffer(data, dtype=np.uint8), cv2.IMREAD_COLOR)
    assert decoded.shape[0] < 2000 and decoded.shape[1] < 2000


def test_render_returns_none_when_no_valid_landmarks():
    """전부 0이면 크롭 영역을 만들 수 없다. 빈 이미지를 지어내지 않는다."""
    blank = np.zeros((33, 2), dtype=np.float32)
    assert render_overlay(_frame(), blank, "1.어드레스") is None


def test_render_does_not_mutate_the_input_frame():
    frame = _frame()
    before = frame.copy()
    render_overlay(frame, _body(), "3.탑")
    assert np.array_equal(frame, before), "원본 프레임이 변경됐다"


def test_korean_label_font_is_available():
    """cv2.putText 는 한글을 못 그린다. Pillow 폰트가 잡혀야 한다."""
    from app.services.swing.overlay import _label_font

    font = _label_font()
    assert font is not None, "한글 폰트를 찾지 못했다 — 라벨이 물음표로 깨진다"


def test_label_bar_is_drawn_at_the_bottom():
    """하단 검은 띠 위에 라벨이 얹힌다. 띠가 없으면 글자가 배경에 묻힌다."""
    data = render_overlay(_frame(), _body(), "3.탑")
    decoded = cv2.imdecode(np.frombuffer(data, dtype=np.uint8), cv2.IMREAD_COLOR)
    h = decoded.shape[0]
    bottom_strip = decoded[h - 24 : h - 20, :]
    assert bottom_strip.mean() < 60, "하단 띠가 충분히 어둡지 않다"
