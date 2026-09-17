"""
pose_estimator.py — 하위 호환 래퍼.

실제 구현은 app.services.swing 패키지로 옮겼다.
새 코드는 app.services.swing.pipeline 을 직접 import 할 것.
"""
from app.services.swing.pipeline import process_pose_estimation

__all__ = ["process_pose_estimation"]
