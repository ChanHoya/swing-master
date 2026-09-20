"""
SQLAlchemy ORM Models — users, uploads, analyses tables
"""
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    UUID,
    CHAR,
    JSON,
    SMALLINT,
    BigInteger,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    uploads: Mapped[list["Upload"]] = relationship(back_populates="user")
    analyses: Mapped[list["Analysis"]] = relationship(back_populates="user")


class Upload(Base):
    __tablename__ = "uploads"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    storage_url: Mapped[str] = mapped_column(Text, nullable=False)
    # 촬영 각도는 어떤 지표를 계산할 수 있는지를 결정한다(metrics.METRIC_ANGLES).
    # 추측하지 않고 업로드할 때 사용자가 고른 값을 쓴다.
    camera_angle: Mapped[str | None] = mapped_column(String(20), nullable=True)
    # 클럽은 지표에 영향을 주지 않는다. 기록을 구분해 보기 위한 정보다.
    club: Mapped[str | None] = mapped_column(String(20), nullable=True)
    file_size: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    user: Mapped["User | None"] = relationship(back_populates="uploads")
    analysis: Mapped["Analysis | None"] = relationship(back_populates="upload")


class Analysis(Base):
    __tablename__ = "analyses"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    upload_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("uploads.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[str] = mapped_column(String(20), default="queued", nullable=False)
    overall_score: Mapped[int | None] = mapped_column(SMALLINT, nullable=True)
    grade: Mapped[str | None] = mapped_column(CHAR(1), nullable=True)
    metrics: Mapped[Any | None] = mapped_column(JSON, nullable=True)
    feedback: Mapped[Any | None] = mapped_column(JSON, nullable=True)
    pose_frames: Mapped[Any | None] = mapped_column(JSON, nullable=True)
    overlay_urls: Mapped[Any | None] = mapped_column(JSON, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    upload: Mapped["Upload"] = relationship(back_populates="analysis")
    user: Mapped["User | None"] = relationship(back_populates="analyses")
