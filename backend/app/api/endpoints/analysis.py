"""
Analysis endpoints — GET /analysis/{upload_id}/status, GET /analysis/{upload_id}/result
"""
import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models import Analysis

router = APIRouter()


@router.get("/{upload_id}/status")
async def get_analysis_status(upload_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> dict:
    """
    업로드된 영상의 현재 분석 상태를 조회합니다 (Polling 용도).
    상태: queued -> processing -> done / failed
    """
    stmt = select(Analysis).where(Analysis.upload_id == upload_id)
    result = await db.execute(stmt)
    analysis = result.scalars().first()

    if not analysis:
        raise HTTPException(status_code=404, detail="해당 업로드에 대한 분석 작업이 존재하지 않습니다.")

    return {
        "upload_id": str(upload_id),
        "status": analysis.status,
        "error_message": analysis.error_message
    }


@router.get("/{upload_id}/result")
async def get_analysis_result(upload_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> dict:
    """
    분석이 완료된 결과(스윙 지표, 피드백 등)를 반환합니다.
    """
    stmt = select(Analysis).where(Analysis.upload_id == upload_id)
    result = await db.execute(stmt)
    analysis = result.scalars().first()

    if not analysis:
        raise HTTPException(status_code=404, detail="해당 업로드에 대한 분석 작업이 존재하지 않습니다.")

    if analysis.status != "done":
        raise HTTPException(status_code=400, detail=f"분석이 아직 완료되지 않았습니다. 현재 상태: {analysis.status}")

    return {
        "upload_id": str(upload_id),
        "status": analysis.status,
        "overall_score": analysis.overall_score,
        "grade": analysis.grade,
        "metrics": analysis.metrics,
        "feedback": analysis.feedback,
        "pose_frames": analysis.pose_frames,
        "overlay_urls": analysis.overlay_urls,
        "completed_at": analysis.completed_at
    }
