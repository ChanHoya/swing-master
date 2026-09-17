import pytest

from app.services.feedback.drills import DRILLS
from app.services.feedback.rules import RULES, evaluate, score_metric


def _payload(**values):
    """지표 페이로드를 만든다. 값이 None 이면 측정 실패."""
    return {
        key: {
            "value": value,
            "confidence": 0.9 if value is not None else 0.0,
            "unit": RULES[key].unit,
            "measurable": True,
        }
        for key, value in values.items()
    }


def test_every_rule_has_a_drill():
    """진단만 하고 처방이 없으면 사용자가 할 수 있는 일이 없다."""
    for key in RULES:
        assert key in DRILLS, f"{key} 에 대응하는 드릴이 없다"


def test_drill_has_korean_steps():
    for key, drill in DRILLS.items():
        assert drill["drill_name"], key
        assert len(drill["steps"]) >= 2, key
        assert drill["repetitions"], key


def test_perfect_value_scores_one_hundred():
    assert score_metric("spine_angle", RULES["spine_angle"].ideal) == 100


def test_score_decreases_as_value_deviates():
    ideal = RULES["spine_angle"].ideal
    near = score_metric("spine_angle", ideal + 3.0)
    far = score_metric("spine_angle", ideal + 20.0)
    assert 100 > near > far >= 0


def test_score_is_clamped_to_zero():
    assert score_metric("spine_angle", 1000.0) == 0


def test_evaluate_ignores_unmeasured_metrics():
    """측정 실패한 지표가 점수를 끌어내리면 안 된다."""
    result = evaluate(_payload(spine_angle=37.0, knee_flex=None))
    assert result["overall_score"] == 100


def test_evaluate_returns_grade_for_score():
    assert evaluate(_payload(spine_angle=37.0))["grade"] == "A"
    assert evaluate(_payload(spine_angle=1000.0))["grade"] == "D"


def test_evaluate_ranks_worst_issues_first():
    result = evaluate(_payload(spine_angle=37.0, knee_flex=90.0, tempo_ratio=0.2))
    order = {"high": 0, "medium": 1, "low": 2}
    severities = [i["severity"] for i in result["top_issues"]]
    assert severities == sorted(severities, key=lambda s: order[s])


def test_evaluate_returns_at_most_three_issues():
    payload = _payload(
        spine_angle=1000.0, knee_flex=1000.0, tempo_ratio=0.01,
        head_movement=90.0, weight_shift=0.0,
    )
    assert len(evaluate(payload)["top_issues"]) <= 3


def test_evaluate_with_nothing_measured_says_so_in_korean():
    result = evaluate(_payload(spine_angle=None))
    assert result["overall_score"] is None
    assert "측정" in result["encouragement"]


def test_issue_feedback_is_korean_and_specific():
    result = evaluate(_payload(spine_angle=80.0))
    issue = result["top_issues"][0]
    assert issue["metric"] == "spine_angle"
    assert len(issue["feedback"]) > 10


def test_drills_match_reported_issues():
    """이슈로 뽑힌 지표에 대해서만 드릴이 나와야 한다."""
    result = evaluate(_payload(spine_angle=80.0, knee_flex=25.0))
    issue_metrics = {i["metric"] for i in result["top_issues"]}
    drill_metrics = {d["issue_metric"] for d in result["drills"]}
    assert drill_metrics == issue_metrics


@pytest.mark.parametrize(
    "word,expected",
    [("척추 각도", "가"), ("무릎 굴곡", "이"), ("템포 비율", "이"),
     ("어깨 회전", "이"), ("헤드 무브먼트", "가"), ("X-팩터", "가")],
)
def test_subject_particle_matches_final_consonant(word, expected):
    """받침이 있으면 '이', 없으면 '가'."""
    from app.services.feedback.rules import _subject_particle

    assert _subject_particle(word) == expected


def test_feedback_sentence_uses_correct_particle():
    result = evaluate(_payload(knee_flex=5.0))
    assert "무릎 굴곡이" in result["top_issues"][0]["feedback"]
