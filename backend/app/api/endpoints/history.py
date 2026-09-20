"""
History endpoint — GET /history
사용자별 분석 이력 + 통계 반환
"""
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user_id
from app.core.database import get_db
from app.models import Analysis, Upload

router = APIRouter()


@router.get("/history")
async def get_history(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    로그인한 사용자의 분석 이력 반환.
    각 항목: upload_id, status, overall_score, grade, overlay_urls, completed_at
    """
    import uuid as uuid_mod
    uid = uuid_mod.UUID(user_id)

    # 촬영 각도와 클럽은 uploads 에 있다. 목록에서 기록을 구분해 보려면
    # 함께 가져와야 하므로 조인한다.
    stmt = (
        select(Analysis, Upload)
        .join(Upload, Upload.id == Analysis.upload_id)
        .where(Analysis.user_id == uid)
        .order_by(Analysis.created_at.desc())
        .limit(20)
    )
    rows = list((await db.execute(stmt)).all())

    items = []
    for a, upload in rows:
        thumbnail = None
        if a.overlay_urls and isinstance(a.overlay_urls, dict):
            thumbnail = a.overlay_urls.get("impact") or a.overlay_urls.get("address")

        items.append({
            "analysis_id": str(a.id),
            "upload_id": str(a.upload_id),
            "status": a.status,
            "overall_score": a.overall_score,
            "grade": a.grade,
            "thumbnail": thumbnail,
            # 옛 기록에는 없다. 지어내지 않고 null 로 둔다.
            "camera_angle": upload.camera_angle,
            "club": upload.club,
            "completed_at": a.completed_at.isoformat() if a.completed_at else None,
        })

    scores = [i["overall_score"] for i in items if i["overall_score"] is not None]
    avg_score = round(sum(scores) / len(scores)) if scores else None

    return {
        "total": len(items),
        "average_score": avg_score,
        "analyses": items,
    }
