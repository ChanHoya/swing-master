"""
feedback/rules.py — 지표에서 진단·점수·등급을 확정한다.

LLM 없이 완결된다. LLM은 이 결과의 문장을 다듬을 뿐이다.
기존 llm_feedback.py 는 LLM이 진단까지 만들었고, 실패하면 빈 껍데기가 나갔다.
관계를 뒤집어 규칙이 확정하고 LLM이 거드는 구조로 바꾼다.
"""
from __future__ import annotations

from dataclasses import dataclass

from app.services.feedback.drills import DRILLS

_SEVERITY_ORDER = {"high": 0, "medium": 1, "low": 2}


@dataclass(frozen=True)
class MetricRule:
    key: str
    label_ko: str
    unit: str
    ideal: float
    tolerance: float  # 이 폭만큼 벗어나면 100점에서 0점이 된다
    low_msg: str  # 기준보다 낮을 때
    high_msg: str  # 기준보다 높을 때


RULES: dict[str, MetricRule] = {
    "spine_angle": MetricRule(
        "spine_angle", "척추 각도", "°", 37.0, 25.0,
        "상체가 너무 서 있습니다. 고관절에서 조금 더 숙여 주세요.",
        "상체를 과하게 숙였습니다. 조금 더 세워서 시야를 확보하세요.",
    ),
    "knee_flex": MetricRule(
        "knee_flex", "무릎 굴곡", "°", 25.0, 20.0,
        "무릎이 거의 펴져 있어 하체가 버텨 주지 못합니다.",
        "무릎을 너무 굽혀 회전이 막힙니다. 살짝만 굽히세요.",
    ),
    "shoulder_rotation": MetricRule(
        "shoulder_rotation", "어깨 회전", "°", 90.0, 45.0,
        "어깨 회전이 부족해 비거리가 손해를 봅니다.",
        "어깨가 과하게 돌아 임팩트에서 정확도가 떨어집니다.",
    ),
    "hip_rotation": MetricRule(
        "hip_rotation", "힙 회전", "°", 45.0, 30.0,
        "골반 회전이 부족합니다. 하체가 멈춰 있습니다.",
        "골반이 과하게 돌아 상하체 분리가 사라졌습니다.",
    ),
    "x_factor": MetricRule(
        "x_factor", "X-팩터", "°", 45.0, 35.0,
        "상하체 분리가 부족해 파워가 새고 있습니다.",
        "분리가 과해 몸에 무리가 갈 수 있습니다.",
    ),
    "head_movement": MetricRule(
        "head_movement", "헤드 무브먼트", "cm", 2.0, 10.0,
        "",  # 0에 가까울수록 좋으므로 낮을 때 지적할 것이 없다
        "머리가 많이 움직여 임팩트가 불안정합니다.",
    ),
    "weight_shift": MetricRule(
        "weight_shift", "체중 이동(추정)", "%", 15.0, 15.0,
        "체중이 뒤에 남아 있습니다. 타겟 쪽으로 밀어 주세요.",
        "체중이 과하게 앞으로 쏠려 균형이 무너집니다.",
    ),
    "tempo_ratio": MetricRule(
        "tempo_ratio", "템포 비율", ":1", 3.0, 2.0,
        "백스윙이 너무 빠릅니다. 조금 더 여유 있게 올리세요.",
        "백스윙이 너무 느려 리듬이 끊깁니다.",
    ),
}


def _subject_particle(word: str) -> str:
    """받침 유무에 따라 주격 조사를 고른다 ("척추 각도가" / "무릎 굴곡이").

    한글 음절은 유니코드에서 0xAC00 부터 28개씩 묶여 있고, 그 안에서의
    위치가 곧 종성 번호다. 0이면 받침이 없다.
    """
    last = word[-1]
    if not ("가" <= last <= "힣"):
        return "가"  # 한글이 아니면(숫자·영문) 기본값
    return "이" if (ord(last) - 0xAC00) % 28 else "가"


def score_metric(key: str, value: float) -> int:
    """기준값에서 벗어난 정도를 0~100 점수로 바꾼다."""
    rule = RULES[key]
    deviation = abs(value - rule.ideal)
    score = 100.0 * (1.0 - deviation / rule.tolerance)
    return int(max(0.0, min(100.0, score)))


def _severity(score: int) -> str:
    if score < 50:
        return "high"
    if score < 75:
        return "medium"
    return "low"


def _grade(score: int) -> str:
    if score >= 85:
        return "A"
    if score >= 70:
        return "B"
    if score >= 55:
        return "C"
    return "D"


def evaluate(payload: dict) -> dict:
    """지표 페이로드에서 진단·점수·드릴을 만든다.

    측정되지 않은 지표는 점수 계산에서 제외한다.
    측정된 것이 하나도 없으면 overall_score 는 None 이다.
    없는 점수를 지어내지 않는다.
    """
    scored: list[tuple[str, float, int]] = []
    for key in RULES:
        entry = payload.get(key)
        if not entry or entry.get("value") is None:
            continue
        value = float(entry["value"])
        scored.append((key, value, score_metric(key, value)))

    if not scored:
        return {
            "overall_score": None,
            "grade": None,
            "top_issues": [],
            "drills": [],
            "encouragement": (
                "이번 영상에서는 지표를 측정하지 못했습니다. "
                "전신이 화면에 들어오도록 조금 더 멀리서 다시 촬영해 주세요."
            ),
        }

    overall = int(round(sum(s for _, _, s in scored) / len(scored)))

    issues = []
    for key, value, score in sorted(scored, key=lambda t: t[2]):
        if score >= 75:
            continue
        rule = RULES[key]
        message = rule.high_msg if value > rule.ideal else rule.low_msg
        if not message:
            message = rule.high_msg or rule.low_msg
        issues.append(
            {
                "metric": key,
                "label": rule.label_ko,
                "severity": _severity(score),
                "score": score,
                "feedback": (
                    f"{rule.label_ko}{_subject_particle(rule.label_ko)} "
                    f"{value}{rule.unit}로 측정됐습니다"
                    f"(기준 {rule.ideal}{rule.unit}). {message}"
                ),
            }
        )
    issues = sorted(issues, key=lambda i: _SEVERITY_ORDER[i["severity"]])[:3]

    drills = [{"issue_metric": i["metric"], **DRILLS[i["metric"]]} for i in issues]

    if overall >= 85:
        encouragement = "안정적인 스윙입니다. 지금 감각을 유지하세요."
    elif overall >= 70:
        encouragement = "기본기는 잡혀 있습니다. 위 드릴로 한 단계 더 올려 보세요."
    else:
        encouragement = "고칠 지점이 뚜렷합니다. 드릴 하나씩만 집중해 보세요."

    return {
        "overall_score": overall,
        "grade": _grade(overall),
        "top_issues": issues,
        "drills": drills,
        "encouragement": encouragement,
    }
