import datetime

from sqlalchemy import exc

from application import db
from application.models import Activity, AdminUser, StravaAccount
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
      strava_id=1
    )
    db.session.add_all((act_1, act_2))
    with self.assertRaisesRegex(exc.IntegrityError, 'UNIQUE constraint failed: activity.strava_id'):
      db.session.commit()


class AdminUserModelTest(FlaskTestCase):

  def test_user_is_valid_with_id_only(self):
    user = AdminUser()  # should not raise
    self.assertIsNotNone(user.id)
  
  def test_id_is_always_same(self):
    user_1 = AdminUser()
    user_2 = AdminUser()
    self.assertEqual(user_1.id, 1)
    self.assertEqual(user_2.id, 1)


class StravaAccountModelTest(FlaskTestCase):

  def test_account_is_valid_with_id_only(self):
    strava_acct = StravaAccount()
    db.session.add(strava_acct)
    db.session.commit()  # should not raise
    self.assertEqual(StravaAccount.query.count(), 1)
    self.assertIsNotNone(strava_acct.strava_id)

    user = AdminUser()
    self.assertIs(strava_acct, user.strava_account)

  def test_access_token(self):
    strava_acct = StravaAccount(
      access_token='4190a7feccff6acaeb6a78cadda52e65de85a75es'
    )
    db.session.add(strava_acct)
    db.session.commit()
    self.assertEqual(
      strava_acct.access_token,
      '4190a7feccff6acaeb6a78cadda52e65de85a75es'
    )
