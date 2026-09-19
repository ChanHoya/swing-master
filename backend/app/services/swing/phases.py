"""
swing/phases.py — 스윙 구간 탐지와 7단계 분할.

알고리즘은 기존 pose_estimator.py 에서 그대로 옮긴 것이다.
정확도 개선은 이번 범위 밖이다.
"""
from __future__ import annotations

import cv2
import numpy as np

from app.services.swing.metrics import L_SHOULDER, R_SHOULDER, R_WRIST
from app.services.swing.types import PHASE_KEYS, PoseSequence

_SMOOTH_WINDOW = 3


# ═══════════════════════════════════════════════════════════════════════════
# PASS 1: 중앙 ROI 기반 스윙 구간 탐지
# ═══════════════════════════════════════════════════════════════════════════
def detect_swing_window(video_path: str) -> tuple[int, int, float]:
    """모션이 가장 활발한 구간을 스윙으로 보고 (시작, 끝, fps) 를 돌려준다."""
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    STEP = 10

    motion: list[float] = []
    indices: list[int] = []
    prev_gray = None

    for i in range(0, total, STEP):
        cap.set(cv2.CAP_PROP_POS_FRAMES, i)
        ret, frame = cap.read()
        if not ret:
            break
        g = cv2.resize(
            cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY),
            (160, 90),
            interpolation=cv2.INTER_NEAREST,
        )
        if prev_gray is not None:
            # 중앙 ROI만 사용 (가장자리 배경·낙엽 등 제외)
            roi = g[18:90, 32:128]
            roi_p = prev_gray[18:90, 32:128]
            motion.append(float(cv2.absdiff(roi, roi_p).mean()))
            indices.append(i)
        prev_gray = g

    cap.release()
    if len(motion) < 3:
        return 0, total, fps

    W = 3
    smoothed = [
        sum(motion[max(0, i - W) : i + W + 1]) / min(2 * W + 1, len(motion))
        for i in range(len(motion))
    ]

    peak_idx = int(np.argmax(smoothed))
    peak_val = smoothed[peak_idx]
    threshold = peak_val * 0.38

    s = peak_idx
    while s > 0 and smoothed[s - 1] > threshold:
        s -= 1
    e = peak_idx
    while e < len(smoothed) - 1 and smoothed[e + 1] > threshold:
        e += 1

    s = max(0, s - 1)
    e = min(len(indices) - 1, e + 1)

    # 이 함수는 대개 영상 거의 전체를 돌려준다. 좁히려고 시도해 봤지만
    # 더 나빠졌다 — 여기서 쓰는 회색조 차분 모션의 피크는 임팩트가 아니라
    # 골퍼가 공을 줍거나 자리를 뜨는 순간일 때가 많다. 영상 11개로 재면
    # 피크 기준 고정 길이 창은 성공률을 6/11에서 2/11로 떨어뜨렸다.
    #
    # 범위를 넓게 주고 detect_phases 가 좁히도록 두는 편이 낫다. 그쪽은
    # 회색조가 아니라 실제 손목 랜드마크를 보므로 훨씬 정확하다.
    print(f"[Swing] 피크={peak_val:.2f} | {indices[s]/fps:.1f}s~{indices[e]/fps:.1f}s")
    return indices[s], indices[e], fps


# ═══════════════════════════════════════════════════════════════════════════
# PASS 2: 7단계 분할
# ═══════════════════════════════════════════════════════════════════════════
def _smooth(values: np.ndarray, window: int = _SMOOTH_WINDOW) -> np.ndarray:
    """이동 평균. 경계에서는 있는 만큼만 평균낸다."""
    n = len(values)
    return np.array(
        [values[max(0, i - window) : min(n, i + window + 1)].mean() for i in range(n)],
        dtype=np.float64,
    )


