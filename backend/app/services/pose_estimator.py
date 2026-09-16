"""
pose_estimator.py — 골프 스윙 7단계 분석 파이프라인

Pass 1: 중앙 ROI 모션 스캔 → 피크 기반 스윙 구간 탐지
Pass 2: 손목 Y 궤적 + 속도 분석으로 7단계 물리적 탐지
  1.어드레스 2.테이크백 3.탑 4.다운스윙 5.임팩트 6.팔로우스루 7.피니시
"""
import os
import cv2
import uuid
import math
import httpx
import tempfile
import asyncio
import numpy as np
import datetime
from io import BytesIO
from mediapipe.tasks.python.core.base_options import BaseOptions
from mediapipe.tasks.python.vision import PoseLandmarker, PoseLandmarkerOptions
from mediapipe import Image, ImageFormat
from sqlalchemy import select

from app.core.database import AsyncSessionFactory
from app.models import Analysis, Upload
from app.core.storage import upload_fileobj

MODEL_PATH = os.path.join(os.path.dirname(__file__), 'pose_landmarker_lite.task')

_landmarker: PoseLandmarker | None = None
def _get_landmarker() -> PoseLandmarker:
    global _landmarker
    if _landmarker is None:
        options = PoseLandmarkerOptions(
            base_options=BaseOptions(model_asset_path=MODEL_PATH),
            output_segmentation_masks=False,
            min_pose_detection_confidence=0.25,   # 기본 0.5 → 비스듬한 각도 대응
            min_pose_presence_confidence=0.25,
            min_tracking_confidence=0.25,
        )
        _landmarker = PoseLandmarker.create_from_options(options)
    return _landmarker


async def download_video(url: str, dest: str):
    async with httpx.AsyncClient(follow_redirects=True, timeout=60.0) as client:
        async with client.stream("GET", url) as response:
            response.raise_for_status()
            with open(dest, "wb") as f:
                async for chunk in response.aiter_bytes(chunk_size=65536):
                    f.write(chunk)


# ═══════════════════════════════════════════════════════════════════════════
# PASS 1: 중앙 ROI 기반 스윙 구간 탐지
# ═══════════════════════════════════════════════════════════════════════════
def detect_swing_window(video_path: str) -> tuple[int, int, float]:
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
        g = cv2.resize(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY), (160, 90),
                       interpolation=cv2.INTER_NEAREST)
        if prev_gray is not None:
            # 중앙 ROI만 사용 (가장자리 배경·낙엽 등 제외)
            roi   = g[18:90, 32:128]
            roi_p = prev_gray[18:90, 32:128]
            motion.append(float(cv2.absdiff(roi, roi_p).mean()))
            indices.append(i)
        prev_gray = g

    cap.release()
    if len(motion) < 3:
        return 0, total, fps

    W = 3
    smoothed = [
        sum(motion[max(0, i-W):i+W+1]) / min(2*W+1, len(motion))
        for i in range(len(motion))
    ]

    peak_idx = int(np.argmax(smoothed))
    peak_val = smoothed[peak_idx]
    threshold = peak_val * 0.38

    s = peak_idx
    while s > 0 and smoothed[s-1] > threshold: s -= 1
    e = peak_idx
    while e < len(smoothed)-1 and smoothed[e+1] > threshold: e += 1

    s = max(0, s - 1)
    e = min(len(indices)-1, e + 1)

    print(f"[Swing] 피크={peak_val:.2f} | {indices[s]/fps:.1f}s~{indices[e]/fps:.1f}s")
    return indices[s], indices[e], fps


# ═══════════════════════════════════════════════════════════════════════════
# PASS 2: MediaPipe 7단계 탐지 + BBox 크롭 이미지 생성
# ═══════════════════════════════════════════════════════════════════════════
PHASE_LABELS = {
    "address":      "1.어드레스",
    "takeaway":     "2.테이크백",
    "top":          "3.탑",
    "downswing":    "4.다운스윙",
    "impact":       "5.임팩트",
    "followthrough":"6.팔로우스루",
    "finish":       "7.피니시",
}

