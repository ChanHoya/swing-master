"""
업로드 파일 형식 검증.

브라우저에서 640px 로 줄여 보내면 MediaRecorder 가 만든 형식이 온다.
Chrome 은 webm, Safari 는 mp4 다. 게다가 content-type 에 코덱 꼬리표가
붙는다 — "video/webm;codecs=vp9" 처럼. 정확히 일치만 보면 이것들이
전부 거부되어, 줄여 보내는 최적화가 통째로 막힌다.
"""
import pytest
from fastapi import HTTPException

from app.api.endpoints.upload import normalise_content_type


@pytest.mark.parametrize(
    "raw",
    [
        "video/mp4",
        "video/quicktime",
        "video/webm",
        "video/webm;codecs=vp9",
        "video/webm; codecs=vp8,opus",
        "video/mp4;codecs=avc1.42E01E",
        "VIDEO/MP4",
    ],
)
def test_accepts_supported_types_with_or_without_codecs(raw):
    assert normalise_content_type(raw).startswith("video/")


@pytest.mark.parametrize("raw", ["image/png", "application/pdf", "video/x-msvideo", "", None])
def test_rejects_unsupported_types(raw):
    with pytest.raises(HTTPException) as exc:
        normalise_content_type(raw)
    assert exc.value.status_code == 400


def test_codec_tag_is_stripped():
    assert normalise_content_type("video/webm;codecs=vp9") == "video/webm"


# ── 저장 파일 확장자 ───────────────────────────────────────────────────────
#
# 브라우저에서 줄여 보내면 내용은 webm 인데 파일 이름은 원본 그대로
# "swing.mp4" 로 온다. 이름을 믿고 확장자를 정하면 R2 에 내용과 다른
# 확장자로 저장된다. 내용을 말해 주는 것은 content-type 이다.
from app.api.endpoints.upload import extension_for


def test_extension_follows_the_content_type_not_the_filename():
    assert extension_for("video/webm") == "webm"
    assert extension_for("video/mp4") == "mp4"
    assert extension_for("video/quicktime") == "mov"
