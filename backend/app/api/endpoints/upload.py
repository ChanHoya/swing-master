"""
Upload endpoint — POST /upload
"""
import uuid
import asyncio
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_optional_user_id
from app.core.database import get_db
from app.core.storage import upload_fileobj
from app.models import Upload, Analysis

router = APIRouter()

MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB
ALLOWED_TYPES = ["video/mp4", "video/quicktime"]


@router.post("")
async def upload_video(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    user_id: str | None = Depends(get_optional_user_id),
) -> dict:
    """
    영상 파일 업로드 엔드포인트.
    1. 파일 검증
    2. Cloudflare R2 스토리지에 업로드
    3. DB에 uploads, analyses 레코드 생성 (queued 상태)
    """
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=400, 
            detail="지원되지 않는 파일 형식입니다. (MP4, MOV만 가능)"
        )

    # 파이썬에서 파일 크기를 확인하기 위해 커서를 맨 끝으로 보냄
    file.file.seek(0, 2)
    file_size = file.file.tell()
    file.file.seek(0)

    if file_size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400, 
            detail=f"파일 크기는 100MB 이하여야 합니다. (현재: {file_size / (1024*1024):.1f}MB)"
        )

    # R2 스토리지용 고유 키 생성
    ext = file.filename.split(".")[-1].lower() if "." in (file.filename or "") else "mp4"
    if ext == "blob":  # FormData에서 filename 지정 안 될 경우 빈번함
        ext = "mp4"
        
    file_key = f"uploads/{uuid.uuid4().hex}.{ext}"

    # boto3는 동기 라이브러리이므로 비동기 로직인 FastAPI를 블로킹하지 않도록 executor에서 실행
    loop = asyncio.get_running_loop()
    try:
        storage_url = await loop.run_in_executor(
            None,
            upload_fileobj,
            file.file,
            file_key,
            file.content_type
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"스토리지 업로드 중 오류가 발생했습니다: {str(e)}"
        )

    # 로그인했다면 그 사용자에게 귀속시킨다. 비로그인이면 None 으로 남는다.
    # 이게 없으면 GET /history 가 user_id 로 필터하므로 로그인해도 빈 배열이 나온다.
    owner = uuid.UUID(user_id) if user_id else None

    # 1. Upload 레코드 추가
    db_upload = Upload(storage_url=storage_url, file_size=file_size, user_id=owner)
    db.add(db_upload)
    await db.flush()  # id를 받아오기 위해 먼저 플러시

    # 2. Analysis 레코드 추가 (최초 상태 queued)
    db_analysis = Analysis(upload_id=db_upload.id, status="queued", user_id=owner)
    db.add(db_analysis)
    await db.commit()
    await db.refresh(db_upload)

    from app.services.swing.pipeline import process_pose_estimation
    background_tasks.add_task(process_pose_estimation, db_upload.id)

    return {
        "message": "성공적으로 업로드되었습니다.",
        "upload_id": str(db_upload.id),
        "storage_url": storage_url
    }