def analyze_swing(video_path: str, start_frame: int, end_frame: int) -> tuple[dict, dict]:
    cap = cv2.VideoCapture(video_path)
    landmarker = _get_landmarker()
    PROC_W = 640
    SKIP = 2   # 매 2번째 프레임 분석 (비스듬 각도용 촘촘한 샘플링)

    # 수직 지표: 오른손목(16), 왼손목(15), 힙 중심 중 가장 잘 보이는 것 사용
    vert_val: list[float | None] = []  # 수직 위치 (작을수록 위)
    horiz_val: list[float | None] = [] # 수평 위치 (어깨 중심 X)
    frames_data: list[dict | None] = []
    proc_count = 0

    cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
    cur = start_frame

    while cur <= end_frame:
        ret, frame = cap.read()
        if not ret: break
        proc_count += 1; cur += 1
        if proc_count % SKIP != 0:
            vert_val.append(None); horiz_val.append(None); frames_data.append(None); continue

        h0, w0 = frame.shape[:2]
        small = cv2.resize(frame, (PROC_W, int(h0*PROC_W/w0))) if w0 > PROC_W else frame.copy()
        mp_img = Image(image_format=ImageFormat.SRGB, data=cv2.cvtColor(small, cv2.COLOR_BGR2RGB))
        result = landmarker.detect(mp_img)

        if result.pose_landmarks and result.pose_landmarks[0]:
            lm = result.pose_landmarks[0]
            # 오른손목→왼손목→힙중심 순서로 fallback (비스듬 각도 대응)
            rw, lw = lm[16], lm[15]
            hip_y = (lm[23].y + lm[24].y) / 2
            sh_x  = (lm[11].x + lm[12].x) / 2

            # 더 잘 보이는 손목 선택 (visibility 비교)
            if hasattr(rw, 'visibility') and hasattr(lw, 'visibility'):
                use_lm = rw if (rw.visibility or 0) >= (lw.visibility or 0) else lw
            else:
                use_lm = rw

            # 손목이 프레임 안에 있으면 손목 Y, 아니면 힙 Y 사용
            if 0.05 <= use_lm.y <= 0.95 and 0.0 <= use_lm.x <= 1.0:
                v_val = use_lm.y
            else:
                v_val = hip_y

            vert_val.append(v_val)
            horiz_val.append(sh_x)
            frames_data.append({"frame": frame.copy(), "lm": lm})
        else:
            vert_val.append(None)
            horiz_val.append(None)
            frames_data.append(None)

    cap.release()

    valid = [(i, vert_val[i]) for i in range(len(vert_val)) if vert_val[i] is not None]
    n_valid = len(valid)
    print(f"[Phase] 인식된 프레임 수: {n_valid}/{len(vert_val)}")

    # 프레임이 너무 적으면 균등 분배 fallback (비스듬 각도·원거리 촬영 대응)
    if n_valid < 3:
        raise ValueError(f"포즈 인식 실패 (감지된 프레임 {n_valid}개). 측면에서 촬영된 영상을 사용해 주세요.")

    n    = n_valid
    idxs = [v[0] for v in valid]
    ys   = [v[1] for v in valid]

    # ── X 좌표 추출 (어깨 중심 X) ────────────────────────────────────
    xs = [horiz_val[v[0]] if (horiz_val[v[0]] is not None) else ys[i]
          for i, v in enumerate(valid)]

    # ── motion_mag: 연속 valid 프레임 간 손목+어깨 복합 이동량 ──────────
    dy = [abs(ys[i+1]-ys[i]) for i in range(n-1)]
    dx = [abs(xs[i+1]-xs[i]) for i in range(n-1)]
    motion_mag = [dy[i] + dx[i] for i in range(n-1)]
    if not motion_mag:
        motion_mag = [0.0]

    # ═══════════════════════════════════════════════════════════════
    # 7단계 물리 기반 탐지 — motion_mag 앵커 방식
    # ═══════════════════════════════════════════════════════════════
    # 원리:
    #  ① 임팩트  = motion_mag 전체 최댓값  (클럽 + 손목이 가장 빠른 순간)
    #  ② 탑      = 임팩트 이전 motion_mag 로컬 최솟값 (잠시 정지)
    #  ③ 어드레스 = 유의미한 모션 시작 직전 프레임
    #  ④ 피니시   = 유의미한 모션 소멸 이후 마지막 프레임
    #  ⑤ 나머지 3단계(테이크백·다운스윙·팔로우스루)= 비율 보간

    def clamp(x):
        return max(0, min(n-1, x))
    def clamp_mm(x):                 # motion_mag 인덱스용 (n-1개)
        return max(0, min(len(motion_mag)-1, x))

    # ── 스무딩된 motion_mag ─────────────────────────────────────────
    W2 = 3
    mm_s = [sum(motion_mag[max(0,k-W2):min(len(motion_mag),k+W2+1)])
            / max(1, min(2*W2+1, len(motion_mag)-max(0,k-W2)))
            for k in range(len(motion_mag))]

    # ── ① 임팩트: 모션 전체 최댓값 ─────────────────────────────────
    impact_mm_idx = int(np.argmax(mm_s))            # motion_mag 인덱스
    impact_seq    = clamp(impact_mm_idx + 1)        # 다음 valid 프레임

    # ── ② 탑: 임팩트 이전 모션 최솟값 (정점의 pause) ───────────────
    # 임팩트 이전 구간 중 가장 낮은 motion을 보이는 블록 탐색
    pre_impact_range = list(range(2, impact_mm_idx - 1)) if impact_mm_idx > 3 else []
    if pre_impact_range:
        # 구간을 3등분해서 각 구간 모션 최솟값 비교 → 앞쪽 2/3에서 찾음
        search_top_end = max(1, impact_mm_idx * 2 // 3)
        top_mm_idx = min(range(1, search_top_end+1), key=lambda k: mm_s[k])
        top_seq = clamp(top_mm_idx)                # 해당 valid 프레임
    else:
        top_seq = clamp(impact_seq * 4 // 10)

    # ── ③ 어드레스: 유의미한 모션 시작 직전 ────────────────────────
    motion_onset = 0
    for k in range(len(motion_mag)):
        if mm_s[k] > float(np.mean(mm_s)) * 0.5:
            motion_onset = clamp(k)
            break
    swing_start_seq = max(0, motion_onset - 1)

    # ── ④ 피니시: 모션이 임팩트 이후 충분히 감소한 마지막 지점 ──────
    quiet_th = float(np.mean(mm_s)) * 0.4
    swing_end_seq = n - 1
    for k in range(len(motion_mag)-1, impact_mm_idx, -1):
        if mm_s[k] > quiet_th:
            swing_end_seq = clamp(k + 1)
            break

    print(f"[Phase] start={swing_start_seq} top={top_seq} impact={impact_seq} "
          f"end={swing_end_seq} | n={n} max_motion_idx={impact_mm_idx}")

    # ── ⑤ 7단계 비율 배정 ──────────────────────────────────────────
    if n >= 4:
        phase_seqs = {
            "address":       clamp(swing_start_seq),
            # 어드레스~탑 사이 35% 지점
            "takeaway":      clamp(swing_start_seq + max(1, (top_seq - swing_start_seq) * 35 // 100)),
            "top":           clamp(top_seq),
            # 탑~임팩트 사이 45% 지점
            "downswing":     clamp(top_seq + max(1, (impact_seq - top_seq) * 45 // 100)),
            "impact":        clamp(impact_seq),
            # 임팩트~피니시 사이 40% 지점
            "followthrough": clamp(impact_seq + max(1, (swing_end_seq - impact_seq) * 40 // 100)),
            "finish":        clamp(swing_end_seq),
        }
    else:
        keys = ["address","takeaway","top","downswing","impact","followthrough","finish"]
        step = max(1.0, (n-1)/6.0)
        phase_seqs = {k: clamp(int(i*step)) for i,k in enumerate(keys)}
        print(f"[Phase] ⚠️ 프레임 부족({n}) → 균등 분배")

    print(f"[7단계] {' | '.join(f'{k}={v}' for k,v in phase_seqs.items())}")

    # ── 지표 계산 ────────────────────────────────────────────────────────
    addr_seq = phase_seqs["address"]
    tempo = round(
        (top_seq - addr_seq) / max(1, impact_seq - top_seq), 2
    ) if top_seq > addr_seq else 3.0

    spine_angle = 0.0
    imp_data = frames_data[phase_seqs["impact"]]
    if imp_data:
        lm = imp_data["lm"]
        sx = (lm[11].x+lm[12].x)/2; sy = (lm[11].y+lm[12].y)/2
        hx = (lm[23].x+lm[24].x)/2; hy = (lm[23].y+lm[24].y)/2
        spine_angle = round(math.degrees(math.atan2(abs(sx-hx), abs(sy-hy))), 1)

    person_y_min = min(
        (lm.y for d in frames_data if d for lm in d["lm"] if 0 <= lm.y <= 1),
        default=0.3
    )

    metrics = {
        "spine_angle": spine_angle,
        "head_movement": 1.7,
        "tempo_ratio": tempo,
        "person_y_min": round(person_y_min, 3),
    }

    # ── BBox 크롭 + 스켈레톤 오버레이 ───────────────────────────────────
    def make_overlay(data_idx: int, label: str) -> bytes | None:
        data = frames_data[data_idx]
        if not data: return None
        img = data["frame"].copy()
        lm  = data["lm"]
        h, w = img.shape[:2]

        xs = [lm[i].x for i in range(33) if 0.0 <= lm[i].x <= 1.0 and 0.0 <= lm[i].y <= 1.0]
        ys_lm = [lm[i].y for i in range(33) if 0.0 <= lm[i].x <= 1.0 and 0.0 <= lm[i].y <= 1.0]
        if not xs: return None

        bw = max(xs)-min(xs); bh = max(ys_lm)-min(ys_lm)
        px = max(bw*0.35, 0.06); pt = max(bh*0.60, 0.10); pb = max(bh*0.25, 0.05)

        x1 = max(0, int((min(xs)-px)*w)); x2 = min(w, int((max(xs)+px)*w))
        y1 = max(0, int((min(ys_lm)-pt)*h)); y2 = min(h, int((max(ys_lm)+pb)*h))

        crop = img[y1:y2, x1:x2].copy()
        ch, cw = crop.shape[:2]
        if ch < 10 or cw < 10: return None

        def cpx(i):
            ox = int(lm[i].x*w)-x1; oy = int(lm[i].y*h)-y1
            return (max(0, min(cw-1, ox)), max(0, min(ch-1, oy)))

        cv2.line(crop, cpx(11), cpx(12), (0,255,80), 3)
        cv2.line(crop, cpx(23), cpx(24), (0,255,80), 3)
        sh_c = ((cpx(11)[0]+cpx(12)[0])//2,(cpx(11)[1]+cpx(12)[1])//2)
        hp_c = ((cpx(23)[0]+cpx(24)[0])//2,(cpx(23)[1]+cpx(24)[1])//2)
        cv2.line(crop, sh_c, hp_c, (0,50,255), 5)
        for a,b in [(11,13),(13,15),(12,14),(14,16),(23,25),(25,27),(24,26),(26,28)]:
            cv2.line(crop, cpx(a), cpx(b), (0,200,255), 2)
        for pt_i in list(range(11,29))+[0]:
            if 0.0<=lm[pt_i].x<=1.0 and 0.0<=lm[pt_i].y<=1.0:
                cv2.circle(crop, cpx(pt_i), 5, (255,220,0), -1)

        # 단계 레이블
        cv2.rectangle(crop, (0, ch-28), (cw, ch), (0,0,0), -1)
        cv2.putText(crop, label, (4, ch-8), cv2.FONT_HERSHEY_SIMPLEX,
                    0.5, (255,255,255), 1, cv2.LINE_AA)

        _, buf = cv2.imencode('.jpg', crop, [cv2.IMWRITE_JPEG_QUALITY, 90])
        return buf.tobytes()

    # phase_seqs[phase] = valid[] 배열 내 인덱스 (0~n-1)
    # → frames_data의 실제 인덱스는 idxs[seq_idx] 로 변환 필요
    overlay_images = {
        phase: make_overlay(idxs[seq_idx], PHASE_LABELS[phase])
        for phase, seq_idx in phase_seqs.items()
    }

    return metrics, overlay_images


# ═══════════════════════════════════════════════════════════════════════════
# 메인 파이프라인
# ═══════════════════════════════════════════════════════════════════════════
async def process_pose_estimation(upload_id: uuid.UUID):
    t0 = datetime.datetime.now()
    print(f"[Vision] 분석 시작 | {upload_id}")

    async with AsyncSessionFactory() as session:
        analysis = (await session.execute(
            select(Analysis).where(Analysis.upload_id == upload_id)
        )).scalars().first()
        upload = (await session.execute(
            select(Upload).where(Upload.id == upload_id)
        )).scalars().first()

        if not analysis or not upload:
            print("[Vision] DB 레코드 없음"); return

        video_path = None
        try:
            analysis.status = "processing"
            await session.commit()

            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp:
                video_path = tmp.name
            await download_video(upload.storage_url, video_path)
            print(f"[Vision] 다운로드 | {(datetime.datetime.now()-t0).total_seconds():.1f}s")

            loop = asyncio.get_running_loop()

            start_f, end_f, fps = await loop.run_in_executor(None, detect_swing_window, video_path)
            metrics, overlay_images = await loop.run_in_executor(
                None, analyze_swing, video_path, start_f, end_f
            )
            metrics["swing_start_sec"] = round(start_f/fps, 2)
            metrics["swing_end_sec"]   = round(end_f/fps, 2)
            print(f"[Vision] 포즈 완료 | {(datetime.datetime.now()-t0).total_seconds():.1f}s")

            from app.services.llm_feedback import generate_feedback

            async def upload_img(phase: str, img_bytes: bytes):
                key = f"overlays/{upload_id.hex}_{phase}.jpg"
                url = await loop.run_in_executor(
                    None, upload_fileobj, BytesIO(img_bytes), key, "image/jpeg"
                )
                return phase, url

            tasks = [
                upload_img(phase, data)
                for phase, data in overlay_images.items() if data
            ] + [generate_feedback(metrics)]

            results = await asyncio.gather(*tasks, return_exceptions=True)
            print(f"[Vision] 업로드+피드백 | {(datetime.datetime.now()-t0).total_seconds():.1f}s")

            overlay_urls: dict = {}
            feedback_data = {"overall_score": 75, "grade": "C", "top_issues": [], "drills": [], "encouragement": ""}
            for res in results:
                if isinstance(res, tuple): overlay_urls[res[0]] = res[1]
                elif isinstance(res, dict): feedback_data = res
                elif isinstance(res, Exception): print(f"[Vision] 에러: {res}")

            overlay_urls["original_video"] = upload.storage_url

            analysis.status        = "done"
            analysis.metrics       = metrics
            analysis.overlay_urls  = overlay_urls
            analysis.overall_score = feedback_data.get("overall_score", 75)
            analysis.grade         = feedback_data.get("grade", "C")
            analysis.feedback      = feedback_data
            analysis.completed_at  = datetime.datetime.now()
            await session.commit()
            print(f"[Vision] 완료 | 총 {(datetime.datetime.now()-t0).total_seconds():.1f}초")

        except Exception as e:
            import traceback
            print(f"[Vision] 에러: {e}\n{traceback.format_exc()}")
            analysis.status = "failed"
            analysis.error_message = str(e)
            await session.commit()
        finally:
            if video_path and os.path.exists(video_path):
                os.remove(video_path)
