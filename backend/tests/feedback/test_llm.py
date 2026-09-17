from unittest.mock import AsyncMock, patch

import pytest

from app.services.feedback.llm import polish

_RULE_RESULT = {
    "overall_score": 68,
    "grade": "C",
    "top_issues": [{
        "metric": "spine_angle", "label": "척추 각도",
        "severity": "medium", "score": 62,
        "feedback": "척추 각도가 55.0°로 측정됐습니다(기준 37.0°).",
    }],
    "drills": [{"issue_metric": "spine_angle", "drill_name": "벽 기대기 어드레스",
                "steps": ["1", "2"], "repetitions": "10회", "tip": "고관절에서 접으세요."}],
    "encouragement": "기본기는 잡혀 있습니다.",
}


async def test_returns_rule_result_when_api_key_missing(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setattr("app.services.feedback.llm.settings.GEMINI_API_KEY", "")
    assert await polish(_RULE_RESULT) == _RULE_RESULT


async def test_returns_rule_result_when_request_fails(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    with patch("app.services.feedback.llm._request", new=AsyncMock(side_effect=RuntimeError("boom"))):
        assert await polish(_RULE_RESULT) == _RULE_RESULT


async def test_scores_are_never_overwritten_by_llm(monkeypatch):
    """LLM이 점수를 바꿔도 규칙 엔진 결과가 이긴다."""
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    tampered = {"overall_score": 99, "grade": "A", "encouragement": "다듬은 문장"}
    with patch("app.services.feedback.llm._request", new=AsyncMock(return_value=tampered)):
        result = await polish(_RULE_RESULT)
    assert result["overall_score"] == 68
    assert result["grade"] == "C"
    assert result["encouragement"] == "다듬은 문장"


async def test_drill_list_length_is_preserved(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    with patch("app.services.feedback.llm._request", new=AsyncMock(return_value={"drills": []})):
        result = await polish(_RULE_RESULT)
    assert len(result["drills"]) == 1
