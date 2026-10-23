"""orders shipping columns for admin order operations (SCRUM-35, needs B review)

Revision ID: d7e2b9a4c1f6
Revises: c3a1f0e2b7d4
Create Date: 2026-10-23 15:40:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd7e2b9a4c1f6'
down_revision: Union[str, Sequence[str], None] = 'c3a1f0e2b7d4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('orders', sa.Column('courier', sa.String(length=20), nullable=True))
    op.add_column('orders', sa.Column('tracking_no', sa.String(length=30), nullable=True))
    op.add_column('orders', sa.Column('admin_note', sa.String(length=300), nullable=True))
    op.add_column('orders', sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False))
    op.create_index('ix_orders_status_ordered_at', 'orders', ['status', 'ordered_at'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_orders_status_ordered_at', table_name='orders')
    op.drop_column('orders', 'updated_at')
    op.drop_column('orders', 'admin_note')
    op.drop_column('orders', 'tracking_no')
    op.drop_column('orders', 'courier')
