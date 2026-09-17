"""
swing/pipeline.py — 스윙 분석 오케스트레이션.

다운로드 → 스윙 구간 탐지 → 포즈 추출 → 7단계 분할 → 지표 계산
→ 오버레이 렌더링 → R2 업로드 → 규칙 기반 피드백 → DB 저장.

기존 pose_estimator.py 의 오케스트레이션(다운로드·DB·R2·asyncio)을 그대로 옮기고,
지표 계산은 app.services.swing.{phases,pose,metrics} 로, 진단·점수는
app.services.feedback.rules 로 교체했다. 측정하지 못한 지표에 가짜 기본값을
채우지 않는 것이 이 모듈의 핵심 규칙이다.
"""
from __future__ import annotations

import asyncio
import datetime
import os
import tempfile
import uuid
from io import BytesIO

import cv2
import httpx
from sqlalchemy import select

from app.core.database import AsyncSessionFactory
from app.core.storage import upload_fileobj
from app.models import Analysis, Upload
from app.services.feedback.rules import evaluate
from app.services.swing.metrics import compute_metrics, metrics_to_json
from app.services.swing.overlay import render_overlay
from app.services.swing.phases import detect_phases, detect_swing_window
from app.services.swing.pose import extract_sequence
from app.services.swing.types import PoseSequence

PHASE_LABELS: dict[str, str] = {
    "address": "1.어드레스",
    "takeaway": "2.테이크백",
    "top": "3.탑",
    "downswing": "4.다운스윙",
    "impact": "5.임팩트",
    "followthrough": "6.팔로우스루",
    "finish": "7.피니시",
}


def summarise_metrics(payload: dict) -> dict:
    """히스토리 목록에서 촬영이 잘 됐는지 가늠할 요약값."""
    measured = sum(
        1 for m in payload.values() if m.get("value") is not None
    )
    return {"measured_count": measured, "total_count": len(payload)}


async def download_video(url: str, dest: str) -> None:
    async with httpx.AsyncClient(follow_redirects=True, timeout=60.0) as client:
        async with client.stream("GET", url) as response:
            response.raise_for_status()
            with open(dest, "wb") as f:
                async for chunk in response.aiter_bytes(chunk_size=65536):
                    f.write(chunk)


def _render_phase_overlays(
    video_path: str,
    seq: PoseSequence,
    phase_seqs: dict[str, int],
    proc_width: int = 640,
) -> dict[str, bytes]:
    """7단계 각각의 프레임을 다시 읽어 스켈레톤 오버레이 이미지를 만든다.

    PoseSequence 는 좌표만 갖고 원본 프레임 픽셀은 버리므로, 오버레이를
    그리려면 영상을 한 번 더 훑어야 한다. xy_px 가 extract_sequence 와 같은
    proc_width 기준 좌표계라 프레임도 동일하게 리사이즈해야 자세가 맞는다.
    """
    cap = cv2.VideoCapture(video_path)
    images: dict[str, bytes] = {}
    try:
        for phase, seq_idx in phase_seqs.items():
            frame_no = int(seq.frame_indices[seq_idx])
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_no)
            ok, frame = cap.read()
            if not ok:
                continue
            h0, w0 = frame.shape[:2]
            if w0 > proc_width:
                frame = cv2.resize(frame, (proc_width, int(h0 * proc_width / w0)))
            img_bytes = render_overlay(frame, seq.xy_px[seq_idx], PHASE_LABELS[phase])
            if img_bytes is not None:
                images[phase] = img_bytes
    finally:
        cap.release()
    return images


async def process_pose_estimation(upload_id: uuid.UUID) -> None:
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

            start_f, end_f, fps = await loop.run_in_executor(
                None, detect_swing_window, video_path
            )
            seq = await loop.run_in_executor(
                None, extract_sequence, video_path, start_f, end_f
            )
            phases = detect_phases(seq)
            # Plan 2에서 uploads.camera_angle 컬럼이 생기기 전까지는 기본값으로 처리한다.
            camera_angle = getattr(upload, "camera_angle", None) or "down_the_line"
            metrics = compute_metrics(seq, phases, camera_angle)
            metrics_payload = metrics_to_json(metrics)
            metrics_payload["_meta"] = {
                "camera_angle": camera_angle,
                "swing_start_sec": round(start_f / fps, 2),
                "swing_end_sec": round(end_f / fps, 2),
                **summarise_metrics(
                    {k: v for k, v in metrics_payload.items() if k != "_meta"}
                ),
            }
            print(f"[Vision] 포즈 완료 | {(datetime.datetime.now()-t0).total_seconds():.1f}s")

            overlay_images = await loop.run_in_executor(
                None, _render_phase_overlays, video_path, seq, phases
            )

            # 규칙 엔진이 진단·점수·드릴을 확정한다. LLM 없이 완결된다.
            # TODO(Task 14): 여기서 evaluate() 결과 문장을 LLM으로 다듬는다.
            metrics_only = {k: v for k, v in metrics_payload.items() if k != "_meta"}
            feedback_data = evaluate(metrics_only)

            async def upload_img(phase: str, img_bytes: bytes):
                key = f"overlays/{upload_id.hex}_{phase}.jpg"
                url = await loop.run_in_executor(
                    None, upload_fileobj, BytesIO(img_bytes), key, "image/jpeg"
                )
                return phase, url

            tasks = [
                upload_img(phase, data)
                for phase, data in overlay_images.items() if data
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            print(f"[Vision] 업로드 | {(datetime.datetime.now()-t0).total_seconds():.1f}s")

            overlay_urls: dict = {}
            for res in results:
                if isinstance(res, tuple):
                    overlay_urls[res[0]] = res[1]
                elif isinstance(res, Exception):
                    print(f"[Vision] 에러: {res}")

            overlay_urls["original_video"] = upload.storage_url

            analysis.status        = "done"
            analysis.metrics       = metrics_payload
            analysis.overlay_urls  = overlay_urls
            analysis.overall_score = feedback_data.get("overall_score")
            analysis.grade         = feedback_data.get("grade")
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
