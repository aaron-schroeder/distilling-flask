"""squash two

Revision ID: bffd00e50483
Revises: 4dde34190ecd
Create Date: 2023-03-28 19:42:17.864408

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'bffd00e50483'
down_revision = '4dde34190ecd'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('activity', schema=None) as batch_op:
        batch_op.drop_constraint('fk_strava_acct_id_id', type_='foreignkey')
        batch_op.create_foreign_key('fk_strava_acct_id', 'strava_account', ['strava_acct_id'], ['id'])
        batch_op.alter_column('strava_id', nullable=False, new_column_name='key')

        batch_op.alter_column('strava_acct_id', new_column_name='import_storage_id')
        batch_op.drop_constraint('fk_strava_acct_id', type_='foreignkey')
        batch_op.create_foreign_key('fk_import_storage_id', 'strava_account', ['import_storage_id'], ['id'])

    with op.batch_alter_table('strava_account', schema=None) as batch_op:
        batch_op.alter_column('strava_id', nullable=False, new_column_name='id')

    # ### end Alembic commands ###f


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('strava_account', schema=None) as batch_op:
        batch_op.alter_column('id', nullable=False, new_column_name='strava_id')

    with op.batch_alter_table('activity', schema=None) as batch_op:
        batch_op.alter_column('import_storage_id', new_column_name='strava_acct_id')
        batch_op.drop_constraint('fk_import_storage_id', type_='foreignkey')
        batch_op.create_foreign_key('fk_strava_acct_id', 'strava_account', ['strava_acct_id'], ['id'])

        batch_op.drop_constraint('fk_strava_acct_id', type_='foreignkey')
        batch_op.create_foreign_key('fk_strava_acct_id_id', 'strava_account', ['strava_acct_id'], ['strava_id'])
        batch_op.alter_column('key', nullable=False, new_column_name='id')

    # ### end Alembic commands ###
