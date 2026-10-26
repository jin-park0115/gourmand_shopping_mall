"""review member link (SCRUM-25)

Revision ID: a4f3fa9ce8d9
Revises: e4b8c2d1a9f3
Create Date: 2026-10-26 10:38:44.749300

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a4f3fa9ce8d9'
down_revision: Union[str, Sequence[str], None] = 'e4b8c2d1a9f3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # 인수 당시 리뷰는 작성자 이름만 있어서 회원을 알 수 없어요 (1인 1리뷰 · 본인 확인 불가).
    # 지금까지 시드 · 화면 어디서도 리뷰를 만들지 않아 비어 있지만, 혹시 남은 옛 리뷰는 지우고 회원 연결로 바꿔요.
    op.execute("DELETE FROM review")
    op.drop_column('review', 'author_name')
    op.add_column('review', sa.Column('member_id', sa.Integer(), nullable=False))
    op.add_column('review', sa.Column('updated_at', sa.DateTime(), nullable=True))
    op.create_foreign_key('review_member_id_fkey', 'review', 'member', ['member_id'], ['member_id'], ondelete='CASCADE')
    op.create_unique_constraint('uq_review_product_member', 'review', ['product_id', 'member_id'])


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("DELETE FROM review")
    op.drop_constraint('uq_review_product_member', 'review', type_='unique')
    op.drop_constraint('review_member_id_fkey', 'review', type_='foreignkey')
    op.drop_column('review', 'updated_at')
    op.drop_column('review', 'member_id')
    op.add_column('review', sa.Column('author_name', sa.String(length=50), nullable=False))
