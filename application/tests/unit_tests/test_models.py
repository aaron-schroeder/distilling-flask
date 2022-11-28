import datetime

from sqlalchemy import exc

from application import db
from application.models import Activity
from .base import FlaskTestCase


class ActivityModelTest(FlaskTestCase):

  def test_saving_and_retrieving_items(self):
    self.create_activity(title='The first (ever) Activity item')
    self.create_activity(title='Activity the second')

    saved_items = Activity.query.all()
    self.assertEqual(len(saved_items), 2)

    first_saved_item = saved_items[0]
    second_saved_item = saved_items[1]
    self.assertEqual(first_saved_item.title, 'The first (ever) Activity item')
    self.assertEqual(second_saved_item.title, 'Activity the second')

  def test_cannot_save_empty_activity(self):
    db.session.add(Activity())
    with self.assertRaisesRegex(exc.IntegrityError, 'NOT NULL constraint failed'):
      db.session.commit()

  def test_cannot_save_duplicate_strava_activity(self):
    act_1 = Activity(
      title='Strava activity',
      description='',
      created=datetime.datetime.utcnow(),
      recorded=datetime.datetime.utcnow(),
      tz_local='UTC',
      moving_time_s=3600,
      elapsed_time_s=3660,
      filepath_orig=f'activity_1.tcx',
      filepath_csv=f'activity_1.csv',
      strava_id=1,
    )
    act_2 = Activity(
      title='Duplicate Strava activity',
      description='',
      created=datetime.datetime.utcnow(),
      recorded=datetime.datetime.utcnow(),
      tz_local='America/Denver',
      moving_time_s=3700,
      elapsed_time_s=3760,
      filepath_orig=f'activity_2.tcx',
      filepath_csv=f'activity_2.csv',
      strava_id=1
    )
    db.session.add_all((act_1, act_2))
    with self.assertRaisesRegex(exc.IntegrityError, 'UNIQUE constraint failed: activity.strava_id'):
      db.session.commit()
