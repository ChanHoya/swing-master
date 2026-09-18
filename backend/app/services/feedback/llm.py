"""
feedback/llm.py — 규칙 엔진 결과의 한국어 문장만 다듬는다.

점수·등급·드릴 구성은 규칙 엔진이 확정한 것을 쓴다.
LLM이 죽어도 입력이 그대로 나가므로 서비스가 멈추지 않는다.
"""
from __future__ import annotations

import json
import logging
import os

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

_MODELS = [
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite",
    "gemini-2.0-flash-lite-001",
]
_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

_SYSTEM = (
    "당신은 한국의 아마추어 골퍼를 20년간 가르쳐 온 프로 골프 코치입니다. "
    "주어진 진단 결과의 숫자와 판단은 그대로 두고, 문장만 따뜻하고 자연스러운 "
    "한국어로 다듬으세요. 새로운 진단이나 드릴을 만들지 마세요."
)


def _api_key() -> str:
    """설정 경로를 한 곳으로 모은다.

    기존 llm_feedback.py 는 os.getenv 로 따로 읽어 설정이 이원화돼 있었다.
    """
    return settings.GEMINI_API_KEY or os.getenv("GEMINI_API_KEY", "")


async def _request(prompt: str, api_key: str) -> dict:
    """Gemini 호출. 모델 목록을 순서대로 시도한다."""
    payload = {
        "system_instruction": {"parts": [{"text": _SYSTEM}]},
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"responseMimeType": "application/json", "temperature": 0.7},
    }
    headers = {"x-goog-api-key": api_key, "Content-Type": "application/json"}

    last_error: Exception | None = None
    async with httpx.AsyncClient(timeout=20.0) as client:
        for model in _MODELS:
            try:
                response = await client.post(
                    _URL.format(model=model), json=payload, headers=headers
                )
                if response.status_code in (429, 503):
                    continue
                response.raise_for_status()
                text = response.json()["candidates"][0]["content"]["parts"][0]["text"]
                return json.loads(text)
            except Exception as exc:  # noqa: BLE001 - 다음 모델로 넘어간다
                last_error = exc
    raise RuntimeError(f"모든 모델 실패: {last_error}")


def _as_list(value: object) -> list:
    """polished[key] 가 리스트가 아니면 빈 리스트로 취급한다.

    dict.get(key, [])는 키가 '없을' 때만 기본값을 준다. LLM이
    {"top_issues": null} 처럼 키는 있지만 타입이 틀린 값을 보내면
    None 이 그대로 나와 zip(list, None) 이 TypeError 를 던진다.
    신뢰할 수 없는 응답이므로 존재 여부가 아니라 타입으로 걸러야 한다.
    """
    return value if isinstance(value, list) else []


def _merge(rule_result: dict, polished: dict) -> dict:
    """규칙 엔진이 확정한 값은 LLM이 덮어쓸 수 없다.

    polished 는 신뢰할 수 없는 입력이므로 각 필드를 타입 검증한 뒤에만 쓴다.
    """
    result = dict(rule_result)
    if isinstance(polished.get("encouragement"), str):
        result["encouragement"] = polished["encouragement"]

    result["top_issues"] = [dict(issue) for issue in result.get("top_issues", [])]
    for target, source in zip(result["top_issues"], _as_list(polished.get("top_issues"))):
        if isinstance(source, dict) and isinstance(source.get("feedback"), str):
            target["feedback"] = source["feedback"]

    result["drills"] = [dict(drill) for drill in result.get("drills", [])]
    for target, source in zip(result["drills"], _as_list(polished.get("drills"))):
        if isinstance(source, dict) and isinstance(source.get("tip"), str):
            target["tip"] = source["tip"]

    return result


async def polish(rule_result: dict) -> dict:
    """문장만 다듬은 결과를 돌려준다. 실패하면 입력 그대로."""
    api_key = _api_key()
    if not api_key:
        logger.info("GEMINI_API_KEY 없음 — 규칙 엔진 결과를 그대로 사용")
        return rule_result

    prompt = (
        "아래 골프 스윙 진단 결과의 feedback·tip·encouragement 문장만 "
        "자연스러운 한국어로 다듬어 같은 JSON 구조로 돌려주세요. "
        "숫자·점수·등급·드릴 이름은 바꾸지 마세요.\n\n"
        + json.dumps(rule_result, ensure_ascii=False)
    )

    try:
        polished = await _request(prompt, api_key)
    except Exception as exc:  # noqa: BLE001
        logger.warning("LLM 윤문 실패 — 규칙 결과 사용: %s", exc)
        return rule_result

    if not isinstance(polished, dict):
        logger.warning("LLM 응답이 JSON 객체가 아님 — 규칙 결과 사용")
        return rule_result

    try:
        return _merge(rule_result, polished)
    except Exception as exc:  # noqa: BLE001 - 신뢰할 수 없는 응답이므로 무엇이 와도 죽지 않는다
        logger.warning("LLM 응답 병합 실패 — 규칙 결과 사용: %s", exc)
        return rule_result
