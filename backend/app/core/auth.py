"""
core/auth.py — JWT 에서 사용자를 꺼내는 공용 의존성과 가입 잠금.

업로드는 한때 비로그인으로도 가능했다. 공개 URL 에 올리면서 그 설계를 접었다 —
주소를 숨길 수 없고(NEXT_PUBLIC_API_URL 은 프론트 번들에 박힌다), 무료
인스턴스는 낯선 사람의 업로드 몇 건으로 막힌다. R2 용량과 Gemini 할당량도
함께 나간다.
"""
from __future__ import annotations

import secrets

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


def verify_invite_code(provided: str | None) -> None:
    """초대 코드가 맞지 않으면 403.

    설정이 비어 있으면 가입을 닫는다. 기본값이 '열림'이면 환경변수를 빠뜨린
    배포가 곧바로 공개 가입이 되므로, 안전한 쪽으로 기울여 둔다.
    비교는 compare_digest 로 한다 — 비밀값 비교의 표준 관행이다.
    """
    expected = settings.INVITE_CODE
    if not expected:
        raise HTTPException(status_code=403, detail="현재 회원가입이 닫혀 있습니다.")
    if provided is None or not secrets.compare_digest(provided, expected):
        raise HTTPException(status_code=403, detail="초대 코드가 올바르지 않습니다.")
