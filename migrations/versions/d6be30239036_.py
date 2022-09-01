"""empty message

Revision ID: d6be30239036
Revises: 
Create Date: 2022-08-25 11:52:23.116464

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'd6be30239036'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('colorum_admins',
    sa.Column('id', sa.String(), nullable=False),
    sa.Column('password', sa.String(), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('id')
    )
    op.create_table('colorum_users',
    sa.Column('id', sa.String(), nullable=False),
    sa.Column('password', sa.String(), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('id')
    )
    op.create_table('gps_devices',
    sa.Column('id', sa.String(), nullable=False),
    sa.Column('online', sa.Boolean(), nullable=False),
    sa.Column('last_location', postgresql.ARRAY(sa.Float()), nullable=True),
    sa.Column('associated_route', sa.String(), nullable=True),
    sa.Column('distance_to_route', sa.Float(), nullable=True),
    sa.Column('is_colorum', sa.Boolean(), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('id')
    )
    op.create_table('puv_routes',
    sa.Column('id', sa.String(), nullable=False),
    sa.Column('gpx_filename', sa.String(), nullable=True),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('id')
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('routes')
    op.drop_table('gps_devices')
    op.drop_table('colorum_users')
    op.drop_table('colorum_admins')
    # ### end Alembic commands ###