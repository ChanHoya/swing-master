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


async def test_returns_rule_result_when_response_is_not_a_dict(monkeypatch):
    """LLM 응답 최상위가 dict 가 아니면(list 등) 규칙 결과를 그대로 쓴다."""
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    with patch("app.services.feedback.llm._request", new=AsyncMock(return_value=["oops"])):
        assert await polish(_RULE_RESULT) == _RULE_RESULT


async def test_null_list_fields_do_not_crash(monkeypatch):
    """top_issues/drills 가 null 로 와도 죽지 않고 규칙 결과를 유지한다.

    dict.get(key, [])는 키가 없을 때만 기본값을 주므로, {"top_issues": null}
    처럼 키는 있지만 값이 None 이면 zip(list, None)이 TypeError 를 던졌던 버그.
    """
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    tampered = {"top_issues": None, "drills": None}
    with patch("app.services.feedback.llm._request", new=AsyncMock(return_value=tampered)):
        result = await polish(_RULE_RESULT)
    assert result["overall_score"] == 68
    assert result["grade"] == "C"
    assert len(result["top_issues"]) == 1
    assert len(result["drills"]) == 1


async def test_wrong_type_list_fields_do_not_crash(monkeypatch):
    """top_issues/drills 가 리스트가 아닌 타입(string, dict)으로 와도 무시한다."""
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    tampered = {"top_issues": "oops", "drills": {"a": 1}}
    with patch("app.services.feedback.llm._request", new=AsyncMock(return_value=tampered)):
        result = await polish(_RULE_RESULT)
    assert result["overall_score"] == 68
    assert result["grade"] == "C"
    assert len(result["top_issues"]) == 1
    assert len(result["drills"]) == 1


async def test_more_issues_and_drills_from_llm_are_not_added(monkeypatch):
    """LLM 이 규칙 엔진보다 많은 항목을 보내도 개수는 늘어나지 않는다."""
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    tampered = {
        "top_issues": [
            {"feedback": "다듬은 문장 1"},
            {"feedback": "LLM 이 지어낸 문제"},
        ],
        "drills": [
            {"tip": "다듬은 팁 1"},
            {"tip": "LLM 이 지어낸 드릴"},
        ],
    }
    with patch("app.services.feedback.llm._request", new=AsyncMock(return_value=tampered)):
        result = await polish(_RULE_RESULT)
    assert result["overall_score"] == 68
    assert result["grade"] == "C"
    assert len(result["top_issues"]) == 1
    assert len(result["drills"]) == 1
    assert result["top_issues"][0]["feedback"] == "다듬은 문장 1"
    assert result["drills"][0]["tip"] == "다듬은 팁 1"


async def test_fewer_issues_and_drills_from_llm_do_not_drop_entries(monkeypatch):
    """LLM 이 규칙 엔진보다 적은 항목(빈 리스트 포함)을 보내도 기존 항목이 사라지지 않는다."""
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    tampered = {"top_issues": [], "drills": []}
    with patch("app.services.feedback.llm._request", new=AsyncMock(return_value=tampered)):
        result = await polish(_RULE_RESULT)
    assert result["overall_score"] == 68
    assert result["grade"] == "C"
    assert len(result["top_issues"]) == 1
    assert len(result["drills"]) == 1
    assert result["top_issues"][0]["feedback"] == _RULE_RESULT["top_issues"][0]["feedback"]
    assert result["drills"][0]["tip"] == _RULE_RESULT["drills"][0]["tip"]
