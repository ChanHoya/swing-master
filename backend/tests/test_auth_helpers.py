"""
app/core/auth.py 의 인증 헬퍼 테스트.

업로드는 로그인 없이도 되어야 하지만, 로그인했다면 그 사용자에게
귀속되어야 한다. 그래야 나중에 히스토리에서 찾을 수 있다.
"""
import uuid

import pytest
from fastapi import HTTPException
from jose import jwt

from app.core.auth import (
    decode_user_id,
    get_current_user_id,
    get_optional_user_id,
)
from app.core.config import settings

USER_ID = str(uuid.uuid4())


def _token(sub: str = USER_ID, secret: str | None = None) -> str:
    return jwt.encode({"sub": sub}, secret or settings.SECRET_KEY, algorithm="HS256")


def _bearer(sub: str = USER_ID) -> str:
    return f"Bearer {_token(sub)}"


# ── decode_user_id — 예외를 던지지 않는 순수 해석기 ──────────────────────
def test_decode_returns_user_id_from_valid_token():
    assert decode_user_id(_bearer()) == USER_ID


def test_decode_returns_none_when_header_missing():
    assert decode_user_id(None) is None


def test_decode_returns_none_when_scheme_is_not_bearer():
    assert decode_user_id(f"Basic {_token()}") is None


def test_decode_returns_none_for_garbage_token():
    assert decode_user_id("Bearer not-a-jwt") is None


def test_decode_returns_none_when_signed_with_wrong_secret():
    """다른 비밀키로 서명된 토큰을 받아들이면 안 된다."""
    assert decode_user_id(f"Bearer {_token(secret='attacker-key')}") is None


def test_decode_returns_none_when_sub_claim_missing():
    token = jwt.encode({"email": "x@y.z"}, settings.SECRET_KEY, algorithm="HS256")
    assert decode_user_id(f"Bearer {token}") is None


# ── get_optional_user_id — 없으면 None, 막지 않는다 ─────────────────────
@pytest.mark.asyncio
async def test_optional_returns_user_id_when_logged_in():
    assert await get_optional_user_id(_bearer()) == USER_ID


@pytest.mark.asyncio
async def test_optional_returns_none_when_anonymous():
    """비로그인 업로드를 막으면 안 된다. ANON_DAILY_LIMIT 설계가 전제다."""
    assert await get_optional_user_id(None) is None


@pytest.mark.asyncio
async def test_optional_returns_none_for_invalid_token_without_raising():
    assert await get_optional_user_id("Bearer broken") is None


# ── get_current_user_id — 없으면 401 ───────────────────────────────────
@pytest.mark.asyncio
async def test_required_returns_user_id_when_logged_in():
    assert await get_current_user_id(_bearer()) == USER_ID


@pytest.mark.asyncio
async def test_required_raises_401_when_header_missing():
    with pytest.raises(HTTPException) as exc:
        await get_current_user_id(None)
    assert exc.value.status_code == 401
    assert "로그인" in exc.value.detail


@pytest.mark.asyncio
async def test_required_raises_401_for_invalid_token():
    with pytest.raises(HTTPException) as exc:
        await get_current_user_id("Bearer broken")
    assert exc.value.status_code == 401
