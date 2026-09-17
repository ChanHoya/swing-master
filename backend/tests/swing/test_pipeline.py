from app.services.swing.pipeline import PHASE_LABELS, summarise_metrics
from app.services.swing.types import PHASE_KEYS


def test_phase_labels_cover_all_seven_phases_in_korean():
    assert set(PHASE_LABELS) == set(PHASE_KEYS)
    assert PHASE_LABELS["impact"] == "5.임팩트"
    assert PHASE_LABELS["address"] == "1.어드레스"


def test_summarise_counts_only_measured_metrics():
    payload = {
        "spine_angle": {"value": 35.0, "confidence": 0.9, "unit": "°", "measurable": True},
        "knee_flex": {"value": None, "confidence": 0.0, "unit": "°", "measurable": True},
        "x_factor": {"value": None, "confidence": 0.0, "unit": "°", "measurable": False},
    }
    summary = summarise_metrics(payload)
    assert summary["measured_count"] == 1
    assert summary["total_count"] == 3


def test_summarise_reports_zero_when_nothing_measured():
    payload = {
        "spine_angle": {"value": None, "confidence": 0.0, "unit": "°", "measurable": True},
    }
    assert summarise_metrics(payload)["measured_count"] == 0
