"""uploads 에 club 과 camera_angle 추가

Revision ID: 002
Revises: 001
Create Date: 2026-09-20 00:00:00.000000

촬영 각도는 지금까지 pipeline.py 에서 늘 "down_the_line" 으로 고정돼 있었다
(컬럼이 없어 getattr 기본값이 쓰였다). 그래서 정면 전용 지표인 head_movement
와 weight_shift 는 어떤 영상에서도 "측정 불가"로만 나왔다.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 기존 행은 값을 알 수 없으므로 NULL 로 둔다. 소급해 채울 근거가 없다.
    op.add_column("uploads", sa.Column("camera_angle", sa.String(20), nullable=True))
    op.add_column("uploads", sa.Column("club", sa.String(20), nullable=True))


def downgrade() -> None:
    op.drop_column("uploads", "club")
    op.drop_column("uploads", "camera_angle")
