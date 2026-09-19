"""
초대 코드 검증 테스트.

공개 URL 에 올리면 누구나 가입할 수 있으므로 가입을 초대 코드로 잠근다.
INVITE_CODE 가 설정되지 않았을 때 '열림'이 아니라 '닫힘'이어야 한다 —
환경변수를 깜빡하고 배포했을 때 문이 열려 있으면 안 된다.
"""
import pytest
from fastapi import HTTPException

from app.core.auth import verify_invite_code
from app.core.config import settings


def test_accepts_matching_code(monkeypatch):
    monkeypatch.setattr(settings, "INVITE_CODE", "let-me-in")
    verify_invite_code("let-me-in")  # 예외가 없으면 통과


def test_rejects_wrong_code(monkeypatch):
    monkeypatch.setattr(settings, "INVITE_CODE", "let-me-in")
    with pytest.raises(HTTPException) as exc:
        verify_invite_code("guess")
    assert exc.value.status_code == 403
    assert "초대 코드" in exc.value.detail


def test_rejects_missing_code(monkeypatch):
    monkeypatch.setattr(settings, "INVITE_CODE", "let-me-in")
    with pytest.raises(HTTPException) as exc:
        verify_invite_code(None)
    assert exc.value.status_code == 403


def test_registration_is_closed_when_code_not_configured(monkeypatch):
    """설정이 비어 있으면 가입을 여는 게 아니라 막는다."""
    monkeypatch.setattr(settings, "INVITE_CODE", "")
    with pytest.raises(HTTPException) as exc:
        verify_invite_code("anything")
    assert exc.value.status_code == 403
    assert "닫혀" in exc.value.detail


def test_rejects_code_of_different_length(monkeypatch):
    """compare_digest 는 길이가 다르면 ValueError 가 아니라 False 여야 한다."""
    monkeypatch.setattr(settings, "INVITE_CODE", "short")
    with pytest.raises(HTTPException) as exc:
        verify_invite_code("a-much-longer-guess")
    assert exc.value.status_code == 403
