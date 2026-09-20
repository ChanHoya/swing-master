"""
Upload endpoint — POST /upload
"""
import uuid
import asyncio
from fastapi import APIRouter, Depends, Form, HTTPException, UploadFile, File, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user_id
from app.core.database import get_db
from app.core.storage import upload_fileobj
from app.models import Upload, Analysis

router = APIRouter()

MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB
# 브라우저에서 640px 로 줄여 보내면 MediaRecorder 가 만든 형식이 온다.
# Chrome 은 webm(VP8/VP9), Safari 는 mp4(H.264) 다. OpenCV 가 둘 다 읽는 것을
# 확인했다(VP9 webm 90프레임/30fps 정상 디코딩).
ALLOWED_TYPES = frozenset({"video/mp4", "video/quicktime", "video/webm"})


def normalise_content_type(raw: str | None) -> str:
    """content-type 에서 코덱 꼬리표를 떼고 검증한다.

    MediaRecorder 는 "video/webm;codecs=vp9" 처럼 코덱을 붙여 보낸다.
    정확히 일치만 보면 이런 값이 전부 거부되어, 줄여 보내는 최적화가 막힌다.
    """
    base = (raw or "").split(";")[0].strip().lower()
    if base not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=400,
            detail="지원되지 않는 파일 형식입니다. (MP4, MOV, WebM만 가능)",
        )
    return base


# content-type 별 저장 확장자. 파일 이름을 믿지 않는 이유는, 브라우저에서
# 640px 로 줄여 보내면 내용은 webm 인데 이름은 원본 그대로 "swing.mp4" 로
# 오기 때문이다. 내용을 말해 주는 것은 content-type 이다.
_EXTENSIONS = {"video/mp4": "mp4", "video/quicktime": "mov", "video/webm": "webm"}


def extension_for(content_type: str) -> str:
    return _EXTENSIONS.get(content_type, "mp4")

# 촬영 각도는 어떤 지표를 계산할 수 있는지를 결정한다(metrics.METRIC_ANGLES).
# 아무 문자열이나 받으면 게이팅이 조용히 무너지므로 허용값만 통과시킨다.
CAMERA_ANGLES = frozenset({"down_the_line", "face_on", "angled"})
CLUBS = frozenset({"드라이버", "3W", "유틸", "5I", "7I", "9I", "PW", "SW"})


def normalise_camera_angle(value: str | None) -> str:
    """촬영 각도를 검증해 돌려준다. 모르면 추측하지 않고 거부한다."""
    if value not in CAMERA_ANGLES:
        raise HTTPException(
            status_code=400,
            detail="촬영 각도를 선택해 주세요. (후면/정면/45°)",
        )
    return value


def normalise_club(value: str | None) -> str | None:
    """클럽을 검증해 돌려준다. 지표에 영향을 주지 않으므로 없어도 된다."""
    if not value:
        return None
    if value not in CLUBS:
        raise HTTPException(status_code=400, detail="알 수 없는 클럽입니다.")
    return value


@router.post("")
async def upload_video(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    camera_angle: str = Form(...),
    club: str | None = Form(None),
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
) -> dict:
    """
    영상 파일 업로드 엔드포인트.
    1. 파일 검증
    2. Cloudflare R2 스토리지에 업로드
    3. DB에 uploads, analyses 레코드 생성 (queued 상태)
    """
    angle = normalise_camera_angle(camera_angle)
    club_name = normalise_club(club)

    content_type = normalise_content_type(file.content_type)

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
    file_key = f"uploads/{uuid.uuid4().hex}.{extension_for(content_type)}"

    # boto3는 동기 라이브러리이므로 비동기 로직인 FastAPI를 블로킹하지 않도록 executor에서 실행
    loop = asyncio.get_running_loop()
    try:
        storage_url = await loop.run_in_executor(
            None,
            upload_fileobj,
            file.file,
            file_key,
            content_type
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"스토리지 업로드 중 오류가 발생했습니다: {str(e)}"
        )

    # 업로드는 로그인한 사용자에게만 허용한다. 공개 URL 에서 익명 업로드를
    # 열어 두면 R2 용량과 Gemini 할당량이 모르는 사람에게 나간다.
    owner = uuid.UUID(user_id)

    # 1. Upload 레코드 추가
    db_upload = Upload(
        storage_url=storage_url,
        file_size=file_size,
        user_id=owner,
        camera_angle=angle,
        club=club_name,
    )
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
