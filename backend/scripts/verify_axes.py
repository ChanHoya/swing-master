"""
MediaPipe world landmark 축 방향 검증.

설계 문서(docs/superpowers/specs/2026-09-16-supervision-metrics-upgrade-design.md)
§6에서 최상위 리스크로 지목한 항목이다. 문서만 보고 확정하면 안 되고,
실제 스윙 영상으로 확인해야 한다. 부호가 반대면 회전 지표가 통째로 뒤집힌다.

사용법:
    cd backend && .venv/bin/python scripts/verify_axes.py <영상경로>

코드가 세운 가정:
  - y축은 아래가 양수  → 어깨의 y 가 힙의 y 보다 작아야 한다
  - 원점은 힙 중심     → 힙 중점의 좌표가 0에 가까워야 한다
  - z축은 깊이         → 몸이 돌면 어깨의 수평각이 크게 변해야 한다
"""
import os
import sys

import numpy as np

# scripts/ 아래에서 직접 실행되므로 backend/ 를 경로에 넣어야 app 을 찾는다.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.swing.metrics import (  # noqa: E402
    L_HIP,
    L_SHOULDER,
    R_HIP,
    R_SHOULDER,
    horizontal_angle,
)
from app.services.swing.pose import extract_sequence  # noqa: E402


def main(video_path: str) -> int:
    seq = extract_sequence(video_path, start_frame=0, end_frame=10_000)
    print(f"인식 프레임 수: {len(seq)}, fps={seq.fps}, 해상도={seq.resolution_wh}")

    first = seq.world[0]
    shoulder_y = (first[L_SHOULDER][1] + first[R_SHOULDER][1]) / 2
    hip_y = (first[L_HIP][1] + first[R_HIP][1]) / 2
    hip_centre = (first[L_HIP] + first[R_HIP]) / 2

    passed = True

    print("\n[가정 1] y축 아래가 양수 → 어깨 y < 힙 y")
    print(f"  어깨 y = {shoulder_y:+.4f}, 힙 y = {hip_y:+.4f}")
    ok1 = shoulder_y < hip_y
    print(f"  판정: {'통과' if ok1 else '실패 — 부호 반전 필요'}")
    passed &= ok1

    print("\n[가정 2] 원점은 힙 중심 → 힙 중점이 (0, 0, 0) 근처")
    print(f"  힙 중점 = {np.round(hip_centre, 4)}")
    ok2 = float(np.linalg.norm(hip_centre)) < 0.05
    print(f"  판정: {'통과' if ok2 else '실패 — 원점 가정 재검토'}")
    passed &= ok2

    angles = [horizontal_angle(f[L_SHOULDER], f[R_SHOULDER]) for f in seq.world]
    span = max(angles) - min(angles)
    print("\n[가정 3] z축이 깊이 → 스윙 중 어깨 수평각이 크게 변한다")
    print(f"  최소 {min(angles):+.1f}°, 최대 {max(angles):+.1f}°, 변화폭 {span:.1f}°")
    ok3 = span > 30.0
    print(f"  판정: {'통과' if ok3 else '실패 — 축 해석 재검토'}")
    passed &= ok3

    print(
        f"\n종합: {'세 가정 모두 통과' if passed else '실패 항목 있음 — 설계 문서 §6 참조'}"
    )
    return 0 if passed else 1


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("사용법: python scripts/verify_axes.py <영상경로>")
        raise SystemExit(2)
    raise SystemExit(main(sys.argv[1]))
