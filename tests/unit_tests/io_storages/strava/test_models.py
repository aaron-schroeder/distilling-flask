import datetime
import json

import pytz
from sqlalchemy import exc
import responses

from distilling_flask import db
from distilling_flask.io_storages.strava.models import StravaImportStorage, StravaApiActivity
from distilling_flask.util.feature_flags import flag_set
from tests.unit_tests.base import FlaskTestCase
from tests.unit_tests.io_storages.strava.base import StravaFlaskTestCase


class StravaImportStorageTest(StravaFlaskTestCase):
  def test_is_valid_with_id_only(self):
    strava_acct = StravaImportStorage()
    db.session.add(strava_acct)
    db.session.commit()  # should not raise
    self.assertEqual(
      db.session.scalar(
        db.select(db.func.count()).select_from(StravaImportStorage)),
      1
    )
    self.assertIsNotNone(strava_acct.id)
    # self.assertIsNotNone(strava_acct.strava_id)
    # user = AdminUser()
    # self.assertIs(strava_acct, user.strava_accounts[0])

  def test_iterkeys(self):  
    s = self.create_strava_acct()
    # For the first page, spit out activity data.
    with open('tests/unit_tests/sample_data/get_activities.json', 'r') as f:
      resp_json = json.load(f)
    self.api_mock.add(
      responses.GET,
      'https://www.strava.com/api/v3/athlete/activities',
      match=[responses.matchers.query_param_matcher({'page': 1,
        'per_page': 200, 'access_token': s.access_token})],
      json=resp_json,
      headers={'X-Ratelimit-Limit': '600,30000',
               'X-Ratelimit-Usage': '100,1000'},
      status=200)
    # Simulate no activities on the second page.
    self.api_mock.add(
      responses.GET,
      'https://www.strava.com/api/v3/athlete/activities',
      match=[responses.matchers.query_param_matcher({'page': 2, 
        'per_page': 200, 'access_token': s.access_token})],
      json=[],
      headers={'X-Ratelimit-Limit': '600,30000',
               'X-Ratelimit-Usage': '101,1001'},
      status=200)
    for k in s.iterkeys():
      self.assertIsInstance(k, int)

  def test_iterkeys_rate_limited(self):
    s = self.create_strava_acct()
    self.api_mock.add(
      responses.GET,
      'https://www.strava.com/api/v3/athlete/activities',
      match=[responses.matchers.query_param_matcher({'page': 1,
        'per_page': 200, 'access_token': s.access_token})],
      json={},
      headers={'X-Ratelimit-Limit': '600,30000',
               'X-Ratelimit-Usage': '629,29300'},
      status=429)
    for k in s.iterkeys():
      self.assertIsInstance(k, int)


  def test_get_data(self):
    key = 1
    with open('tests/unit_tests/sample_data/get_activity.json', 'r') as f:
      resp_json = json.load(f)
    self.api_mock.add(
      responses.GET,
      f'https://www.strava.com/api/v3/activities/{key}',
      json=resp_json,
      headers={'X-Ratelimit-Limit': '600,30000',
               'X-Ratelimit-Usage': '100,1000'},
      status=200)
    self.api_mock.add(
      responses.GET,
      f'https://www.strava.com/api/v3/activities/{key}/streams/time,latlng,distance,altitude,'
      f'velocity_smooth,heartrate,cadence,watts,temp,moving,grade_smooth',
      json=[],
      headers={'X-Ratelimit-Limit': '600,30000',
               'X-Ratelimit-Usage': '101,1001'},
      status=200)
    result = self.create_strava_acct().get_data(key)
    self.assertIsInstance(result, dict)
    self.assertIsInstance(result.pop('summary_compressed'), bytes)
    self.assertIsInstance(result.pop('streams_compressed'), bytes)
    self.assertIsInstance(result.pop('created'), datetime.datetime)
    self.assertEqual(result.pop('key'), key)
    self.assertEqual(len(result), 0)

  def test_access_token(self):
    token = '4190a7feccff6acaeb6a78cadda52e65de85a75es'
    strava_acct = StravaImportStorage(access_token=token)
    db.session.add(strava_acct)
    db.session.commit()
    self.assertEqual(strava_acct.access_token, token)

  def test_get_client_token_expired(self):
    self.api_mock.add(
      responses.POST,
      'https://www.strava.com/oauth/token',
      json=self.get_mock_token(),
      status=200)
    s = self.create_strava_acct(token_expired=True)
    _ = s.get_client()
    self.assertNotEqual(s.expires_at, 0)


def create_activity(**kwargs):
  if flag_set('ff_rename'):
    defaults = dict(
      key=1,
      created=datetime.datetime.utcnow(),
      # ngp_ms=None,
    )
  else:
    defaults = dict(
      title='title',
      description='description',
      created=datetime.datetime.utcnow(),
      recorded=datetime.datetime.utcnow(),
      tz_local='UTC',
      moving_time_s=3600,
      elapsed_time_s=3660,
      # Fields below here not required
      # strava_id=activity_data['id'],
      # distance_m=activity_data['distance'],
      # elevation_m=activity_data['total_elevation_gain'],
      ngp_ms=None
    )
  act = StravaApiActivity(**{k: kwargs.get(k, v) for k, v in defaults.items()})
  db.session.add(act)
  db.session.commit()
  return act


