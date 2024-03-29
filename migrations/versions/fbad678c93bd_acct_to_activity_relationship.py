"""acct to activity relationship

Revision ID: fbad678c93bd
Revises: 01decae7c1ec
Create Date: 2023-01-06 16:19:10.112957

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'fbad678c93bd'
down_revision = '01decae7c1ec'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('activity', schema=None) as batch_op:
        batch_op.add_column(sa.Column('strava_acct_id', sa.Integer(), nullable=True))
        batch_op.create_foreign_key('fk_strava_acct_id_id', 'strava_account', ['strava_acct_id'], ['strava_id'])

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('activity', schema=None) as batch_op:
        batch_op.drop_constraint(None, type_='foreignkey')
        batch_op.drop_column('strava_acct_id')

    # ### end Alembic commands ###
