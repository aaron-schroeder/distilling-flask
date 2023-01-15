
from application.models import db, Activity
from application.util import units


for activity in Activity.query.all():
  activity.ngp_ms = units.pace_to_speed('6:30') * activity.intensity_factor
  db.session.commit()