"""
core/auth.py — JWT 에서 사용자를 꺼내는 공용 의존성.

원래 history.py 안에 get_current_user_id 하나만 있었고 업로드는 인증을
아예 받지 않았다. 그래서 Upload.user_id 와 Analysis.user_id 가 항상 NULL 이었고,
user_id 로 필터하는 GET /history 는 로그인해도 빈 배열을 돌려줬다.

업로드는 로그인 없이도 되어야 하므로(ANON_DAILY_LIMIT 설계) 인증을 강제할 수
없다. 대신 "있으면 쓰고 없으면 넘어가는" 변형을 둔다.
"""
from __future__ import annotations

from fastapi import Header, HTTPException
from jose import JWTError, jwt

from app.core.config import settings

JWT_ALGO = "HS256"
_BEARER_PREFIX = "Bearer "


def decode_user_id(authorization: str | None) -> str | None:
    """Authorization 헤더에서 user_id 를 꺼낸다. 실패하면 None.

    예외를 던지지 않는 순수 해석기다. 강제 인증과 선택 인증이 같은
    판정 로직을 쓰도록 여기로 모았다.
    """
    if not authorization or not authorization.startswith(_BEARER_PREFIX):
        return None
    token = authorization[len(_BEARER_PREFIX) :]
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[JWT_ALGO])
    except JWTError:
        return None
    user_id = payload.get("sub")
    return user_id if isinstance(user_id, str) and user_id else None


async def get_current_user_id(authorization: str = Header(None)) -> str:
    """로그인을 요구하는 엔드포인트용. 토큰이 없거나 틀리면 401."""
    user_id = decode_user_id(authorization)
    if user_id is None:
        raise HTTPException(status_code=401, detail="로그인이 필요합니다.")
    return user_id


async def get_optional_user_id(authorization: str = Header(None)) -> str | None:
    """로그인을 요구하지 않는 엔드포인트용. 토큰이 있으면 쓰고 없으면 None.

    잘못된 토큰도 막지 않는다 — 업로드 자체는 익명으로도 가능해야 한다.
    """
    return decode_user_id(authorization)
