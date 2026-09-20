"""
업로드 시 받는 촬영 각도·클럽 검증.

촬영 각도는 어떤 지표를 계산할 수 있는지를 결정하므로(METRIC_ANGLES),
아무 문자열이나 받으면 게이팅이 조용히 무너진다. 허용값만 통과시킨다.
"""
import pytest
from fastapi import HTTPException

from app.api.endpoints.upload import normalise_camera_angle, normalise_club


@pytest.mark.parametrize("angle", ["down_the_line", "face_on", "angled"])
def test_accepts_known_angles(angle):
    assert normalise_camera_angle(angle) == angle


def test_rejects_unknown_angle():
    with pytest.raises(HTTPException) as exc:
        normalise_camera_angle("sideways")
    assert exc.value.status_code == 400
    assert "촬영 각도" in exc.value.detail


def test_rejects_missing_angle():
    """각도를 모르면 추측하지 않는다. 지표 게이팅의 근거이기 때문이다."""
    with pytest.raises(HTTPException) as exc:
        normalise_camera_angle(None)
    assert exc.value.status_code == 400


@pytest.mark.parametrize("club", ["드라이버", "7I", "SW"])
def test_accepts_known_clubs(club):
    assert normalise_club(club) == club


def test_club_is_optional():
    """클럽은 지표에 영향을 주지 않는다. 없으면 없는 대로 둔다."""
    assert normalise_club(None) is None
    assert normalise_club("") is None


def test_rejects_unknown_club():
    with pytest.raises(HTTPException) as exc:
        normalise_club("드라이버; DROP TABLE uploads")
    assert exc.value.status_code == 400
    assert "클럽" in exc.value.detail
