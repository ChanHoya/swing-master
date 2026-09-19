"""
Swing Master Backend — FastAPI Application Entry Point
"""
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import engine, Base
from app.api.router import api_router




def check_production_config() -> None:
    """운영 설정이 빠졌는지 기동 전에 확인한다.

    DATABASE_URL 을 빠뜨리면 앱은 config.py 의 기본값(localhost)으로 조용히
    떨어져 컨테이너 자기 자신에게 접속하고, 화면에는 원인과 무관해 보이는
    ConnectionRefusedError 가 찍힌다. 실제 Render 배포가 그렇게 실패했다.
    설정 실수는 설정 실수라고 말해야 고칠 수 있다.
    """
    if settings.ENV != "production":
        return

    problems: list[str] = []

    if "localhost" in settings.DATABASE_URL or "127.0.0.1" in settings.DATABASE_URL:
        problems.append(
            "DATABASE_URL 이 localhost 를 가리키고 있습니다. 환경변수가 "
            "설정되지 않아 기본값이 쓰인 것으로 보입니다. 배포 대시보드에서 "
            "DATABASE_URL 을 postgresql+asyncpg://... 형태로 넣어 주세요."
        )

    if settings.SECRET_KEY == "change-me-in-production":
        problems.append(
            "SECRET_KEY 가 기본값입니다. 이대로면 누구나 로그인 토큰을 "
            "위조할 수 있습니다. 배포 대시보드에서 SECRET_KEY 를 설정해 주세요."
        )

    if problems:
        raise RuntimeError("운영 설정 오류:\n  - " + "\n  - ".join(problems))


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan: startup & shutdown hooks."""
    # Startup
    check_production_config()

    async with engine.begin() as conn:
        # In production, use Alembic migrations instead
        # This creates tables only in development / test
        if settings.ENV == "development":
            await conn.run_sync(Base.metadata.create_all)
    yield
    # Shutdown
    await engine.dispose()


app = FastAPI(
    title="Swing Master API",
    description="Golf Swing AI Analysis — FastAPI Backend",
    version="0.1.0",
    docs_url="/docs" if settings.ENV != "production" else None,
    redoc_url="/redoc" if settings.ENV != "production" else None,
    lifespan=lifespan,
)

# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    # 빈 문자열을 그대로 넘기면 모든 오리진에 대해 fullmatch 가 시도된다.
    # 설정하지 않았다는 뜻이므로 None 으로 바꿔 끈다.
    allow_origin_regex=settings.CORS_ORIGIN_REGEX or None,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------
app.include_router(api_router)
