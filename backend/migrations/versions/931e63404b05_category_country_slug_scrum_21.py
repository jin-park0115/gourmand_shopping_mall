"""category country slug (SCRUM-21)

Revision ID: 931e63404b05
Revises: c3a1f0e2b7d4
Create Date: 2026-10-23 16:01:34.288596

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '931e63404b05'
down_revision: Union[str, Sequence[str], None] = 'c3a1f0e2b7d4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# 이 리비전 시점의 값 (앱 코드를 import 하지 않도록 복사). 시드(infrastructure/seed.py)와 같아요.
CATEGORY_SLUGS = {
    "스낵·칩": "snack",
    "쿠키·비스킷": "cookie",
    "케이크·베이커리": "bakery",
    "초콜릿": "chocolate",
    "젤리·캔디": "candy",
    "육포·견과·별미": "savory",
}
COUNTRY_SLUGS = {"일본": "japan", "대만": "taiwan", "중국": "china", "베트남": "vietnam"}


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('category', sa.Column('slug', sa.String(length=30), nullable=True))
    op.add_column('country', sa.Column('slug', sa.String(length=30), nullable=True))

    # 이미 들어 있는 행 채우기. 6개 분류가 아닌 옛 카테고리는 임시 slug 로 (시드를 다시 돌리면 정리돼요)
    for name, slug in CATEGORY_SLUGS.items():
        op.execute(sa.text("UPDATE category SET slug = :slug WHERE name = :name").bindparams(slug=slug, name=name))
    op.execute("UPDATE category SET slug = 'category-' || category_id WHERE slug IS NULL")
    for name, slug in COUNTRY_SLUGS.items():
        op.execute(sa.text("UPDATE country SET slug = :slug WHERE name = :name").bindparams(slug=slug, name=name))

    op.alter_column('category', 'slug', nullable=False)
    op.create_unique_constraint('category_slug_key', 'category', ['slug'])
    op.create_unique_constraint('country_slug_key', 'country', ['slug'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint('country_slug_key', 'country', type_='unique')
    op.drop_constraint('category_slug_key', 'category', type_='unique')
    op.drop_column('country', 'slug')
    op.drop_column('category', 'slug')
