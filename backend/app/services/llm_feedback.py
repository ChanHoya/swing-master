"""
llm_feedback.py — 하위 호환 래퍼.

진단·점수·드릴은 app.services.feedback.rules 가 확정하고,
app.services.feedback.llm 은 문장만 다듬는다.
"""
from app.services.feedback.llm import polish
from app.services.feedback.rules import evaluate

__all__ = ["evaluate", "polish"]
