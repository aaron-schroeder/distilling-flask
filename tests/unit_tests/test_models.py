import datetime

import pytz
from sqlalchemy import exc

from application import db
from application.models import Activity, AdminUser, StravaAccount, UserSettings
from application.util import units
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

  def test_find_overlap_ids(self):

    saved_8_9 = self.create_activity(
      recorded=datetime.datetime(2019, 12, 4, hour=8),
      elapsed_time_s=3600,
    )

    saved_11_12 = self.create_activity(
      recorded=datetime.datetime(2019, 12, 4, hour=11),
      elapsed_time_s=3600,
    )

    # ---------------------------------------------------------------------
    # Single-overlap cases

    # Prospective: |______|
    # Saved:            |______|      |______| 
    self.assertTrue(len(Activity.find_overlap_ids(
      datetime.datetime(2019, 12, 4, hour=7, minute=30, tzinfo=pytz.UTC),
      datetime.datetime(2019, 12, 4, hour=8, minute=30, tzinfo=pytz.UTC),
    )))

    # Prospective:     |______|
    # Saved:       |______|      |______| 
    self.assertTrue(len(Activity.find_overlap_ids(
      datetime.datetime(2019, 12, 4, hour=8, minute=30, tzinfo=pytz.UTC),
      datetime.datetime(2019, 12, 4, hour=9, minute=30, tzinfo=pytz.UTC),
    )))

    # Prospective:   |__|
    # Saved:       |______|      |______| 
    self.assertTrue(len(Activity.find_overlap_ids(
      datetime.datetime(2019, 12, 4, hour=8, minute=15, tzinfo=pytz.UTC),
      datetime.datetime(2019, 12, 4, hour=8, minute=45, tzinfo=pytz.UTC),
    )))

    # Prospective: |__________|
    # Saved:         |______|      |______| 
    self.assertTrue(len(Activity.find_overlap_ids(
      datetime.datetime(2019, 12, 4, hour=7, minute=45, tzinfo=pytz.UTC),
      datetime.datetime(2019, 12, 4, hour=9, minute=15, tzinfo=pytz.UTC),
    )))

    # ---------------------------------------------------------------------
    # Non-overlap cases

    # Prospective: |______|
    # Saved:                |______|          |______|
    self.assertFalse(len(Activity.find_overlap_ids(
      datetime.datetime(2019, 12, 4, hour=6, minute=30, tzinfo=pytz.UTC),
      datetime.datetime(2019, 12, 4, hour=7, minute=30, tzinfo=pytz.UTC),
    )))

    # Prospective:                            |______|
    # Saved:       |______|          |______| 
    self.assertFalse(len(Activity.find_overlap_ids(
      datetime.datetime(2019, 12, 4, hour=12, minute=30, tzinfo=pytz.UTC),
      datetime.datetime(2019, 12, 4, hour=13, minute=30, tzinfo=pytz.UTC),
    )))

    # Prospective:          |______|
    # Saved:       |______|          |______| 
    self.assertFalse(len(Activity.find_overlap_ids(
      datetime.datetime(2019, 12, 4, hour=9, minute=30, tzinfo=pytz.UTC),
      datetime.datetime(2019, 12, 4, hour=10, minute=30, tzinfo=pytz.UTC),
    )))

    # ---------------------------------------------------------------------
    # Double-overlap cases

    # Prospective:          |__________|
    # Saved:           |______|      |______| 
    self.assertEqual(
      len(Activity.find_overlap_ids(
        datetime.datetime(2019, 12, 4, hour=8, minute=45, tzinfo=pytz.UTC),
        datetime.datetime(2019, 12, 4, hour=12, minute=15, tzinfo=pytz.UTC),
      )),
      2
    )

  def test_intensity_factor(self):
    db.session.add(UserSettings())
    db.session.commit()

    self.assertEqual(   
      self.create_activity(ngp_ms=units.pace_to_speed('6:30')).intensity_factor,
      1.0
    )

    self.assertLess(
      self.create_activity(ngp_ms=units.pace_to_speed('7:30')).intensity_factor,
      1.0
    )

    self.assertGreater(
      self.create_activity(ngp_ms=units.pace_to_speed('5:30')).intensity_factor,
      1.0
    )

  def test_tss(self):
    db.session.add(UserSettings())
    db.session.commit()

    activity = self.create_activity(
      ngp_ms=units.pace_to_speed('6:30'),
      elapsed_time_s=3600,
    )

    self.assertEqual(   
      activity.tss,
      100.0
    )

    self.assertLess(
      self.create_activity(
        ngp_ms=units.pace_to_speed('7:30'),
        elapsed_time_s=3600,
      ).tss,
      100.0
    )

    self.assertGreater(
      self.create_activity(
        ngp_ms=units.pace_to_speed('5:30'),
        elapsed_time_s=3600,
      ).tss,
      100.0
    )


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
    self.assertIs(strava_acct, user.strava_accounts[0])

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
