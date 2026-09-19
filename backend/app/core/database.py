"""
Async SQLAlchemy engine & session factory
"""
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.ENV == "development",
    pool_size=10,
    max_overflow=20,
    # Neon 은 5분 유휴 후 컴퓨트를 정지하며 연결을 끊는다. 풀에 남은 죽은
    # 커넥션을 그대로 쓰면 다음 요청이 실패하므로, 꺼낼 때 한 번 확인한다.
    pool_pre_ping=True,
    connect_args={
        "statement_cache_size": 0,
        "prepared_statement_cache_size": 0,
    }
)

AsyncSessionFactory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncSession:
    """FastAPI dependency — yields an async DB session."""
    async with AsyncSessionFactory() as session:
        yield session