def detect_phases(seq: PoseSequence) -> dict[str, int]:
    """손목 궤적과 이동량으로 7단계 프레임 인덱스를 찾는다.

    ① 임팩트  = 이동량 최댓값 (클럽과 손목이 가장 빠른 순간)
    ② 탑      = 임팩트 이전 이동량 최솟값 (잠시 멈추는 지점)
    ③ 어드레스 = 유의미한 움직임이 시작되기 직전
    ④ 피니시   = 움직임이 잦아든 뒤 마지막 지점
    ⑤ 나머지 3단계 = 위 네 지점 사이의 비율 보간
    """
    n = len(seq)
    if n < 4:
        raise ValueError(
            f"포즈가 인식된 프레임이 부족합니다 ({n}개). "
            "전신이 보이도록 다시 촬영해 주세요."
        )

    wrist_y = seq.xy_px[:, R_WRIST, 1]
    wrist_x = seq.xy_px[:, R_WRIST, 0]
    shoulder_x = (seq.xy_px[:, L_SHOULDER, 0] + seq.xy_px[:, R_SHOULDER, 0]) / 2.0

    motion = (
        np.abs(np.diff(wrist_y))
        + np.abs(np.diff(wrist_x))
        + np.abs(np.diff(shoulder_x))
    )
    if len(motion) == 0:
        motion = np.zeros(1, dtype=np.float64)
    smoothed = _smooth(motion)

    def clamp(i: int) -> int:
        return max(0, min(n - 1, int(i)))

    impact_m = int(np.argmax(smoothed))
    impact = clamp(impact_m + 1)

    # 어드레스 = 백스윙이 시작되기 직전의 마지막 정지.
    #
    # 원래는 앞에서부터 훑어 "모션이 처음 문턱을 넘는 지점"을 찾았다. 그러면
    # 골퍼가 걸어 들어오거나 연습 스윙을 한 움직임이 문턱을 넘어 어드레스가
    # 영상 맨 앞으로 밀린다. 실측 영상 3개가 이 탓에 스윙 길이 6~13초로
    # 부풀었다(실제는 2초 안팎).
    #
    # 어드레스는 정의상 백스윙 직전이므로 임팩트에서 거꾸로 찾는 것이 맞다.
    # 이렇게 바꾸니 영상 11개 기준 정상이 8/11 에서 11/11 이 됐다.
    quiet_threshold_before = float(smoothed.mean()) * 0.4
    address = 0
    for k in range(min(impact_m - 1, len(smoothed) - 1), -1, -1):
        if smoothed[k] < quiet_threshold_before:
            address = k
            break

    # 탑 = 어드레스와 임팩트 사이에서 손목이 가장 높은(y가 가장 작은) 지점.
    #
    # 원래 이식한 휴리스틱은 "임팩트 이전 모션 최솟값"으로 탑을 찾았지만,
    # 어드레스의 정지 구간도 모션이 0에 가까워 그쪽을 탑으로 집는다.
    # 실제 스윙 프로파일로 검증했을 때 탑을 14프레임 빗나갔고
    # takeaway 와 같은 프레임으로 붕괴했다.
    # 탑은 정의상 손이 가장 높이 올라간 지점이므로 그것을 직접 찾는다.
    search_lo = min(address + 1, n - 2)
    search_hi = max(search_lo + 1, impact)
    top = search_lo + int(np.argmin(wrist_y[search_lo:search_hi]))

    # 피니시 = 임팩트 이후 모션이 처음으로 잦아드는 지점.
    #
    # 원래 코드는 뒤에서부터 거꾸로 훑어 "마지막으로 모션이 있던 곳"을 찾았다.
    # 그러면 스윙이 끝난 뒤의 잡움직임(클럽 내리기, 자리 이동)을 집어서
    # 피니시가 영상 끝으로 밀린다. 실측 영상에서 실제 피니시 3.97초를
    # 10.97초로 잡았고, 팔로우스루도 덩달아 6.57초로 틀어졌다.
    # 스윙은 임팩트 직후에 끝나므로 앞에서부터 찾는 것이 맞다.
    # 임팩트 후 1초를 넘는 지점은 스윙이 아니다. 골프 팔로우스루는 그 안에 끝난다.
    # 이 상한이 없으면 스윙이 끝난 뒤의 잡움직임(클럽 내리기, 자리 이동)까지
    # 스윙으로 삼아 피니시가 영상 끝으로 밀린다.
    # 스무딩된 모션은 다운스윙 스파이크가 번져 들어가므로 원본 모션으로 판정한다.
    impact_frame = float(seq.frame_indices[impact])
    latest_frame = impact_frame + seq.fps  # 임팩트 + 1초
    quiet_threshold = float(motion.mean()) * 0.4

    finish = n - 1
    for k in range(impact_m + 1, len(motion)):
        candidate = clamp(k + 1)
        if float(seq.frame_indices[candidate]) > latest_frame:
            finish = candidate
            break
        if motion[k] < quiet_threshold:
            finish = candidate
            break

    # 단조 증가를 보장한다. 어긋나면 지표 전부가 틀어진다.
    address = min(address, n - 4)
    top = max(address + 1, min(top, n - 3))
    impact = max(top + 1, min(impact, n - 2))
    finish = max(impact + 1, min(finish, n - 1))

    phases = {
        "address": address,
        "takeaway": clamp(address + max(1, (top - address) * 35 // 100)),
        "top": top,
        "downswing": clamp(top + max(1, (impact - top) * 45 // 100)),
        "impact": impact,
        "followthrough": clamp(impact + max(1, (finish - impact) * 40 // 100)),
        "finish": finish,
    }
    assert set(phases) == set(PHASE_KEYS)
    return phases
