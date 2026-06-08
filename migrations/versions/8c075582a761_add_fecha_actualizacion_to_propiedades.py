"""create propiedades table

Revision ID: 8c075582a761
Revises:
Create Date: 2026-06-03 16:00:03.921798

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = '8c075582a761'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'propiedades',
        sa.Column('id_propiedad', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('titulo', sa.String(200), nullable=False),
        sa.Column('descripcion', sa.Text, nullable=False),
        sa.Column('precio', sa.Numeric(12, 2), nullable=False),
        sa.Column('moneda', sa.String(3), nullable=False),
        sa.Column('provincia', sa.String(50), nullable=False),
        sa.Column('canton', sa.String(100), nullable=False),
        sa.Column('distrito', sa.String(100), nullable=False),
        sa.Column('tipo', sa.String(20), nullable=False),
        sa.Column('estado', sa.String(20), nullable=False, server_default='disponible'),
        sa.Column('imagenes', postgresql.ARRAY(sa.Text), nullable=False),
        sa.Column('id_dueno', sa.String(100), nullable=False),
        sa.Column('amenidades', postgresql.ARRAY(sa.Text), nullable=False),
        sa.Column('fecha_creacion', sa.DateTime(timezone=True), nullable=False),
        sa.Column('fecha_actualizacion', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('ix_propiedades_id_dueno', 'propiedades', ['id_dueno'])
    op.create_index('ix_propiedades_provincia_tipo', 'propiedades', ['provincia', 'tipo'])
    op.create_index('ix_propiedades_precio', 'propiedades', ['precio'])
    op.create_index('ix_propiedades_estado', 'propiedades', ['estado'])


def downgrade() -> None:
    op.drop_index('ix_propiedades_estado', table_name='propiedades')
    op.drop_index('ix_propiedades_precio', table_name='propiedades')
    op.drop_index('ix_propiedades_provincia_tipo', table_name='propiedades')
    op.drop_index('ix_propiedades_id_dueno', table_name='propiedades')
    op.drop_table('propiedades')
