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


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan: startup & shutdown hooks."""
    # Startup
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
