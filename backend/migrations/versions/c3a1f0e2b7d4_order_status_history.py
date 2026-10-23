"""order status history (SCRUM-33)

Revision ID: c3a1f0e2b7d4
Revises: 509a0c2d7dc1
Create Date: 2026-10-23 15:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c3a1f0e2b7d4'
down_revision: Union[str, Sequence[str], None] = '509a0c2d7dc1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

STATUS_VALUES = "'접수', '상품준비중', '배송중', '배송완료', '배송지연', '주문취소'"


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('order_status_history',
    sa.Column('history_id', sa.Integer(), nullable=False),
    sa.Column('order_id', sa.Integer(), nullable=False),
    sa.Column('from_status', sa.String(length=20), nullable=True),
    sa.Column('to_status', sa.String(length=20), nullable=False),
    sa.Column('changed_by', sa.Integer(), nullable=True),
    sa.Column('note', sa.String(length=300), nullable=True),
    sa.Column('changed_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint(f'to_status IN ({STATUS_VALUES})', name='ck_order_status_history_to_status'),
    sa.CheckConstraint(f'from_status IS NULL OR from_status IN ({STATUS_VALUES})', name='ck_order_status_history_from_status'),
    sa.ForeignKeyConstraint(['changed_by'], ['member.member_id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['order_id'], ['orders.order_id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('history_id')
    )
    op.create_index('ix_order_status_history_order_changed', 'order_status_history', ['order_id', 'changed_at'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_order_status_history_order_changed', table_name='order_status_history')
    op.drop_table('order_status_history')
