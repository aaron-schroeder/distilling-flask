"""manual ngp_ms data migration

Revision ID: 71dd4ea1073f
Revises: 2b03e9148ec7
Create Date: 2023-01-15 07:34:44.733757

"""
from application.models import db, Activity
from application.util import units


# revision identifiers, used by Alembic.
revision = '71dd4ea1073f'
down_revision = '2b03e9148ec7'
branch_labels = None
depends_on = None


def upgrade():
    for activity in Activity.query.all():
        activity.ngp_ms = activity.intensity_factor * units.pace_to_speed('6:30')
        db.session.add(activity)
        db.session.commit()



def downgrade():
    pass