class StravaApiActivityTest(FlaskTestCase):
  def test_cannot_save_empty_activity(self):
    db.session.add(StravaApiActivity())
    with self.assertRaisesRegex(exc.IntegrityError, 'NOT NULL constraint failed'):
      db.session.commit()

  def test_cannot_save_duplicate_activity(self):
    act_1 = create_activity(key=1)
    with self.assertRaisesRegex(exc.IntegrityError, 
      f'UNIQUE constraint failed: '
      f'activity.{"key" if flag_set("ff_rename") else "strava_id"}'
    ):
      act_2 = create_activity(key=1)

  def test_saving_and_retrieving_items(self):
    create_activity(key=111)
    create_activity(key=2222)
    saved_items = db.session.scalars(db.select(StravaApiActivity)).all()
    self.assertEqual(len(saved_items), 2)
    first_saved_item = saved_items[0]
    second_saved_item = saved_items[1]
    self.assertEqual(first_saved_item.key, '111')
    self.assertEqual(second_saved_item.key, '2222')

  if not flag_set('ff_rename'):
    def test_find_overlap_ids(self):
      saved_8_9 = create_activity(
        recorded=datetime.datetime(2019, 12, 4, hour=8),
        elapsed_time_s=3600)
      saved_11_12 = create_activity(
        recorded=datetime.datetime(2019, 12, 4, hour=11),
        elapsed_time_s=3600)

      # ---------------------------------------------------------------------
      # Single-overlap cases

      # Prospective: |______|
      # Saved:            |______|      |______| 
      self.assertTrue(len(StravaApiActivity.find_overlap_ids(
        datetime.datetime(2019, 12, 4, hour=7, minute=30, tzinfo=pytz.UTC),
        datetime.datetime(2019, 12, 4, hour=8, minute=30, tzinfo=pytz.UTC),
      )))

      # Prospective:     |______|
      # Saved:       |______|      |______| 
      self.assertTrue(len(StravaApiActivity.find_overlap_ids(
        datetime.datetime(2019, 12, 4, hour=8, minute=30, tzinfo=pytz.UTC),
        datetime.datetime(2019, 12, 4, hour=9, minute=30, tzinfo=pytz.UTC),
      )))

      # Prospective:   |__|
      # Saved:       |______|      |______| 
      self.assertTrue(len(StravaApiActivity.find_overlap_ids(
        datetime.datetime(2019, 12, 4, hour=8, minute=15, tzinfo=pytz.UTC),
        datetime.datetime(2019, 12, 4, hour=8, minute=45, tzinfo=pytz.UTC),
      )))

      # Prospective: |__________|
      # Saved:         |______|      |______| 
      self.assertTrue(len(StravaApiActivity.find_overlap_ids(
        datetime.datetime(2019, 12, 4, hour=7, minute=45, tzinfo=pytz.UTC),
        datetime.datetime(2019, 12, 4, hour=9, minute=15, tzinfo=pytz.UTC),
      )))

      # ---------------------------------------------------------------------
      # Non-overlap cases

      # Prospective: |______|
      # Saved:                |______|          |______|
      self.assertFalse(len(StravaApiActivity.find_overlap_ids(
        datetime.datetime(2019, 12, 4, hour=6, minute=30, tzinfo=pytz.UTC),
        datetime.datetime(2019, 12, 4, hour=7, minute=30, tzinfo=pytz.UTC),
      )))

      # Prospective:                            |______|
      # Saved:       |______|          |______| 
      self.assertFalse(len(StravaApiActivity.find_overlap_ids(
        datetime.datetime(2019, 12, 4, hour=12, minute=30, tzinfo=pytz.UTC),
        datetime.datetime(2019, 12, 4, hour=13, minute=30, tzinfo=pytz.UTC),
      )))

      # Prospective:          |______|
      # Saved:       |______|          |______| 
      self.assertFalse(len(StravaApiActivity.find_overlap_ids(
        datetime.datetime(2019, 12, 4, hour=9, minute=30, tzinfo=pytz.UTC),
        datetime.datetime(2019, 12, 4, hour=10, minute=30, tzinfo=pytz.UTC),
      )))

      # ---------------------------------------------------------------------
      # Double-overlap cases

      # Prospective:          |__________|
      # Saved:           |______|      |______| 
      self.assertEqual(
        len(StravaApiActivity.find_overlap_ids(
          datetime.datetime(2019, 12, 4, hour=8, minute=45, tzinfo=pytz.UTC),
          datetime.datetime(2019, 12, 4, hour=12, minute=15, tzinfo=pytz.UTC),
        )),
        2
      )

    # NOTE: The following functionality is not really related to any model and
    # will be tested separately...eventually.

    # def test_intensity_factor(self):
    #   db.session.add(UserSettings())
    #   db.session.commit()

    #   self.assertEqual(   
    #     self.create_activity(ngp_ms=units.pace_to_speed('6:30')).intensity_factor,
    #     1.0
    #   )

    #   self.assertLess(
    #     self.create_activity(ngp_ms=units.pace_to_speed('7:30')).intensity_factor,
    #     1.0
    #   )

    #   self.assertGreater(
    #     self.create_activity(ngp_ms=units.pace_to_speed('5:30')).intensity_factor,
    #     1.0
    #   )

    # def test_tss(self):
    #   db.session.add(UserSettings())
    #   db.session.commit()

    #   activity = self.create_activity(
    #     ngp_ms=units.pace_to_speed('6:30'),
    #     elapsed_time_s=3600,
    #   )

    #   self.assertEqual(   
    #     activity.tss,
    #     100.0
    #   )

    #   self.assertLess(
    #     self.create_activity(
    #       ngp_ms=units.pace_to_speed('7:30'),
    #       elapsed_time_s=3600,
    #     ).tss,
    #     100.0
    #   )

    #   self.assertGreater(
    #     self.create_activity(
    #       ngp_ms=units.pace_to_speed('5:30'),
    #       elapsed_time_s=3600,
    #     ).tss,
    #     100.0
    #   )