"""manual migration for acct/activity relationship

Revision ID: 7356c906381a
Revises: fbad678c93bd
Create Date: 2023-01-07 08:59:16.270869

"""
from stravalib import Client

from application.models import db, Activity, StravaAccount


# revision identifiers, used by Alembic.
revision = '7356c906381a'
down_revision = 'fbad678c93bd'
branch_labels = None
depends_on = None


def upgrade():
    for a in Activity.query.all():
        for acct in StravaAccount.query.all():
            try:
                sact = Client(access_token=acct.get_token()['access_token']).get_activity(a.strava_id)
            except Exception as e:
                print(e)
            else:
                print(f'{a} belongs to {acct}')
                a.strava_acct_id = acct.strava_id
                db.session.commit()
                break


def downgrade():
    pass
